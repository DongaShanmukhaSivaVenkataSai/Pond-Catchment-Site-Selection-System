import json
import numpy as np

from shapely.geometry import box, mapping
from shapely.ops import unary_union
from pyproj import Transformer


# ============================================================
# FILES
# ============================================================

CATCHMENT_FILE = "catchment.npz"
CONTOURS_FILE = "contours.json"

OUTPUT_FILE = "catchment.geojson"


# ============================================================
# 1. LOAD CATCHMENT DATA
# ============================================================

data = np.load(CATCHMENT_FILE)

catchment_mask = data["catchment_mask"]

grid_x = data["grid_x"]
grid_y = data["grid_y"]

dem = data["dem"]

resolution = float(data["resolution"])

pond_row = int(data["pond_row"])
pond_col = int(data["pond_col"])


print("Catchment mask shape:", catchment_mask.shape)
print("Resolution:", resolution, "meters")


# ============================================================
# 2. GET CATCHMENT CELLS
# ============================================================

rows, cols = np.where(catchment_mask)

print("Number of catchment cells:", len(rows))


if len(rows) == 0:
    raise ValueError("No catchment cells found.")


# ============================================================
# 3. CREATE POLYGON FOR EACH GRID CELL
# ============================================================

cell_polygons = []


for row, col in zip(rows, cols):

    center_x = grid_x[row, col]
    center_y = grid_y[row, col]

    half = resolution / 2

    cell_polygon = box(
        center_x - half,
        center_y - half,
        center_x + half,
        center_y + half
    )

    cell_polygons.append(cell_polygon)


# ============================================================
# 4. MERGE ALL CELLS INTO ONE CATCHMENT GEOMETRY
# ============================================================

print("Merging catchment cells...")

catchment_polygon = unary_union(cell_polygons)

# Fix small geometry issues
catchment_polygon = catchment_polygon.buffer(0)


print(
    "Catchment geometry type:",
    catchment_polygon.geom_type
)


# ============================================================
# 5. CALCULATE AREA
# ============================================================

catchment_area_m2 = catchment_polygon.area

catchment_area_hectares = (
    catchment_area_m2 / 10000
)


print()
print("Catchment area:")
print(
    f"{catchment_area_m2:.2f} m²"
)

print(
    f"{catchment_area_hectares:.4f} hectares"
)


# ============================================================
# 6. DETERMINE PROJECTED CRS
# ============================================================

# Read original longitude/latitude coordinates
# to determine the appropriate UTM zone.

with open(CONTOURS_FILE, "r") as f:
    contours = json.load(f)


all_longitudes = []
all_latitudes = []


for contour in contours:

    for lon, lat in contour["coordinates"]:

        all_longitudes.append(lon)
        all_latitudes.append(lat)


if not all_longitudes:
    raise ValueError(
        "No coordinates found in contours.json"
    )


mean_lon = np.mean(all_longitudes)
mean_lat = np.mean(all_latitudes)


# Determine UTM zone automatically
utm_zone = int(
    (mean_lon + 180) // 6
) + 1


# Northern or southern hemisphere
if mean_lat >= 0:

    epsg = 32600 + utm_zone

else:

    epsg = 32700 + utm_zone


print()
print("Mean longitude:", mean_lon)
print("Mean latitude:", mean_lat)
print("UTM zone:", utm_zone)
print("Projected CRS:", f"EPSG:{epsg}")


# ============================================================
# 7. CREATE TRANSFORMER
# ============================================================

transformer = Transformer.from_crs(
    f"EPSG:{epsg}",
    "EPSG:4326",
    always_xy=True
)


# ============================================================
# 8. TRANSFORM CATCHMENT TO WGS84
# ============================================================

def transform_polygon(polygon):

    # Exterior boundary
    exterior = []

    for x, y in polygon.exterior.coords:

        lon, lat = transformer.transform(
            x,
            y
        )

        exterior.append(
            [lon, lat]
        )


    # Interior holes
    holes = []

    for interior in polygon.interiors:

        hole = []

        for x, y in interior.coords:

            lon, lat = transformer.transform(
                x,
                y
            )

            hole.append(
                [lon, lat]
            )

        holes.append(hole)


    return {
        "type": "Polygon",
        "coordinates": [
            exterior,
            *holes
        ]
    }


def transform_geometry(geometry):

    if geometry.geom_type == "Polygon":

        return transform_polygon(
            geometry
        )


    elif geometry.geom_type == "MultiPolygon":

        polygons = []

        for polygon in geometry.geoms:

            polygons.append(
                transform_polygon(
                    polygon
                )["coordinates"]
            )


        return {
            "type": "MultiPolygon",
            "coordinates": polygons
        }


    else:

        raise ValueError(
            "Unsupported geometry type: "
            + geometry.geom_type
        )


catchment_geometry = transform_geometry(
    catchment_polygon
)


# ============================================================
# 9. GET POND LOCATION
# ============================================================

pond_x = grid_x[
    pond_row,
    pond_col
]

pond_y = grid_y[
    pond_row,
    pond_col
]


pond_longitude, pond_latitude = (
    transformer.transform(
        pond_x,
        pond_y
    )
)


pond_elevation = dem[
    pond_row,
    pond_col
]


print()
print("Pond location:")
print("X:", pond_x)
print("Y:", pond_y)
print("Latitude:", pond_latitude)
print("Longitude:", pond_longitude)
print("Elevation:", pond_elevation)


# ============================================================
# 10. CREATE GEOJSON
# ============================================================

geojson = {

    "type": "FeatureCollection",

    "features": [

        # ----------------------------------------------------
        # Catchment polygon
        # ----------------------------------------------------

        {
            "type": "Feature",

            "properties": {

                "feature_type": "catchment",

                "area_m2": float(
                    catchment_area_m2
                ),

                "area_hectares": float(
                    catchment_area_hectares
                )
            },

            "geometry": catchment_geometry
        },


        # ----------------------------------------------------
        # Pond point
        # ----------------------------------------------------

        {
            "type": "Feature",

            "properties": {

                "feature_type": "pond",

                "elevation_m": float(
                    pond_elevation
                )
            },

            "geometry": {

                "type": "Point",

                "coordinates": [

                    float(pond_longitude),

                    float(pond_latitude)
                ]
            }
        }
    ]
}


# ============================================================
# 11. SAVE GEOJSON
# ============================================================

with open(
    OUTPUT_FILE,
    "w"
) as f:

    json.dump(
        geojson,
        f,
        indent=2
    )


print()
print("===================================")
print("GeoJSON created successfully")
print("===================================")

print("File:", OUTPUT_FILE)

print(
    "Catchment area:",
    f"{catchment_area_m2:.2f} m²"
)

print(
    "Catchment area:",
    f"{catchment_area_hectares:.4f} hectares"
)

print(
    "Pond:",
    pond_latitude,
    pond_longitude
)

print()
print(
    "Google Maps:"
)

print(
    f"https://www.google.com/maps?q="
    f"{pond_latitude},{pond_longitude}"
)