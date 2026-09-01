import json
import os
import numpy as np


INPUT_FLOW = "flow_direction.npz"
TOP_5_POND_FILE = "top_5_pond_candidates.json"
SINGLE_POND_FILE = "best_pond_candidate.json"

OUTPUT_FILE = "catchment.npz"
OUTPUT_TOP_5_NPZ = "top_5_catchments.npz"
OUTPUT_TOP_5_JSON = "top_5_catchments.json"


# --------------------------------------------------
# 1. Load flow direction and DEM data
# --------------------------------------------------

data = np.load(INPUT_FLOW)

flow_direction = data["flow_direction"]
dem = data["dem"]

grid_x = data["grid_x"]
grid_y = data["grid_y"]

resolution = float(data["resolution"])
rows, cols = flow_direction.shape


# --------------------------------------------------
# 2. Load pond candidates
# --------------------------------------------------

ponds = []

if os.path.exists(TOP_5_POND_FILE):
    with open(TOP_5_POND_FILE, "r") as f:
        ponds_data = json.load(f)
        ponds = ponds_data.get("candidates", [])

if not ponds and os.path.exists(SINGLE_POND_FILE):
    with open(SINGLE_POND_FILE, "r") as f:
        single_pond = json.load(f)
        loc = single_pond.get("pond_location", {})
        ponds = [{
            "rank": 1,
            "latitude": loc.get("latitude"),
            "longitude": loc.get("longitude"),
            "x_m": loc.get("x_m"),
            "y_m": loc.get("y_m"),
            "elevation_m": single_pond.get("terrain", {}).get("elevation_m"),
            "flow_accumulation_cells": single_pond.get("hydrology", {}).get("flow_accumulation_cells"),
            "google_maps_url": f"https://www.google.com/maps?q={loc.get('latitude')},{loc.get('longitude')}"
        }]

if not ponds:
    raise FileNotFoundError(f"Neither {TOP_5_POND_FILE} nor {SINGLE_POND_FILE} found.")


# --------------------------------------------------
# 3. D8 direction offsets
# --------------------------------------------------

directions = [
    (-1, -1),  # 0 = NW
    (-1,  0),  # 1 = N
    (-1,  1),  # 2 = NE
    ( 0, -1),  # 3 = W
    ( 0,  1),  # 4 = E
    ( 1, -1),  # 5 = SW
    ( 1,  0),  # 6 = S
    ( 1,  1)   # 7 = SE
]


# --------------------------------------------------
# 4. Build reverse-flow (upstream) graph
# --------------------------------------------------

print("Building reverse flow graph...")
upstream = {}

for r in range(rows):
    for c in range(cols):
        direction = flow_direction[r, c]

        if direction == -1:
            continue

        dr, dc = directions[direction]
        nr = r + dr
        nc = c + dc

        if 0 <= nr < rows and 0 <= nc < cols:
            if (nr, nc) not in upstream:
                upstream[(nr, nc)] = []
            upstream[(nr, nc)].append((r, c))


# --------------------------------------------------
# 5. Delineate Catchments for all candidates
# --------------------------------------------------

cell_area = resolution * resolution
catchment_masks = []
catchment_results = []

for pond in ponds:
    rank = pond.get("rank", len(catchment_results) + 1)
    pond_x = pond["x_m"]
    pond_y = pond["y_m"]

    # Find closest cell to the pond outlet
    dist_sq = (grid_x - pond_x) ** 2 + (grid_y - pond_y) ** 2
    pond_row, pond_col = np.unravel_index(
        np.argmin(dist_sq),
        dist_sq.shape
    )

    pond_elev = float(dem[pond_row, pond_col])

    # Upstream BFS/DFS traversal
    mask = np.zeros((rows, cols), dtype=bool)
    stack = [(pond_row, pond_col)]

    while stack:
        r, c = stack.pop()
        if mask[r, c]:
            continue

        mask[r, c] = True

        for upstream_cell in upstream.get((r, c), []):
            stack.append(upstream_cell)

    catchment_cells = int(np.sum(mask))
    area_m2 = float(catchment_cells * cell_area)
    area_hectares = float(area_m2 / 10000.0)

    catchment_masks.append(mask)

    catchment_dem_vals = dem[mask]
    min_elev = float(np.min(catchment_dem_vals))
    max_elev = float(np.max(catchment_dem_vals))
    mean_elev = float(np.mean(catchment_dem_vals))

    catchment_results.append({
        "rank": rank,
        "pond_outlet": {
            "latitude": pond.get("latitude"),
            "longitude": pond.get("longitude"),
            "x_m": float(pond_x),
            "y_m": float(pond_y),
            "grid_row": int(pond_row),
            "grid_col": int(pond_col),
            "elevation_m": pond_elev,
            "google_maps_url": pond.get("google_maps_url")
        },
        "catchment": {
            "cell_count": catchment_cells,
            "cell_area_m2": cell_area,
            "area_m2": area_m2,
            "area_hectares": area_hectares,
            "min_elevation_m": min_elev,
            "max_elevation_m": max_elev,
            "mean_elevation_m": mean_elev
        }
    })

catchment_masks_arr = np.array(catchment_masks, dtype=bool)


# --------------------------------------------------
# 6. Save results
# --------------------------------------------------

# 6.1 Primary catchment.npz (backward compatible with single catchment + full top 5 stack)
best_pond_row = catchment_results[0]["pond_outlet"]["grid_row"]
best_pond_col = catchment_results[0]["pond_outlet"]["grid_col"]
best_pond_x = catchment_results[0]["pond_outlet"]["x_m"]
best_pond_y = catchment_results[0]["pond_outlet"]["y_m"]

np.savez_compressed(
    OUTPUT_FILE,
    catchment_mask=catchment_masks[0],
    catchment_masks=catchment_masks_arr,
    pond_row=best_pond_row,
    pond_col=best_pond_col,
    pond_x=best_pond_x,
    pond_y=best_pond_y,
    dem=dem,
    flow_direction=flow_direction,
    grid_x=grid_x,
    grid_y=grid_y,
    resolution=resolution
)

# 6.2 Top 5 NPZ
np.savez_compressed(
    OUTPUT_TOP_5_NPZ,
    catchment_masks=catchment_masks_arr,
    grid_x=grid_x,
    grid_y=grid_y,
    dem=dem,
    resolution=resolution
)

# 6.3 Top 5 JSON summary
with open(OUTPUT_TOP_5_JSON, "w") as f:
    json.dump({"top_catchments": catchment_results}, f, indent=2)


# --------------------------------------------------
# 7. Print summary
# --------------------------------------------------

print("\n" + "=" * 80)
print(f" TOP {len(catchment_results)} DELINEATED CATCHMENTS SUMMARY")
print("=" * 80)

for res in catchment_results:
    p = res["pond_outlet"]
    c = res["catchment"]
    print(f"\n[RANK #{res['rank']}] Pond Outlet: Lat {p['latitude']:.6f}, Lon {p['longitude']:.6f} | Elev: {p['elevation_m']:.1f} m")
    print(f"  Grid Location:   Row {p['grid_row']}, Col {p['grid_col']} (UTM: X={p['x_m']:.1f}, Y={p['y_m']:.1f})")
    print(f"  Catchment Area:  {c['area_m2']:,.1f} m² ({c['area_hectares']:.4f} hectares / {c['cell_count']:,} cells)")
    print(f"  Elevation Range: {c['min_elevation_m']:.1f} m to {c['max_elevation_m']:.1f} m (Mean: {c['mean_elevation_m']:.1f} m)")
    print(f"  Google Maps:     {p['google_maps_url']}")

print("\n" + "=" * 80)
print(f"Saved primary catchment to: {OUTPUT_FILE}")
print(f"Saved all top {len(catchment_results)} masks to:   {OUTPUT_TOP_5_NPZ}")
print(f"Saved summary JSON to:      {OUTPUT_TOP_5_JSON}")
print("=" * 80)