# Copernicus GLO-30 DTE to DTED transformer
Downloads Copernicus GLO-30 DTE from AWS and transforms to DTED suitable for ATAK (*Android Team Awareness Kit*)

## Data source
https://registry.opendata.aws/copernicus-dem

## Dependencies

* python3
* gdal
* gdal-python-tools


**For Fedora users**
``` bash
sudo dnf update && dnf install python3 gdal gdal-python-tools
```

## How to run

``` bash
python cop30_to_dted.py --lat_min 53 --lat_max 57 --lon_min 20 --lon_max 27 --output ./DTED_Location
```

## Geometry and Padding

The Copernicus DEM data is sourced from AWS as Cloud Optimized GeoTIFFs (COG). There is a critical difference between the AWS storage format and the DTED Level 2 specification:

#### The "Missing Pixel" Issue
* **Standard DEMs**: Usually include a shared boundary row/column (e.g., $3601 \times 3601$).
* **AWS COGs**: To optimize for tiling and "power of two" overviews, AWS removed the shared rows/columns on the East and South edges. For example, a $3601 \times 3601$ tile is stored on AWS as $3600 \times 3600$.
* **DTED Requirement**: The DTED driver (and the MIL-SPEC) strictly requires the $3601$st pixel to define the boundary. Without it, the tile is technically "malformed" for Level 2 and will show gaps between adjacent tiles.

#### The Solution
This script automatically "heals" the AWS data during conversion:
* **Expansion**: It uses `gdal_translate` to force the output dimensions back to the required size (e.g., $3601 \times 3601$).
* **Edge Padding**: It assigns a temporary `NoData` value to the newly created "empty" bottom/right pixels.
* **Filling**: It uses `gdal_fillnodata.py` to smear the elevation values from the $3600$th row into the $3601$th row. This ensures a seamless transition between tiles without introducing artificial "cliffs" or zero-elevation pits.

