from pathlib import Path

import esri2gpd

CWD = Path(__file__).resolve().parent
DATA_DIR = CWD / ".." / "data"

API = "https://services.arcgis.com/fLeGjb7u4uXqeF9q/arcgis/rest/services/Street_Centerline/FeatureServer"
LAYER_ID = 0
EPSG = 2272

if __name__ == "__main__":

    # Download the raw data
    df = esri2gpd.get(f"{API}/{LAYER_ID}").to_crs(epsg=EPSG)

    # Save the raw data
    df.to_file(
        DATA_DIR / "raw" / "street-centerlines.gpkg",
        driver="GPKG",
        layer="data",
    )

    # Process the raw data
    df.reset_index().rename(
        columns={
            "index": "segment_id",
            "STNAME": "street_name",
            "RESPONSIBL": "responsible",
            "L_HUNDRED": "l_hundred",
            "R_HUNDRED": "r_hundred",
            "L_F_ADD": "l_f_add",
            "R_F_ADD": "r_f_add",
            "L_T_ADD": "l_t_add",
            "R_T_ADD": "r_t_add",
        }
    )[
        [
            "segment_id",
            "street_name",
            "responsible",
            "l_hundred",
            "r_hundred",
            "l_f_add",
            "r_f_add",
            "l_t_add",
            "r_t_add",
            "geometry",
        ]
    ].to_file(
        DATA_DIR / "processed" / "street-centerlines.gpkg",
        driver="GPKG",
        layer="data",
    )
