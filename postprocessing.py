import json
import sys
from datetime import datetime
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from arcgis2geojson import arcgis2geojson


def to_datetime(x):
    if np.isnan(x):
        return x
    else:
        return datetime.fromtimestamp(int(x / 1000))


def get_latest_processed_data():

    # Get the data path
    script_name, data_file = sys.argv

    # Load the raw data
    j = json.load(Path(data_file).open("r"))

    # Fix ESRI geometries and initialize GeoDataFrame
    geojson = [arcgis2geojson(f) for f in j["features"]]
    gdf = gpd.GeoDataFrame.from_features(geojson, crs="EPSG:4326")

    # Fix dates
    for col in ["recycling_time_visited", "rubbish_time_visited"]:
        gdf[col] = gdf[col].apply(to_datetime)

    return gdf


def get_geometry(gdf):

    filename = Path("streets.geojson")

    # Merge together
    if filename.exists():
        gdf = pd.concat([gpd.read_file(filename), gdf])

    # Remove duplicates and save
    gdf = gdf.drop_duplicates().sort_values("OBJECTID")
    gdf.to_file(filename, driver="GeoJSON")


def save_combined_database(gdf):

    filename = Path("daily-data-combined.csv")

    # Merge together
    if filename.exists():
        gdf = pd.concat([gdf, pd.read_csv(filename)])

    # Remove duplicates and save
    gdf = gdf.drop_duplicates()
    gdf.to_csv(filename, index=False)


if __name__ == "__main__":

    # Get latest processed
    gdf = get_latest_processed_data()

    # Get geometry
    geo = get_geometry(gdf[["geometry", "OBJECTID"]])

    # Save latest without geometry
    COLS = [
        "OBJECTID",
        "visited_status",
        "recycling_time_visited",
        "rubbish_time_visited",
    ]
    assert all(col in gdf.columns for col in COLS)
    gdf[COLS].to_csv("latest-data-processed.csv", index=False)

    # Combine with past
    save_combined_database(gdf[COLS])

