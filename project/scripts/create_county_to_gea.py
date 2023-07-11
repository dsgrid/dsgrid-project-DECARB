from pathlib import Path

import pandas as pd

here = Path(__file__).parent.absolute()

if __name__ == "__main__":
    # Data table transcribed from https://www.nrel.gov/docs/fy23osti/84916.pdf, Table 12
    gea_to_pca = pd.read_csv(here / "data" / "gea_to_pca.csv",header=0)
    
    geas = set(gea_to_pca["gea"].tolist())
    assert len(geas) == 20

    pcas = set(gea_to_pca["pca"].tolist())
    assert len(pcas) == 134
    assert len(pcas) == len(gea_to_pca.index)

    county_to_reeds_pca = pd.read_csv(here.parent / "dimension_mappings" / "lookup_county_to_reeds_pca.csv")
    other_pcas = set(county_to_reeds_pca["to_id"].tolist())
    assert pcas == other_pcas

    result = county_to_reeds_pca.merge(gea_to_pca,how="left",left_on="to_id",right_on="pca")
    result = result[["from_id","gea"]]
    result.columns = ["from_id","to_id"]
    p = here.parent / "dimension_mappings" / "lookup_county_to_cambium_gea.csv"
    print(f"Writing:\n{result}\nto {p}.")
    result.to_csv(p,index=False)
