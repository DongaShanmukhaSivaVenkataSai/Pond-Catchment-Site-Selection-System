import numpy as np


INPUT_FILE = "flow_accumulation.npz"
OUTPUT_FILE = "pond_candidates.npz"


# --------------------------------------------------
# Configuration
# --------------------------------------------------

FLOW_PERCENTILE = 10

# Maximum slope considered reasonable for a
# preliminary pond candidate.
MAX_SLOPE_DEGREES = 10.0

# Ignore cells close to the DEM boundary.
BOUNDARY_CELLS = 2


# --------------------------------------------------
# 1. Load data
# --------------------------------------------------

data = np.load(INPUT_FILE)

dem = data["dem"]
flow_accumulation = data["flow_accumulation"]
resolution = float(data["resolution"])

grid_x = data["grid_x"]
grid_y = data["grid_y"]

rows, cols = dem.shape


# --------------------------------------------------
# 2. Calculate slope again
# --------------------------------------------------

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
# 3. Calculate flow threshold dynamically
# --------------------------------------------------

flow_threshold = np.percentile(
    flow_accumulation,
    FLOW_PERCENTILE
)

print("Flow threshold:", flow_threshold)


# --------------------------------------------------
# 4. Create candidate mask
# --------------------------------------------------

candidate_mask = (
    (flow_accumulation >= flow_threshold)
    &
    (slope_degrees <= MAX_SLOPE_DEGREES)
)


# --------------------------------------------------
# 5. Remove boundary cells
# --------------------------------------------------

candidate_mask[:BOUNDARY_CELLS, :] = False
candidate_mask[-BOUNDARY_CELLS:, :] = False

candidate_mask[:, :BOUNDARY_CELLS] = False
candidate_mask[:, -BOUNDARY_CELLS:] = False


# --------------------------------------------------
# 6. Get candidate locations
# --------------------------------------------------

candidate_rows, candidate_cols = np.where(
    candidate_mask
)


print("Number of candidate cells:", len(candidate_rows))


# --------------------------------------------------
# 7. Extract candidate information
# --------------------------------------------------

candidates = []

for r, c in zip(candidate_rows, candidate_cols):

    candidates.append({
        "row": int(r),
        "col": int(c),

        "x": float(grid_x[r, c]),
        "y": float(grid_y[r, c]),

        "elevation": float(dem[r, c]),

        "slope_degrees": float(
            slope_degrees[r, c]
        ),

        "flow_accumulation": float(
            flow_accumulation[r, c]
        )
    })


# --------------------------------------------------
# 8. Sort candidates
# --------------------------------------------------

candidates.sort(
    key=lambda x: x["flow_accumulation"],
    reverse=True
)


# --------------------------------------------------
# 9. Display top candidates
# --------------------------------------------------

print("\nTop 10 candidates:")

for candidate in candidates[:10]:

    print(
        "X:", candidate["x"],
        "Y:", candidate["y"],
        "Elevation:", candidate["elevation"],
        "Slope:", candidate["slope_degrees"],
        "Flow:", candidate["flow_accumulation"]
    )


# --------------------------------------------------
# 10. Save
# --------------------------------------------------

np.savez_compressed(
    OUTPUT_FILE,

    candidate_mask=candidate_mask,

    slope_degrees=slope_degrees,

    dem=dem,

    flow_accumulation=flow_accumulation,

    grid_x=grid_x,

    grid_y=grid_y,

    resolution=resolution
)


print()
print("Candidates saved to:", OUTPUT_FILE)