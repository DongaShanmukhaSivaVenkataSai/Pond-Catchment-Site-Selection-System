import xml.etree.ElementTree as ET
import json

NAMESPACE = {
    "kml": "http://www.opengis.net/kml/2.2"
}

tree = ET.parse("contours_1m.kml")
root = tree.getroot()

placemarks = root.findall(".//kml:Placemark", NAMESPACE)

contours = []

for placemark in placemarks:

    # 2. ID
    id_element = placemark.find(
        ".//kml:SimpleData[@name='ID']",
        NAMESPACE
    )
    if id_element is None or id_element.text is None:
        continue

    contour_id = int(id_element.text)

    # 1. Elevation
    name = placemark.find("kml:name", NAMESPACE)
    elevation = float(name.text) if (name is not None and name.text) else 0.0

    # 3. Coordinates
    coordinates_element = placemark.find(
        ".//kml:coordinates",
        NAMESPACE
    )

    if coordinates_element is None or not coordinates_element.text:
        continue

    coordinates_text = coordinates_element.text.strip()

    points = []

    for point in coordinates_text.split():

        parts = point.split(",")
        if len(parts) >= 2:
            lon, lat = parts[0], parts[1]

            points.append([
                float(lon),
                float(lat)
            ])

    # 4. Store contour
    contour = {
        "id": contour_id,
        "elevation": elevation,
        "coordinates": points
    }

    contours.append(contour)


# Save parsed data
with open("contours.json", "w") as f:
    json.dump(contours, f, indent=2)


print("Total contours:", len(contours))
print("Saved parsed data to contours.json")


for contour in contours[:5]:

    print("\nContour")
    print("ID:", contour["id"])
    print("Elevation:", contour["elevation"])
    print("Number of points:", len(contour["coordinates"]))
    print("First point:", contour["coordinates"][0])