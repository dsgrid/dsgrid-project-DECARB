"""
Create county-to-EMM map using duckdb-queried total residential and commercial electricity from StandardScenarios
Created on 07/25/24

Queried result on Kestrel: /projects/dsgrid/data-StandardScenario/buildstock_county_emm_map/building_total_electricity_by_county.csv
"""
from pathlib import Path

import pandas as pd

here = Path(__file__).parent.absolute()
ss_repo = here.parents[2] / "dsgrid-project-StandardScenarios"


def main():
    dtypes = {"from_id":str, "to_id": str}
    load_file = here / "data" / "building_total_electricity_by_county.csv"
    load = pd.read_csv(load_file)
    county_emm_map = pd.read_csv(here.parent / "dimension_mappings" / "lookup_county_to_emm.csv", dtype=dtypes)

    # convert dataset counties to project counties
    county_map_res_file = ss_repo / "dsgrid_project" / "datasets" / "modeled" / "resstock" / "dimension_mappings" / "county_to_county.csv"
    county_map_com_file = ss_repo / "dsgrid_project" / "datasets" / "modeled" / "comstock" / "dimension_mappings" / "county_to_county.csv"
    county_map_res = pd.read_csv(county_map_res_file, dtype=dtypes)
    county_map_com = pd.read_csv(county_map_com_file, dtype=dtypes)

    county_map = pd.concat([county_map_res, county_map_com], axis=0).drop_duplicates()
    assert county_map["from_id"].duplicated().sum() == 0, f'duplicated from_id in county_map \n{county_map.loc[county_map["from_id"].duplicated()]}'
    key_diff = set(load["geography"])-set(county_map["from_id"])
    assert key_diff == set(), f"county_map is missing mapping for geography: {key_diff}"

    load["county"] = load["geography"].map(county_map.set_index("from_id")["to_id"])
    load = load.loc[~load["county"].isna()].reset_index(drop=True)
    key_diff = set(county_emm_map["from_id"]) -set(load["county"])
    # 48301 = G4803010, not available in ResStock and have no load in ComStock
    assert key_diff == {'48301'}, f"load geography is missing unexpected counties other than 48301 compared to county_emm_map: {key_diff}"

    # create emm-to-county disaggregation map
    county_emm_map.columns = ["to_id", "from_id"]
    county_emm_map["from_fraction"] = county_emm_map["to_id"].map(load.set_index("county")["total_electricity"]).fillna(0)
    county_emm_map.groupby("from_id")["from_fraction"].apply(lambda x: x/x.sum())
    county_emm_map["from_fraction"] = (county_emm_map.set_index("from_id")["from_fraction"] / county_emm_map.groupby("from_id")["from_fraction"].sum()).values
    assert county_emm_map.groupby("from_id")["from_fraction"].sum().round(5).unique().tolist() == [1], "from fraction does not equal to 1 when grouped by from_id"
    
    # export
    county_emm_map = county_emm_map[["from_id", "to_id", "from_fraction"]]
    output_file = here.parents[1] / "datasets" / "modeled" / "buildings" / "dimension_mappings" / "emm_region_to_county.csv"
    county_emm_map.to_csv(output_file, index=False)
    print(f"Using building electricity file:\n{load_file}, \ncreated mapping file:\n{output_file}.")


if __name__ == "__main__":
    main()
