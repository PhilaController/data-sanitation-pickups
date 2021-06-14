import json
import sys
from datetime import datetime
from pathlib import Path

import geopandas as gpd
import numpy as np
from arcgis2geojson import arcgis2geojson


def to_datetime(x):
    if np.isnan(x):
        return x
    else:
        return datetime.fromtimestamp(int(x / 1000))


if __name__ == "__main__":

    # Get the data path
    script_name, data_file = sys.argv

    # Load the raw data
    json = json.load(Path(data_file).open("r"))

    # Fix ESRI geometries and initialize GeoDataFrame
    geojson = [arcgis2geojson(f) for f in json["features"]]
    gdf = gpd.GeoDataFrame.from_features(geojson, crs="EPSG:4326")

    # Fix dates
    for col in ["recycling_time_visited", "rubbish_time_visited"]:
        gdf[col] = gdf[col].apply(to_datetime)

    # Save
    gdf.to_csv("data-processed.csv", index=False)

