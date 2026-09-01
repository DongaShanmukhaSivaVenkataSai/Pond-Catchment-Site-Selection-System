import numpy as np


INPUT_FILE = "flow_direction.npz"
OUTPUT_FILE = "flow_accumulation.npz"


# --------------------------------------------------
# 1. Load flow direction
# --------------------------------------------------

data = np.load(INPUT_FILE)

dem = data["dem"]
flow_direction = data["flow_direction"]

resolution = float(data["resolution"])
grid_x = data["grid_x"]
grid_y = data["grid_y"]

rows, cols = dem.shape


# --------------------------------------------------
# 2. D8 directions
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
# 3. Initialize accumulation
# --------------------------------------------------

# Every cell initially contributes its own water.
flow_accumulation = np.ones(
    (rows, cols),
    dtype=np.float64
)


# --------------------------------------------------
# 4. Count incoming cells
# --------------------------------------------------

incoming = np.zeros(
    (rows, cols),
    dtype=np.int32
)


for r in range(rows):

    for c in range(cols):

        direction = flow_direction[r, c]

        if direction == -1:
            continue

        dr, dc = directions[direction]

        nr = r + dr
        nc = c + dc

        if nr < 0 or nr >= rows:
            continue

        if nc < 0 or nc >= cols:
            continue

        incoming[nr, nc] += 1


# --------------------------------------------------
# 5. Process cells from upstream to downstream
# --------------------------------------------------

queue = []

for r in range(rows):

    for c in range(cols):

        if incoming[r, c] == 0:
            queue.append((r, c))


processed = 0


while queue:

    r, c = queue.pop()

    processed += 1

    direction = flow_direction[r, c]

    if direction == -1:
        continue

    dr, dc = directions[direction]

    nr = r + dr
    nc = c + dc

    if nr < 0 or nr >= rows:
        continue

    if nc < 0 or nc >= cols:
        continue

    # Send accumulated water downstream
    flow_accumulation[nr, nc] += flow_accumulation[r, c]

    # One upstream dependency has now been processed
    incoming[nr, nc] -= 1

    if incoming[nr, nc] == 0:
        queue.append((nr, nc))


# --------------------------------------------------
# 6. Print statistics
# --------------------------------------------------

print("DEM shape:", dem.shape)
print("Processed cells:", processed)

print(
    "Minimum flow accumulation:",
    flow_accumulation.min()
)

print(
    "Maximum flow accumulation:",
    flow_accumulation.max()
)

print(
    "Mean flow accumulation:",
    flow_accumulation.mean()
)


# --------------------------------------------------
# 7. Save
# --------------------------------------------------

np.savez_compressed(
    OUTPUT_FILE,

    dem=dem,

    flow_direction=flow_direction,

    flow_accumulation=flow_accumulation,

    resolution=resolution,

    grid_x=grid_x,

    grid_y=grid_y
)


print()
print("Flow accumulation calculated.")
print("Saved to:", OUTPUT_FILE)