import json
import numpy as np
from scipy.interpolate import griddata


INPUT_FILE = "projected_contours.json"
OUTPUT_FILE = "dem.npz"

RESOLUTION = 1.0   # meters


# --------------------------------------------------
# 1. Load projected contours
# --------------------------------------------------

with open(INPUT_FILE, "r") as f:
    data = json.load(f)

contours = data["contours"]

print("Loaded contours:", len(contours))


# --------------------------------------------------
# 2. Extract X, Y, Z
# --------------------------------------------------

x_points = []
y_points = []
elevations = []


for contour in contours:

    elevation = contour["elevation"]

    for x, y in contour["coordinates"]:

        x_points.append(x)
        y_points.append(y)
        elevations.append(elevation)


x_points = np.array(x_points)
y_points = np.array(y_points)
elevations = np.array(elevations)


print("Total elevation points:", len(x_points))


# --------------------------------------------------
# 3. Determine terrain extent
# --------------------------------------------------

min_x = x_points.min()
max_x = x_points.max()

min_y = y_points.min()
max_y = y_points.max()


print("X range:", min_x, "to", max_x)
print("Y range:", min_y, "to", max_y)


# --------------------------------------------------
# 4. Create DEM grid
# --------------------------------------------------

grid_x = np.arange(
    min_x,
    max_x + RESOLUTION,
    RESOLUTION
)

grid_y = np.arange(
    min_y,
    max_y + RESOLUTION,
    RESOLUTION
)


grid_x, grid_y = np.meshgrid(grid_x, grid_y)


# --------------------------------------------------
# 5. Interpolate elevation
# --------------------------------------------------

dem = griddata(
    (x_points, y_points),
    elevations,
    (grid_x, grid_y),
    method="linear"
)


# --------------------------------------------------
# 6. Fill areas outside interpolation
# --------------------------------------------------

missing = np.isnan(dem)

if np.any(missing):

    dem_nearest = griddata(
        (x_points, y_points),
        elevations,
        (grid_x[missing], grid_y[missing]),
        method="nearest"
    )

    dem[missing] = dem_nearest


# --------------------------------------------------
# 7. Save DEM
# --------------------------------------------------

np.savez_compressed(
    OUTPUT_FILE,
    dem=dem,
    grid_x=grid_x,
    grid_y=grid_y,
    resolution=RESOLUTION
)


print()
print("DEM created successfully.")
print("DEM shape:", dem.shape)
print("Elevation minimum:", np.min(dem))
print("Elevation maximum:", np.max(dem))
print("Saved to:", OUTPUT_FILE)