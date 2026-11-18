# Map to Our Clinic — source

`../map-to-clinic.webp` is built from OpenStreetMap data with the original hand-drawn directions
(`../map.jpg`) redrawn on top at the same positions. Same framing as the original graphic (1253×810).

- `build_map.py`: draws the basemap (roads, buildings, parks, labels) from an OSM extract and adds the
  directions layer: callout text, arrows, dashed route, "Veer Left", end dot, NES box, playing fields and
  Grampians Reserve. Modes: `final` (the map), `compare` (directions in red over the original, for checking
  alignment), `ann` (directions only).
- `fit.json`: Web Mercator zoom-17 scale and offset that put OSM coordinates on the original graphic's pixels
  (fitted on the Franklyn St × Waimea Rd and Franklyn St × Braemar Pl intersections).
- `wordmark.png`: the NES wordmark cut from the logo, used inside the box.
- `render.mjs`: rasterises the generated HTML with the project's puppeteer (run from the project root).
- `map-to-clinic.svg`: the vector master. It needs Didact Gothic, Jost and Urbanist (Google Fonts) to display as intended.

## Rebuild

```sh
# 1. OSM extract (one request; keep the "© OpenStreetMap contributors" credit on the map)
curl -sS -A "static-map-builder/1.0" -o /tmp/area.json https://overpass-api.de/api/interpreter --data-urlencode 'data=[out:json][timeout:60];
(way["highway"](-41.2945,173.2640,-41.2805,173.2870);way["building"](-41.2945,173.2640,-41.2805,173.2870);
 way["landuse"](-41.2945,173.2640,-41.2805,173.2870);way["leisure"](-41.2945,173.2640,-41.2805,173.2870);
 way["amenity"](-41.2945,173.2640,-41.2805,173.2870);way["natural"](-41.2945,173.2640,-41.2805,173.2870);
 node["name"](-41.2945,173.2640,-41.2805,173.2870););out geom;'

# 2. Build and render at 2x, then save ~1880px wide as WebP (quality 86)
python3 -I resources/site-images/map-source/build_map.py /tmp/area.json resources/site-images/map-source/fit.json \
  resources/site-images/map-source/wordmark.png resources/site-images/map.jpg /tmp final
node resources/site-images/map-source/render.mjs /tmp/map-final.html /tmp/map-2x.png 2
```

Street labels keep the original graphic's wording. OSM names two of those roads differently: the "Corgarff Pl"
branch is part of Braemar Place in OSM, and the road labelled "Ngatitama St" is unnamed there.
