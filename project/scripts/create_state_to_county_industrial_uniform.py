"""
Used to create dummy mapping, 1/N uniform distribution for industrial dataset's "state_to_county_industrial.csv"
"""
from pathlib import Path

import pandas as pd

decarb_dir = Path(__file__).parents[2].absolute()

def main():
    state_file =  decarb_dir / "datasets" / "modeled" / "industry" / "dimensions" / "states.csv"
    county_file = decarb_dir / "project" / "dimensions" / "counties.csv"
    state_to_county_file = decarb_dir / "datasets" / "modeled" / "industry" / "dimension_mappings" / "state_to_county_industrial.csv"

    df = pd.read_csv(county_file,header=0)
    col_rename = {"state": "from_id", "id": "to_id"}
    df = df.rename(columns=col_rename)[col_rename.values()]

    df["from_fraction"] = 1
    df["from_fraction"] = df.groupby("from_id")["from_fraction"].transform(lambda x: x/x.sum()).round(8)

    # Check
    df.groupby("from_id")["from_fraction"].sum().round(5).unique().tolist() == [1], "from fraction does not equal to 1 when grouped by from_id"
    df_state = pd.read_csv(state_file)
    diff = set(df["from_id"].unique()) - set(df_state["id"].to_list())
    assert len(diff) == 0, f"from_id has states not in dimension record: \n{diff}"
    
    # Format and export
    df["to_id"] = df["to_id"].astype(str).str.zfill(5)
    df.to_csv(state_to_county_file, index=False)
    print(f"Mapping file created: {state_to_county_file}")


if __name__ == "__main__":
    main()

