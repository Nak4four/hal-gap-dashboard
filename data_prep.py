"""
data_prep.py  —  Builds the dashboard-ready dataset for the
Lifespan vs. Healthspan (LE - HALE gap) project.

CORE METRIC:  gap = life_expectancy - healthy_life_expectancy
              ("years lived in poor health"), per country x year.

SOURCES (all free, public, fetched live):
  - HALE at birth, both sexes ....... WHO Global Health Observatory (via Our World in Data)
  - Life expectancy at birth ........ UN World Population Prospects / HMD (via Our World in Data)
  - Life expectancy by sex .......... UN WPP (via Our World in Data)  -> gender layer

NOTE ON SOURCES (documented limitation): HALE is from WHO GHO; the
companion life-expectancy series is UN WPP. Both are period estimates
at birth and track each other closely, but they are not the same
producer, so the gap carries a small cross-source caveat. WHO does not
publish a HALE-by-sex series on OWID, so the gender layer uses LE by sex.

This script must run in an environment with internet access (e.g. the
local machine or Streamlit Community Cloud). The sandbox used to draft
the project cannot reach the data hosts, which is why the file is built
at deploy/run time rather than committed as static rows.
"""

import pandas as pd

OWID = "https://ourworldindata.org/grapher/{slug}.csv?v=1&csvType=full&useColumnShortNames=false"
UA = {"User-Agent": "MSBA382 HALE-gap project data fetch/1.0"}

# Eastern Mediterranean / MENA focus list (ISO3) for the regional lens
MENA_ISO3 = {
    "BHR","DJI","EGY","IRN","IRQ","JOR","KWT","LBN","LBY","MAR","OMN",
    "PSE","QAT","SAU","SDN","SOM","SYR","TUN","ARE","YEM",
}

def _fetch(slug, value_name):
    df = pd.read_csv(OWID.format(slug=slug), storage_options=UA)
    # the indicator column is the 4th column; rename it cleanly
    val_col = df.columns[-1]
    df = df.rename(columns={val_col: value_name, "Entity": "entity", "Code": "iso3", "Year": "year"})
    return df[["entity", "iso3", "year", value_name]]

def build(start_year=2000, end_year=2021):
    hale = _fetch("healthy-life-expectancy-at-birth", "hale")
    le   = _fetch("life-expectancy", "life_exp")
    le_m = _fetch("mens-life-expectancy-at-birth", "life_exp_male")
    le_f = _fetch("womens-life-expectancy-at-birth", "life_exp_female")

    df = (hale
          .merge(le,   on=["entity", "iso3", "year"], how="inner")
          .merge(le_m, on=["entity", "iso3", "year"], how="left")
          .merge(le_f, on=["entity", "iso3", "year"], how="left"))

    df = df[(df.year >= start_year) & (df.year <= end_year)].copy()

    # CORE metric and the gendered gap
    df["gap"]        = (df["life_exp"]        - df["hale"]).round(2)
    df["gap_male"]   = (df["life_exp_male"]   - df["hale"]).round(2)   # HALE both-sexes (see caveat)
    df["gap_female"] = (df["life_exp_female"] - df["hale"]).round(2)
    df["le_sex_gap"] = (df["life_exp_female"] - df["life_exp_male"]).round(2)

    # geography flags: WHO aggregate rows have no ISO3; real countries do
    df["is_aggregate"] = df["iso3"].isna() | df["entity"].str.contains(r"\(WHO\)", na=False)
    df["mena"] = df["iso3"].isin(MENA_ISO3)

    for c in ["hale", "life_exp"]:
        df[c] = df[c].round(2)

    df = df.sort_values(["entity", "year"]).reset_index(drop=True)
    cols = ["entity","iso3","year","life_exp","hale","gap",
            "life_exp_male","life_exp_female","gap_male","gap_female","le_sex_gap",
            "mena","is_aggregate"]
    return df[cols]

if __name__ == "__main__":
    data = build()
    data.to_csv("hale_le_gap.csv", index=False)
    print(f"Wrote hale_le_gap.csv  ->  {len(data):,} rows, "
          f"{data.entity.nunique()} entities, "
          f"years {int(data.year.min())}-{int(data.year.max())}")
    print(data[data.mena & (data.year == 2021)]
          [["entity","life_exp","hale","gap"]].to_string(index=False))
