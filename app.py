"""
Lifespan vs. Healthspan — the Healthy Life Expectancy Gap
MSBA382 Healthcare Analytics · Individual Project · Streamlit dashboard

Core metric:  gap = life expectancy (LE) - healthy life expectancy (HALE)
              = the years a person lives in poor health.

Data is built live from Our World in Data (WHO GHO + UN WPP) and cached,
so the app is self-contained on Streamlit Community Cloud. If a local
hale_le_gap.csv exists (built by data_prep.py) it is used instead.
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Lifespan vs. Healthspan",
                   page_icon="🫀", layout="wide")

# --------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------
OWID = "https://ourworldindata.org/grapher/{slug}.csv?v=1&csvType=full&useColumnShortNames=false"
UA = {"User-Agent": "MSBA382 HALE-gap project/1.0"}

MENA_ISO3 = {"BHR","DJI","EGY","IRN","IRQ","JOR","KWT","LBN","LBY","MAR",
             "OMN","PSE","QAT","SAU","SDN","SOM","SYR","TUN","ARE","YEM"}

def _fetch(slug, name):
    df = pd.read_csv(OWID.format(slug=slug), storage_options=UA)
    df = df.rename(columns={df.columns[-1]: name,
                            "Entity": "entity", "Code": "iso3", "Year": "year"})
    return df[["entity", "iso3", "year", name]]

@st.cache_data(ttl=60 * 60 * 24)
def load_data(start=2000, end=2021):
    # prefer a pre-built file if present
    try:
        df = pd.read_csv("hale_le_gap.csv")
        return df
    except Exception:
        pass
    hale = _fetch("healthy-life-expectancy-at-birth", "hale")
    le   = _fetch("life-expectancy", "life_exp")
    df = hale.merge(le, on=["entity", "iso3", "year"], how="inner")
    # gender layer (degrade gracefully if a slug changes)
    try:
        m = _fetch("mens-life-expectancy-at-birth", "life_exp_male")
        f = _fetch("womens-life-expectancy-at-birth", "life_exp_female")
        df = df.merge(m, on=["entity","iso3","year"], how="left") \
               .merge(f, on=["entity","iso3","year"], how="left")
    except Exception:
        df["life_exp_male"] = np.nan
        df["life_exp_female"] = np.nan

    df = df[(df.year >= start) & (df.year <= end)].copy()
    df["gap"]        = (df.life_exp - df.hale).round(2)
    df["le_sex_gap"] = (df.life_exp_female - df.life_exp_male).round(2)
    df["is_aggregate"] = df.iso3.isna() | df.entity.str.contains(r"\(WHO\)", na=False)
    df["mena"] = df.iso3.isin(MENA_ISO3)
    df[["hale","life_exp"]] = df[["hale","life_exp"]].round(2)
    return df.sort_values(["entity","year"]).reset_index(drop=True)

# --------------------------------------------------------------------------
# Password gate (simple landing page)
# --------------------------------------------------------------------------
def check_password():
    try:
        correct = st.secrets.get("password", "healthspan2026")
    except Exception:
        correct = "healthspan2026"
    if st.session_state.get("auth_ok"):
        return True
    st.markdown("<h1 style='text-align:center'>🫀 Lifespan vs. Healthspan</h1>",
                unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;color:gray'>"
                "The Healthy Life Expectancy Gap — years lived in poor health.<br>"
                "Enter the access password to continue.</p>", unsafe_allow_html=True)
    c = st.columns([1, 1, 1])[1]
    with c:
        pw = st.text_input("Password", type="password", label_visibility="collapsed",
                           placeholder="Password")
        if pw:
            if pw == correct:
                st.session_state.auth_ok = True
                st.rerun()
            else:
                st.error("Incorrect password.")
    return False

if not check_password():
    st.stop()

df = load_data()
countries = df[~df.is_aggregate]
LATEST = int(df.year.max())

# --------------------------------------------------------------------------
# Sidebar
# --------------------------------------------------------------------------
st.sidebar.title("Controls")
year = st.sidebar.slider("Year", int(df.year.min()), LATEST, LATEST)
scope = st.sidebar.radio("Country scope", ["All countries", "MENA only"])
st.sidebar.caption("Lifespan = life expectancy (LE). "
                   "Healthspan = healthy life expectancy (HALE). "
                   "Gap = LE − HALE.")
st.sidebar.caption("Sources: WHO GHO (HALE) & UN WPP (LE), via Our World in Data. "
                   "HALE and LE are different producers — small cross-source caveat.")

scoped = countries[countries.mena] if scope == "MENA only" else countries

# --------------------------------------------------------------------------
# Header + KPIs
# --------------------------------------------------------------------------
st.title("Lifespan vs. Healthspan")
st.markdown("**The Healthy Life Expectancy Gap** — how many years people live, "
            "versus how many they live in good health.")

wrow = df[(df.entity == "World") & (df.year == year)]
cy = scoped[scoped.year == year]
k1, k2, k3, k4 = st.columns(4)
if not wrow.empty:
    k1.metric("World life expectancy", f"{wrow.life_exp.iloc[0]:.1f} yrs")
    k2.metric("World healthy life expectancy", f"{wrow.hale.iloc[0]:.1f} yrs")
    k3.metric("World gap", f"{wrow.gap.iloc[0]:.1f} yrs",
              help="Years lived in poor health")
if not cy.empty:
    hi = cy.loc[cy.gap.idxmax()]
    k4.metric(f"Widest gap ({scope.lower()})", f"{hi.gap:.1f} yrs", hi.entity)

tab_map, tab_trend, tab_rank, tab_gender, tab_mena, tab_fc = st.tabs(
    ["🗺️ Map", "📈 Trends", "📊 Ranking", "⚥ Gender", "🌍 MENA focus", "🔮 Forecast"])

# --------------------------------------------------------------------------
# Map
# --------------------------------------------------------------------------
with tab_map:
    st.subheader(f"The gap across the world — {year}")
    mp = countries[countries.year == year].dropna(subset=["iso3"])
    fig = px.choropleth(mp, locations="iso3", color="gap", hover_name="entity",
                        color_continuous_scale="OrRd", range_color=(5, 15),
                        labels={"gap": "Gap (yrs)"})
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=480,
                      coloraxis_colorbar_title="Gap<br>(yrs)")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Darker = more years lived in poor health. The gap is wide in much "
               "of the Gulf and parts of the Americas, and narrowest across much of "
               "Sub-Saharan Africa, where shorter lifespans leave less room for it.")

# --------------------------------------------------------------------------
# Trends
# --------------------------------------------------------------------------
with tab_trend:
    st.subheader("Lifespan and healthspan over time")
    opts = sorted(df.entity.unique())
    default = [e for e in ["World", "Eastern Mediterranean (WHO)", "Lebanon", "Japan"]
               if e in opts]
    picks = st.multiselect("Entities", opts, default=default)
    if picks:
        sub = df[df.entity.isin(picks)]
        long = sub.melt(id_vars=["entity", "year"],
                        value_vars=["life_exp", "hale"],
                        var_name="measure", value_name="years")
        long.measure = long.measure.map({"life_exp": "Life expectancy",
                                         "hale": "Healthy life expectancy"})
        fig = px.line(long, x="year", y="years", color="entity",
                      line_dash="measure", markers=False)
        fig.add_vline(x=2020, line_dash="dot", line_color="gray",
                      annotation_text="COVID-19")
        fig.update_layout(height=430, margin=dict(t=10),
                          legend_title_text="", yaxis_title="Years")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Solid = lifespan, dashed = healthspan. The space between the two "
                   "lines is the gap. Note the 2020–21 dip from COVID-19.")

        figg = px.line(sub, x="year", y="gap", color="entity", markers=True)
        figg.add_vline(x=2020, line_dash="dot", line_color="gray")
        figg.update_layout(height=330, margin=dict(t=10), yaxis_title="Gap (yrs)")
        st.markdown("**The gap itself**")
        st.plotly_chart(figg, use_container_width=True)

# --------------------------------------------------------------------------
# Ranking / distribution
# --------------------------------------------------------------------------
with tab_rank:
    st.subheader(f"Where the gap is widest and narrowest — {year}")
    cy2 = scoped[scoped.year == year].dropna(subset=["gap"])
    colA, colB = st.columns(2)
    with colA:
        top = cy2.nlargest(15, "gap").sort_values("gap")
        fig = px.bar(top, x="gap", y="entity", orientation="h",
                     color="gap", color_continuous_scale="OrRd")
        fig.update_layout(height=460, margin=dict(t=10), yaxis_title="",
                          xaxis_title="Gap (yrs)", coloraxis_showscale=False)
        st.markdown("**Widest 15**")
        st.plotly_chart(fig, use_container_width=True)
    with colB:
        fig2 = px.histogram(cy2, x="gap", nbins=25)
        fig2.update_layout(height=460, margin=dict(t=10),
                           xaxis_title="Gap (yrs)", yaxis_title="# countries")
        st.markdown("**Distribution across countries**")
        st.plotly_chart(fig2, use_container_width=True)
        st.caption(f"Median gap: {cy2.gap.median():.1f} yrs · "
                   f"range {cy2.gap.min():.1f}–{cy2.gap.max():.1f} yrs.")

# --------------------------------------------------------------------------
# Gender
# --------------------------------------------------------------------------
with tab_gender:
    st.subheader("The gender pattern")
    if countries.life_exp_female.notna().any():
        cy3 = scoped[(scoped.year == year)].dropna(subset=["le_sex_gap"])
        st.markdown("**Female − male life expectancy** (women almost always live longer)")
        topg = cy3.nlargest(15, "le_sex_gap").sort_values("le_sex_gap")
        fig = px.bar(topg, x="le_sex_gap", y="entity", orientation="h",
                     color="le_sex_gap", color_continuous_scale="Purpor")
        fig.update_layout(height=430, margin=dict(t=10), yaxis_title="",
                          xaxis_title="Extra years women live", coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Women live longer almost everywhere — but the literature shows "
                   "those extra years are often spent in poorer health. HALE is not "
                   "published by sex, so this layer uses life expectancy by sex.")
    else:
        st.info("Sex-disaggregated life expectancy was not available at load time.")

# --------------------------------------------------------------------------
# MENA focus
# --------------------------------------------------------------------------
with tab_mena:
    st.subheader(f"MENA / Eastern Mediterranean — {year}")
    m = countries[countries.mena & (countries.year == year)].dropna(subset=["gap"])
    m = m.sort_values("gap")
    fig = px.bar(m, x="gap", y="entity", orientation="h",
                 color="gap", color_continuous_scale="OrRd")
    fig.update_layout(height=520, margin=dict(t=10), yaxis_title="",
                      xaxis_title="Gap (yrs)", coloraxis_showscale=False)
    st.plotly_chart(fig, use_container_width=True)
    mena_ts = (countries[countries.mena].groupby("year").gap.mean().reset_index())
    world_ts = df[df.entity == "World"][["year", "gap"]].rename(columns={"gap": "World"})
    comp = mena_ts.merge(world_ts, on="year").rename(columns={"gap": "MENA average"})
    fig2 = px.line(comp.melt("year", var_name="series", value_name="gap"),
                   x="year", y="gap", color="series", markers=True)
    fig2.update_layout(height=320, margin=dict(t=10), yaxis_title="Gap (yrs)")
    st.markdown("**MENA average vs. World**")
    st.plotly_chart(fig2, use_container_width=True)

# --------------------------------------------------------------------------
# Forecast (bonus): linear trend on the pre-COVID series
# --------------------------------------------------------------------------
with tab_fc:
    st.subheader("Projecting the gap (simple trend)")
    ent = st.selectbox("Entity", sorted(countries.entity.unique()),
                       index=sorted(countries.entity.unique()).index("Lebanon")
                       if "Lebanon" in countries.entity.values else 0)
    s = df[(df.entity == ent) & (df.year <= 2019)].dropna(subset=["gap"])
    if len(s) >= 5:
        b, a = np.polyfit(s.year, s.gap, 1)            # slope, intercept
        fut = np.arange(2000, 2031)
        pred = a + b * fut
        actual = df[df.entity == ent][["year", "gap"]]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=actual.year, y=actual.gap, mode="markers+lines",
                                 name="Observed"))
        fig.add_trace(go.Scatter(x=fut, y=pred, mode="lines", name="Trend → 2030",
                                 line=dict(dash="dash")))
        fig.add_vline(x=2019, line_dash="dot", line_color="gray",
                      annotation_text="fit window ends")
        fig.update_layout(height=420, margin=dict(t=10), yaxis_title="Gap (yrs)")
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"Trend fitted on 2000–2019 (pre-COVID). Slope ≈ "
                   f"{b*10:.2f} yrs added to the gap per decade. "
                   "A simple linear trend; a richer model (e.g. ARIMA, or regressing "
                   "the gap on health spending) is a natural extension.")
    else:
        st.info("Not enough data to fit a trend for this entity.")

st.divider()
st.caption("Built for MSBA382 Healthcare Analytics. Data: WHO Global Health "
           "Observatory (HALE) and UN World Population Prospects (life expectancy), "
           "processed by Our World in Data. Metric: gap = LE − HALE.")
