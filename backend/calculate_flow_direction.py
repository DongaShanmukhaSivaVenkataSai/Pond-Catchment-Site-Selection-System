import numpy as np


INPUT_FILE = "terrain_analysis.npz"
OUTPUT_FILE = "flow_direction.npz"


# --------------------------------------------------
# 1. Load DEM
# --------------------------------------------------

data = np.load(INPUT_FILE)

dem = data["dem"]
resolution = float(data["resolution"])

rows, cols = dem.shape

print("DEM shape:", dem.shape)
print("Resolution:", resolution, "meters")


# --------------------------------------------------
# 2. Define D8 directions
# --------------------------------------------------

# (row change, column change)
directions = [
    (-1, -1),  # NW
    (-1,  0),  # N
    (-1,  1),  # NE
    ( 0, -1),  # W
    ( 0,  1),  # E
    ( 1, -1),  # SW
    ( 1,  0),  # S
    ( 1,  1)   # SE
]


# Direction codes
# 0 = NW
# 1 = N
# 2 = NE
# 3 = W
# 4 = E
# 5 = SW
# 6 = S
# 7 = SE


flow_direction = np.full(
    (rows, cols),
    -1,
    dtype=np.int8
)


# --------------------------------------------------
# 3. Calculate flow direction
# --------------------------------------------------

for r in range(rows):

    for c in range(cols):

        current_elevation = dem[r, c]

        best_slope = 0
        best_direction = -1

        for direction_index, (dr, dc) in enumerate(directions):

            nr = r + dr
            nc = c + dc

            # Outside DEM
            if nr < 0 or nr >= rows:
                continue

            if nc < 0 or nc >= cols:
                continue

            neighbor_elevation = dem[nr, nc]

            # Only consider downhill neighbors
            elevation_drop = (
                current_elevation - neighbor_elevation
            )

            if elevation_drop <= 0:
                continue

            # Horizontal/vertical distance
            if dr == 0 or dc == 0:
                distance = resolution

            # Diagonal distance
            else:
                distance = resolution * np.sqrt(2)

            # Downhill slope
            slope = elevation_drop / distance

            # Keep steepest downhill direction
            if slope > best_slope:
                best_slope = slope
                best_direction = direction_index

        flow_direction[r, c] = best_direction


# --------------------------------------------------
# 4. Statistics
# --------------------------------------------------

no_flow = np.sum(flow_direction == -1)

print("Cells with no downhill neighbor:", no_flow)

for i, (dr, dc) in enumerate(directions):

    count = np.sum(flow_direction == i)

    print(
        f"Direction {i}: {count} cells"
    )


# --------------------------------------------------
# 5. Save
# --------------------------------------------------

np.savez_compressed(
    OUTPUT_FILE,

    dem=dem,

    flow_direction=flow_direction,

    resolution=resolution,

    grid_x=data["grid_x"],

    grid_y=data["grid_y"]
)


print()
print("Flow direction calculated.")
print("Saved to:", OUTPUT_FILE)