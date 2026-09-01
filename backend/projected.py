import json
import math
from pyproj import Transformer


INPUT_FILE = "contours.json"
OUTPUT_FILE = "projected_contours.json"


# --------------------------------------------------
# 1. Load parsed contour data
# --------------------------------------------------

with open(INPUT_FILE, "r") as f:
    contours = json.load(f)

print("Loaded contours:", len(contours))


# --------------------------------------------------
# 2. Collect all longitude/latitude points
# --------------------------------------------------

all_points = []

for contour in contours:
    for lon, lat in contour["coordinates"]:
        all_points.append((lon, lat))


if not all_points:
    raise ValueError("No coordinates found in contours.json")


# --------------------------------------------------
# 3. Calculate center of the dataset
# --------------------------------------------------

mean_lon = sum(lon for lon, lat in all_points) / len(all_points)
mean_lat = sum(lat for lon, lat in all_points) / len(all_points)

print("Center longitude:", mean_lon)
print("Center latitude :", mean_lat)


# --------------------------------------------------
# 4. Determine UTM zone automatically
# --------------------------------------------------

utm_zone = math.floor((mean_lon + 180) / 6) + 1

# Northern/Southern hemisphere
if mean_lat >= 0:
    epsg = 32600 + utm_zone
    hemisphere = "north"
else:
    epsg = 32700 + utm_zone
    hemisphere = "south"


print("UTM zone:", utm_zone)
print("Hemisphere:", hemisphere)
print("EPSG:", epsg)


# --------------------------------------------------
# 5. Create coordinate transformer
# --------------------------------------------------

transformer = Transformer.from_crs(
    "EPSG:4326",       # WGS84 lon/lat
    f"EPSG:{epsg}",    # UTM
    always_xy=True
)


# --------------------------------------------------
# 6. Convert every contour
# --------------------------------------------------

projected_contours = []

for contour in contours:

    projected_coordinates = []

    for lon, lat in contour["coordinates"]:

        x, y = transformer.transform(lon, lat)

        projected_coordinates.append([
            x,
            y
        ])

    projected_contours.append({
        "id": contour["id"],
        "elevation": contour["elevation"],
        "coordinates": projected_coordinates
    })


# --------------------------------------------------
# 7. Store projected data
# --------------------------------------------------

output = {
    "coordinate_system": {
        "source": "EPSG:4326",
        "target": f"EPSG:{epsg}",
        "projection": "UTM",
        "utm_zone": utm_zone,
        "hemisphere": hemisphere,
        "units": "meters"
    },
    "contours": projected_contours
}


with open(OUTPUT_FILE, "w") as f:
    json.dump(output, f, indent=2)


print()
print("Successfully projected coordinates.")
print("Saved to:", OUTPUT_FILE)


# --------------------------------------------------
# 8. Display first contour for verification
# --------------------------------------------------

first = projected_contours[0]

print()
print("First contour:")
print("ID:", first["id"])
print("Elevation:", first["elevation"])
print("Number of points:", len(first["coordinates"]))

print("First projected point:")
print(first["coordinates"][0])