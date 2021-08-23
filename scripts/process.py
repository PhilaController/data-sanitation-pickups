from datetime import datetime
from pathlib import Path

import esri2gpd
import geopandas as gpd
import numpy as np
import pandas as pd
from loguru import logger
from sklearn.neighbors import NearestNeighbors

CWD = Path(__file__).resolve().parent
DATA_DIR = CWD / ".." / "data"

EPSG = 2272


def _to_datetime(x):
    """Utility to convert to datetime from timestamp."""
    if np.isnan(x):
        return x
    else:
        return datetime.fromtimestamp(int(x / 1000))


def _get_xy_from_geometry(df):
    """
    Return a numpy array with two columns, where the
    first holds the `x` geometry coordinate and the second
    column holds the `y` geometry coordinate
    """
    # NEW: use the centroid.x and centroid.y to support Polygon() and Point() geometries
    x = df.geometry.centroid.x
    y = df.geometry.centroid.y

    return np.column_stack((x, y))


def query_latest_data():
    """Pull the latest daily data from the StreetSmart API."""

    # Query the latest data for StreetSmart API
    ENDPOINT = "https://services.arcgis.com/fLeGjb7u4uXqeF9q/arcgis/rest/services/StreetSmartPHL/FeatureServer"
    LAYER = 8
    gdf = esri2gpd.get(f"{ENDPOINT}/{LAYER}").to_crs(epsg=EPSG)

    # Fix dates
    for col in ["recycling_time_visited", "rubbish_time_visited"]:
        gdf[col] = gdf[col].apply(_to_datetime)

    return gdf


def load_street_centerlines():
    """Load the processed street centerlines."""
    return gpd.read_file(DATA_DIR / "processed" / "street-centerlines.gpkg")


if __name__ == "__main__":

    # STEP 1: Get the latest data
    latest = query_latest_data()
    latest.to_file(DATA_DIR / "raw" / "latest-data.geojson", driver="GeoJSON")

    # STEP 2: Load the processed streets
    streets = load_street_centerlines()

    streetsXY = _get_xy_from_geometry(streets)
    latestXY = _get_xy_from_geometry(latest)

    # STEP 1: Initialize the algorithm
    nbrs = NearestNeighbors(n_neighbors=1)

    # STEP 2: Fit the algorithm on the "neighbors" dataset
    nbrs.fit(streetsXY)

    # STEP 3: Get distances for sale to neighbors
    dists, indices = nbrs.kneighbors(latestXY)

    latest["index_right"] = indices.squeeze()
    latest["dist"] = dists.squeeze()

    latest_lengths = latest.geometry.length.values
    all_lengths = streets.loc[indices.squeeze()].geometry.length.values
    latest["len_diff"] = latest_lengths - all_lengths

    merged = pd.merge(
        latest,
        streets.reset_index()[["index", "segment_id"]],
        left_on="index_right",
        right_on="index",
        how="left",
    )
    assert len(merged) == len(latest)

    DIST_CUTOFF = 10
    LEN_CUTOFF = 10
    matched = (merged["dist"].abs() < DIST_CUTOFF) & (
        (merged["len_diff"].abs() < LEN_CUTOFF)
    )

    # Log the matched segments
    num_matches = matched.sum()
    f = num_matches / len(latest)
    logger.info(f"Matched {num_matches} out of {len(latest)} ({100*f:.0f}%)")

    # Save the missing segments
    missing = (
        merged.loc[~matched]
        .copy()[["geometry"]]
        .reset_index()
        .rename(columns={"index": "segment_id"})
    )
    missing["segment_id"] += streets["segment_id"].max() + 1
    new_streets = pd.concat([streets, missing], axis=0, ignore_index=True)

    # STEP 4: Save the new streets
    new_streets.to_file(
        DATA_DIR / "processed" / "street-centerlines.gpkg",
        driver="GPKG",
        layer="data",
    )

    # Set the segment id
    merged.loc[~matched, "segment_id"] = missing["segment_id"].values

    # STEP 5: Save the new streets to a GeoJSON file
    merged[list(latest.columns) + ["segment_id"]].drop(
        labels=["geometry", "OBJECTID", "dist", "len_diff", "index_right"],
        axis=1,
        errors="ignore",
    ).to_csv(DATA_DIR / "processed" / "daily-data-combined.csv", index=False)
