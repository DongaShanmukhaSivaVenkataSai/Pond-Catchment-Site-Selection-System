import numpy as np


INPUT_FILE = "dem.npz"
OUTPUT_FILE = "terrain_analysis.npz"


# --------------------------------------------------
# 1. Load DEM
# --------------------------------------------------

data = np.load(INPUT_FILE)

dem = data["dem"]
resolution = float(data["resolution"])

print("DEM shape:", dem.shape)
print("Resolution:", resolution, "meters")


# --------------------------------------------------
# 2. Calculate elevation gradients
# --------------------------------------------------

# Gradient in Y direction
gradient_y, gradient_x = np.gradient(
    dem,
    resolution,
    resolution
)


# --------------------------------------------------
# 3. Calculate slope
# --------------------------------------------------

slope_radians = np.arctan(
    np.sqrt(
        gradient_x ** 2 +
        gradient_y ** 2
    )
)

slope_degrees = np.degrees(slope_radians)

slope_percent = (
    np.tan(slope_radians) * 100
)


# --------------------------------------------------
# 4. Print statistics
# --------------------------------------------------

print("Minimum slope:", slope_degrees.min(), "degrees")
print("Maximum slope:", slope_degrees.max(), "degrees")
print("Mean slope:", slope_degrees.mean(), "degrees")


# --------------------------------------------------
# 5. Save terrain information
# --------------------------------------------------

np.savez_compressed(
    OUTPUT_FILE,

    dem=dem,

    slope_degrees=slope_degrees,

    slope_percent=slope_percent,

    resolution=resolution,

    grid_x=data["grid_x"],

    grid_y=data["grid_y"]
)


print("Saved to:", OUTPUT_FILE)