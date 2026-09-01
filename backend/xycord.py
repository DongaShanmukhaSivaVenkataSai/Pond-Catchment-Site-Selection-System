from pyproj import Transformer
import json
import numpy as np


# Load original contours
with open("contours.json", "r") as f:
    contours = json.load(f)

# Load candidates
data = np.load("pond_candidates.npz")

dem = data["dem"]
flow_accumulation = data["flow_accumulation"]
candidate_mask = data["candidate_mask"]

grid_x = data["grid_x"]
grid_y = data["grid_y"]


# --------------------------------------------------
# Determine UTM zone from input data
# --------------------------------------------------

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


# --------------------------------------------------
# UTM → WGS84
# --------------------------------------------------

transformer = Transformer.from_crs(
    f"EPSG:{epsg}",
    "EPSG:4326",
    always_xy=True
)


# --------------------------------------------------
# Find top 10 candidates
# --------------------------------------------------

rows, cols = np.where(candidate_mask)

# Sort candidates by flow accumulation descending
sorted_indices = np.argsort(flow_accumulation[rows, cols])[::-1]

print("\nTOP 10 POND CANDIDATES")
print("=" * 60)

for i in range(min(10, len(sorted_indices))):
    idx = sorted_indices[i]
    r = rows[idx]
    c = cols[idx]

    x = grid_x[r, c]
    y = grid_y[r, c]

    # Convert UTM -> WGS84
    longitude, latitude = transformer.transform(x, y)

    flow_val = flow_accumulation[r, c]
    elev_val = dem[r, c]

    print(f"\nCandidate #{i + 1}")
    print("-" * 30)
    print(f"UTM X: {x:.2f}, UTM Y: {y:.2f}")
    print(f"Elevation: {elev_val:.2f} m | Flow Accumulation: {flow_val:.1f}")
    print(f"Latitude : {latitude:.6f}")
    print(f"Longitude: {longitude:.6f}")
    print(f"Google Maps Link: https://www.google.com/maps?q={latitude:.6f},{longitude:.6f}")