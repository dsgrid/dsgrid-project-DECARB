from pathlib import Path

import pandas as pd

here = Path(__file__).absolute().parent
decarb_dir = here.parents[1]

# Description of the data file from 12/8/2023 email from Colin McMillan to Anna Schleifer:
#     Here’s the file for county-level estimates of electricity demand by manufacturing NAICS code 
#     for 2014. The data come from our 2018 Industrial Energy Databook. Some additional processing 
#     has been done to fix a handful of duplicate entries and for general clean-up. Note that these 
#     estimates are for net electricity (the sum of purchased electricity, transfers in, and 
#     generation from noncombustible renewable resources minus the quantities of electricity sold 
#     and transferred offsite). There are industries in counties that have negative values for net 
#     electricity; these represent cases where large facilities with their own generation (e.g., 
#     petroleum refineries) are selling more electricity to the grid than they purchase.
#
# Note that an updated dataset that includes behind-the-meter generation estimates is currently 
# being compiled. Once that is ready, it could be used instead if the estimates from LBNL are 
# inclusive of all electricity use.
# Used to create industrial dataset's "state_to_county_industrial.csv"

def main():
    # dsgrid files
    county_file = decarb_dir / "project" / "dimensions" / "counties.csv"
    state_to_county_file = decarb_dir / "datasets" / "modeled" / "industry" / "dimension_mappings" / "state_to_county_industrial.csv"

    # Helper files
    mfg_file = here / "data" / "annual_mfg_electricity_all_counties.csv"
    state_fips_file = here / "data" / "states_fips.csv" # retrieved: https://gist.github.com/aodin/24c30ba793e404a0270f8c8ef2be350b#file-states_fips-csv

    # Create mapping based on historical loads
    df = pd.read_csv(mfg_file, dtype={"FIPSTATE": str, "COUNTY_FIPS": str})
    df = df.groupby(["FIPSTATE","COUNTY_FIPS"])["MWH_TOTAL"].sum().reset_index()
    df = df.merge(df.groupby("FIPSTATE")["MWH_TOTAL"].sum(), on="FIPSTATE", suffixes=("_county", "_state"))
    df["from_fraction"] = df["MWH_TOTAL_county"].divide(df["MWH_TOTAL_state"])

    # Fix county fips and rename to_id
    n_df = len(df)
    # 2014 name change: Shannon County, SD (46113) -> Oglala Lakota County, SD (46102)
    # 2013 merging: Bedford City, VA (51515) merged into Bedford County, VA (51019)
    df["COUNTY_FIPS"] = df["COUNTY_FIPS"].replace({
        "46113": "46102",
        "51515": "51019",
        })
    df = df.groupby(["FIPSTATE", "COUNTY_FIPS"])["from_fraction"].sum().reset_index()
    assert len(df)+1 == n_df, "expecting reduction by 1 row after county fips correction"
    df = df.rename(columns={"COUNTY_FIPS": "to_id"})

    # Map state fips to abbrev and rename from_id
    state_fips = pd.read_csv(state_fips_file, dtype={"FIPS": str})
    state_fips["FIPS"] = state_fips["FIPS"].str.zfill(2)
    df["from_id"] = df["FIPSTATE"].map(state_fips.set_index("FIPS")["Postal"])
    df_na = df.loc[df.isna().any(axis=1)]
    assert len(df_na)==0, f"df has na values: {df_na}"
    df = df.drop(columns=["FIPSTATE"])

    # Create mapping from/to_id from county dimension file
    df2 = pd.read_csv(county_file, dtype={"id": str})
    df2["id"] = df2["id"].str.zfill(5)
    col_rename = {"state": "from_id", "id": "to_id"}
    df2 = df2.rename(columns=col_rename)[col_rename.values()]
    df3 = pd.merge(df2, df, on=["from_id", "to_id"], how="left")

    # Check that all unmapped counties from df are outside the project's states
    unmapped_counties = set(df["to_id"].unique()) - set(df2["to_id"])
    unmapped_state_fips = {x[:2] for x in unmapped_counties}
    diff = set(df2["from_id"].unique()).intersection(set(state_fips.loc[state_fips["FIPS"].isin(unmapped_state_fips), "Postal"].to_list()))
    assert diff == set(), f"Unmapped counties belong to project states={diff}"

    # Fillna
    no_load_counties = set(df2["to_id"]) - set(df["to_id"].unique())
    print(f"{len(no_load_counties)} counties have no loads, filling with 0")
    df3["from_fraction"] = df3["from_fraction"].fillna(0)
    df_na = df3.loc[df3.isna().any(axis=1)]
    assert len(df_na)==0, f"df3 has na values: {df_na}"

    # QC and export
    assert len(df2[["from_id", "to_id"]].compare(df3[["from_id", "to_id"]]))==0, "mapping does not have the expected rows."
    assert df3.groupby("from_id")["from_fraction"].sum().round(5).unique().tolist() == [1], "from fraction does not equal to 1 when grouped by from_id"
    df3.to_csv(state_to_county_file, index=False)
    print(f"Mapping file created: {state_to_county_file}")


if __name__ == "__main__":
    main()
