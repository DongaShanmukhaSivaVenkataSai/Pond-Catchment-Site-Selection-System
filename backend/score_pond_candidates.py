import numpy as np
import json
from pyproj import Transformer


INPUT_FILE = "pond_candidates.npz"
CONTOURS_FILE = "contours.json"

OUTPUT_FILE = "best_pond_candidate.json"
OUTPUT_TOP_N_FILE = "top_5_pond_candidates.json"

# Number of pond locations to find
TOP_N = 5

# Minimum spatial distance (in meters) between selected pond sites
# to ensure they represent distinct geographic locations.
MIN_DISTANCE_METERS = 100.0


# --------------------------------------------------
# 1. Load candidate data
# --------------------------------------------------

data = np.load(INPUT_FILE)

dem = data["dem"]
candidate_mask = data["candidate_mask"]
flow_accumulation = data["flow_accumulation"]

grid_x = data["grid_x"]
grid_y = data["grid_y"]
resolution = float(data["resolution"])


# --------------------------------------------------
# 2. Calculate / retrieve slope
# --------------------------------------------------

if "slope_degrees" in data:
    slope_degrees = data["slope_degrees"]
else:
    gradient_y, gradient_x = np.gradient(
        dem,
        resolution,
        resolution
    )
    slope_radians = np.arctan(
        np.sqrt(
            gradient_x ** 2 +
            gradient_y ** 2
        )
    )
    slope_degrees = np.degrees(slope_radians)


# --------------------------------------------------
# 3. Get candidate cells
# --------------------------------------------------

rows, cols = np.where(candidate_mask)

if len(rows) == 0:
    raise ValueError("No pond candidates found.")


candidate_flow = flow_accumulation[
    rows,
    cols
]

candidate_slope = slope_degrees[
    rows,
    cols
]

candidate_elevation = dem[
    rows,
    cols
]


# --------------------------------------------------
# 4. Normalize values
# --------------------------------------------------

def normalize(values):
    minimum = np.min(values)
    maximum = np.max(values)

    if maximum == minimum:
        return np.ones_like(values)

    return (
        (values - minimum)
        / (maximum - minimum)
    )


# Flow: higher is better
flow_score = normalize(candidate_flow)

# Slope: lower is better
slope_score = 1.0 - normalize(candidate_slope)

# Elevation: lower elevation gets higher score
elevation_score = 1.0 - normalize(candidate_elevation)


# --------------------------------------------------
# 5. Calculate combined score
# --------------------------------------------------

FLOW_WEIGHT = 0.60
SLOPE_WEIGHT = 0.30
ELEVATION_WEIGHT = 0.10


suitability_score = (
    FLOW_WEIGHT * flow_score
    +
    SLOPE_WEIGHT * slope_score
    +
    ELEVATION_WEIGHT * elevation_score
)


# --------------------------------------------------
# 6. Setup coordinate transformer (UTM -> WGS84)
# --------------------------------------------------

with open(CONTOURS_FILE, "r") as f:
    contours = json.load(f)

all_lon = []
all_lat = []

for contour in contours:
    for lon, lat in contour["coordinates"]:
        all_lon.append(lon)
        all_lat.append(lat)

mean_lon = np.mean(all_lon)
mean_lat = np.mean(all_lat)

utm_zone = int((mean_lon + 180) // 6) + 1

if mean_lat >= 0:
    epsg = 32600 + utm_zone
else:
    epsg = 32700 + utm_zone

transformer = Transformer.from_crs(
    f"EPSG:{epsg}",
    "EPSG:4326",
    always_xy=True
)


# --------------------------------------------------
# 7. Select Top N distinct candidates (Spatial NMS)
# --------------------------------------------------

sorted_indices = np.argsort(suitability_score)[::-1]

selected_candidates = []

for idx in sorted_indices:
    r = rows[idx]
    c = cols[idx]

    cand_x = float(grid_x[r, c])
    cand_y = float(grid_y[r, c])

    # Check minimum distance against already selected candidates
    too_close = False
    for prev in selected_candidates:
        dist_sq = (cand_x - prev["x_m"]) ** 2 + (cand_y - prev["y_m"]) ** 2
        if dist_sq < (MIN_DISTANCE_METERS ** 2):
            too_close = True
            break

    if not too_close:
        lon, lat = transformer.transform(cand_x, cand_y)

        cand_elevation = float(dem[r, c])
        cand_slope = float(slope_degrees[r, c])
        cand_flow = float(flow_accumulation[r, c])
        cand_score = float(suitability_score[idx])

        rank = len(selected_candidates) + 1

        selected_candidates.append({
            "rank": rank,
            "latitude": float(lat),
            "longitude": float(lon),
            "x_m": cand_x,
            "y_m": cand_y,
            "elevation_m": cand_elevation,
            "slope_degrees": cand_slope,
            "flow_accumulation_cells": cand_flow,
            "suitability_score": cand_score,
            "google_maps_url": f"https://www.google.com/maps?q={lat},{lon}"
        })

        if len(selected_candidates) == TOP_N:
            break


# --------------------------------------------------
# 8. Save results
# --------------------------------------------------

# 8.1 Primary best candidate JSON (maintains full compatibility)
best = selected_candidates[0]
best_result = {
    "pond_location": {
        "latitude": best["latitude"],
        "longitude": best["longitude"],
        "x_m": best["x_m"],
        "y_m": best["y_m"]
    },
    "terrain": {
        "elevation_m": best["elevation_m"],
        "slope_degrees": best["slope_degrees"]
    },
    "hydrology": {
        "flow_accumulation_cells": best["flow_accumulation_cells"]
    },
    "suitability": {
        "score": best["suitability_score"],
        "flow_weight": FLOW_WEIGHT,
        "slope_weight": SLOPE_WEIGHT,
        "elevation_weight": ELEVATION_WEIGHT
    },
    "crs": {
        "projected_epsg": f"EPSG:{epsg}",
        "source": "EPSG:4326"
    }
}

with open(OUTPUT_FILE, "w") as f:
    json.dump(best_result, f, indent=2)

# 8.2 Top N candidates JSON
top_n_result = {
    "top_candidates_count": len(selected_candidates),
    "min_separation_distance_m": MIN_DISTANCE_METERS,
    "crs": {
        "projected_epsg": f"EPSG:{epsg}",
        "source": "EPSG:4326"
    },
    "weights": {
        "flow_weight": FLOW_WEIGHT,
        "slope_weight": SLOPE_WEIGHT,
        "elevation_weight": ELEVATION_WEIGHT
    },
    "candidates": selected_candidates
}

with open(OUTPUT_TOP_N_FILE, "w") as f:
    json.dump(top_n_result, f, indent=2)


# --------------------------------------------------
# 9. Print results
# --------------------------------------------------

print("=" * 75)
print(f" TOP {len(selected_candidates)} BEST POND CANDIDATES (Min Separation: {MIN_DISTANCE_METERS}m)")
print("=" * 75)

for cand in selected_candidates:
    print(f"\n[RANK #{cand['rank']}] Suitability Score: {cand['suitability_score']:.4f}")
    print(f"  Coordinates:  Lat {cand['latitude']:.6f}, Lon {cand['longitude']:.6f} (UTM: X={cand['x_m']:.1f}, Y={cand['y_m']:.1f})")
    print(f"  Terrain:      Elevation = {cand['elevation_m']:.1f} m | Slope = {cand['slope_degrees']:.2f}°")
    print(f"  Hydrology:    Flow Accumulation = {cand['flow_accumulation_cells']:.0f} cells")
    print(f"  Google Maps:  {cand['google_maps_url']}")

print("\n" + "=" * 75)
print(f"Saved #1 candidate to:  {OUTPUT_FILE}")
print(f"Saved all top {len(selected_candidates)} to:    {OUTPUT_TOP_N_FILE}")
print("=" * 75)