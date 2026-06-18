"""
Lifespan vs. Healthspan — the Healthy Life Expectancy Gap
MSBA382 Healthcare Analytics · Individual Project · Streamlit dashboard (single page)

Core metric:  gap = life expectancy (LE) - healthy life expectancy (HALE)
              = the years a person lives in poor health.
A lifespan splits into healthy years (HALE) + years in poor health (gap).

Data is built live from Our World in Data (WHO GHO + UN WPP) and cached.
If a local hale_le_gap.csv exists (from data_prep.py) it is used instead.
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Lifespan vs. Healthspan",
                   page_icon="🫀", layout="wide")

GREEN, RED = "#2a9d8f", "#e76f51"

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
    try:
        return pd.read_csv("hale_le_gap.csv")
    except Exception:
        pass
    hale = _fetch("healthy-life-expectancy-at-birth", "hale")
    le   = _fetch("life-expectancy", "life_exp")
    df = hale.merge(le, on=["entity", "iso3", "year"], how="inner")
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
# Password gate
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
        pw = st.text_input("Password", type="password",
                           label_visibility="collapsed", placeholder="Password")
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
df = df[df.iso3 != "ISR"].copy()      # excluded from all country-level charts
countries = df[~df.is_aggregate]
LATEST = int(df.year.max())

# --------------------------------------------------------------------------
# Sidebar
# --------------------------------------------------------------------------
st.sidebar.title("Filters")
year = st.sidebar.slider("Year (map, rankings, gender, MENA)",
                         int(df.year.min()), LATEST, LATEST)
scope = st.sidebar.radio("Country scope", ["All countries", "MENA only"])
st.sidebar.caption("Lifespan = life expectancy (LE). Healthspan = healthy life "
                   "expectancy (HALE). Gap = LE − HALE = years in poor health.")
st.sidebar.caption("Sources: WHO GHO (HALE) & UN WPP (LE), via Our World in Data.")
scoped = countries[countries.mena] if scope == "MENA only" else countries

# --------------------------------------------------------------------------
# Header + KPIs
# --------------------------------------------------------------------------
st.title("Lifespan vs. Healthspan — the Healthy Life Expectancy Gap")
st.markdown("How long people live (life expectancy) versus how long they live in "
            "good health (healthy life expectancy). The space between them — the "
            "**gap** — is the years lived in poor health.")

wrow = df[(df.entity == "World") & (df.year == year)]
cy = scoped[scoped.year == year]
k1, k2, k3, k4 = st.columns(4)
if not wrow.empty:
    k1.metric("World life expectancy", f"{wrow.life_exp.iloc[0]:.1f} yrs")
    k2.metric("World healthy life expectancy", f"{wrow.hale.iloc[0]:.1f} yrs")
    k3.metric("World gap", f"{wrow.gap.iloc[0]:.1f} yrs", help="Years in poor health")
if not cy.empty:
    hi = cy.loc[cy.gap.idxmax()]
    k4.metric(f"Widest gap — {scope.lower()}", f"{hi.gap:.1f} yrs", hi.entity)
st.caption(f"Figures for {year}. Use the sidebar to change the year and scope.")

# ==========================================================================
# 1) MAP
# ==========================================================================
st.divider()
st.subheader(f"1 · The gap across the world — {year}")
mp = countries[countries.year == year].dropna(subset=["iso3"])
fig = px.choropleth(mp, locations="iso3", color="gap", hover_name="entity",
                    color_continuous_scale="OrRd", range_color=(5, 15),
                    labels={"gap": "Gap (yrs)"})
fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=430,
                  coloraxis_colorbar_title="Gap<br>(yrs)")
st.plotly_chart(fig, use_container_width=True)
st.caption("Darker = more years lived in poor health. A small gap in much of "
           "Sub-Saharan Africa reflects shorter lifespans, not better health.")

# ==========================================================================
# 2) ANATOMY OF A LIFESPAN  (donut + gauge + stacked split)
# ==========================================================================
st.divider()
st.subheader("2 · Anatomy of a lifespan")
a_opts = sorted(df.entity.unique())
a_idx = a_opts.index("World") if "World" in a_opts else 0
a_ent = st.selectbox("Break a lifespan into healthy vs. unhealthy years for:",
                     a_opts, index=a_idx)
arow = df[(df.entity == a_ent) & (df.year == year)]
cA, cB, cC = st.columns([1, 1, 1.3])
if not arow.empty:
    H = float(arow.hale.iloc[0]); G = float(arow.gap.iloc[0]); L = float(arow.life_exp.iloc[0])
    pct = H / L * 100 if L else 0
    # donut
    donut = go.Figure(go.Pie(
        labels=["Healthy years (HALE)", "Years in poor health (gap)"],
        values=[H, G], hole=0.58, sort=False,
        marker_colors=[GREEN, RED], textinfo="value"))
    donut.update_layout(height=330, margin=dict(t=30, b=0, l=0, r=0),
                        showlegend=True, legend=dict(orientation="h", y=-0.1),
                        title=dict(text=f"{a_ent}, {year}", x=0.5),
                        annotations=[dict(text=f"{pct:.0f}%<br>healthy",
                                          x=0.5, y=0.5, font_size=18, showarrow=False)])
    cA.plotly_chart(donut, use_container_width=True)
    # gauge
    gauge = go.Figure(go.Indicator(
        mode="gauge+number", value=round(pct, 1), number={"suffix": "%"},
        title={"text": "Share of life in good health"},
        gauge={"axis": {"range": [0, 100]}, "bar": {"color": GREEN},
               "steps": [{"range": [0, 80], "color": "#f4f1de"},
                         {"range": [80, 100], "color": "#e9f5f3"}]}))
    gauge.update_layout(height=330, margin=dict(t=40, b=0, l=20, r=20))
    cB.plotly_chart(gauge, use_container_width=True)
    cC.markdown(f"**{a_ent}, {year}** — of a {L:.1f}-year lifespan, about "
                f"**{H:.1f} years** are lived in good health and **{G:.1f} years** "
                f"in poor health ({pct:.0f}% healthy). The donut and gauge show the "
                f"same split two ways; lower the year in the sidebar to see how the "
                f"healthy share has shifted over time.")
# stacked split across countries
st.markdown("**Healthy years vs. years in poor health — stacked by country**")
sb = scoped[scoped.year == year].dropna(subset=["gap"]).nlargest(12, "life_exp")
sb_long = sb.melt(id_vars="entity", value_vars=["hale", "gap"],
                  var_name="part", value_name="years")
sb_long.part = sb_long.part.map({"hale": "Healthy years", "gap": "Years in poor health"})
fs = px.bar(sb_long, x="years", y="entity", color="part", orientation="h",
            color_discrete_map={"Healthy years": GREEN, "Years in poor health": RED})
fs.update_layout(height=380, margin=dict(t=10), barmode="stack", yaxis_title="",
                 xaxis_title="Years", legend_title_text="",
                 yaxis={"categoryorder": "total ascending"})
st.plotly_chart(fs, use_container_width=True)
st.caption("Bar length = total lifespan; the red segment is the gap. Longer-lived "
           "countries tend to carry a larger red segment.")

# ==========================================================================
# 3) TRENDS
# ==========================================================================
st.divider()
st.subheader("3 · Lifespan and healthspan over time")
opts = sorted(df.entity.unique())
default = [e for e in ["World", "Eastern Mediterranean (WHO)", "Lebanon", "Japan"]
           if e in opts]
picks = st.multiselect("Entities to compare", opts, default=default)
cL, cR = st.columns(2)
if picks:
    sub = df[df.entity.isin(picks)]
    long = sub.melt(id_vars=["entity", "year"], value_vars=["life_exp", "hale"],
                    var_name="measure", value_name="years")
    long.measure = long.measure.map({"life_exp": "Life expectancy",
                                     "hale": "Healthy life expectancy"})
    f1 = px.line(long, x="year", y="years", color="entity", line_dash="measure")
    f1.add_vline(x=2020, line_dash="dot", line_color="gray", annotation_text="COVID-19")
    f1.update_layout(height=340, margin=dict(t=10), legend_title_text="",
                     yaxis_title="Years")
    cL.markdown("**Lifespan (solid) vs. healthspan (dashed)**")
    cL.plotly_chart(f1, use_container_width=True)
    f2 = px.line(sub, x="year", y="gap", color="entity", markers=True)
    f2.add_vline(x=2020, line_dash="dot", line_color="gray")
    f2.update_layout(height=340, margin=dict(t=10), yaxis_title="Gap (yrs)",
                     legend_title_text="")
    cR.markdown("**The gap itself, over time**")
    cR.plotly_chart(f2, use_container_width=True)

# ==========================================================================
# 4) RANKING + DISTRIBUTION + SCATTER
# ==========================================================================
st.divider()
st.subheader(f"4 · Where the gap is widest, and what drives it — {year}")
cy2 = scoped[scoped.year == year].dropna(subset=["gap"])
cL, cR = st.columns(2)
top = cy2.nlargest(15, "gap").sort_values("gap")
fb = px.bar(top, x="gap", y="entity", orientation="h", color="gap",
            color_continuous_scale="OrRd")
fb.update_layout(height=420, margin=dict(t=10), yaxis_title="",
                 xaxis_title="Gap (yrs)", coloraxis_showscale=False)
cL.markdown("**Widest 15**")
cL.plotly_chart(fb, use_container_width=True)
fh = px.histogram(cy2, x="gap", nbins=25)
fh.update_layout(height=420, margin=dict(t=10), xaxis_title="Gap (yrs)",
                 yaxis_title="# countries")
cR.markdown("**Distribution across countries**")
cR.plotly_chart(fh, use_container_width=True)
cR.caption(f"Median {cy2.gap.median():.1f} yrs · "
           f"range {cy2.gap.min():.1f}–{cy2.gap.max():.1f} yrs.")
# scatter: LE vs gap, with a fitted trend line
sc = countries[countries.year == year].dropna(subset=["gap", "life_exp"]).copy()
sc["Region"] = np.where(sc.mena, "MENA", "Other")
fsc = px.scatter(sc, x="life_exp", y="gap", color="Region", hover_name="entity",
                 color_discrete_map={"MENA": RED, "Other": "#577590"}, opacity=0.75)
if len(sc) >= 5:
    b, a = np.polyfit(sc.life_exp, sc.gap, 1)
    xs = np.linspace(sc.life_exp.min(), sc.life_exp.max(), 50)
    fsc.add_trace(go.Scatter(x=xs, y=a + b * xs, mode="lines", name="Trend",
                             line=dict(color="gray", dash="dash")))
fsc.update_layout(height=420, margin=dict(t=10), legend_title_text="",
                  xaxis_title="Life expectancy (yrs)", yaxis_title="Gap (yrs)")
st.markdown("**Do longer-lived countries have bigger gaps?**")
st.plotly_chart(fsc, use_container_width=True)
st.caption("Each point is a country. The upward trend line shows the gap tends to "
           "widen as lifespan rises — more late-life years in which chronic disease "
           "accumulates. MENA countries are highlighted.")

# ==========================================================================
# 5) GENDER + MENA
# ==========================================================================
st.divider()
st.subheader(f"5 · Gender and the MENA region — {year}")
cL, cR = st.columns(2)
if countries.life_exp_female.notna().any():
    cy3 = scoped[scoped.year == year].dropna(subset=["le_sex_gap"])
    topg = cy3.nlargest(15, "le_sex_gap").sort_values("le_sex_gap")
    fg = px.bar(topg, x="le_sex_gap", y="entity", orientation="h",
                color="le_sex_gap", color_continuous_scale="Purpor")
    fg.update_layout(height=420, margin=dict(t=10), yaxis_title="",
                     xaxis_title="Extra years women live", coloraxis_showscale=False)
    cL.markdown("**Female − male life expectancy**")
    cL.plotly_chart(fg, use_container_width=True)
    cL.caption("Women live longer almost everywhere; the literature shows those "
               "extra years are often less healthy. HALE is not published by sex.")
else:
    cL.info("Sex-disaggregated life expectancy unavailable at load time.")
m = countries[countries.mena & (countries.year == year)].dropna(subset=["gap"]).sort_values("gap")
fm = px.bar(m, x="gap", y="entity", orientation="h", color="gap",
            color_continuous_scale="OrRd")
fm.update_layout(height=420, margin=dict(t=10), yaxis_title="",
                 xaxis_title="Gap (yrs)", coloraxis_showscale=False)
cR.markdown("**MENA / Eastern Mediterranean — gap by country**")
cR.plotly_chart(fm, use_container_width=True)

# ==========================================================================
# 6) MENA vs WORLD trend + FORECAST
# ==========================================================================
st.divider()
st.subheader("6 · Regional trajectory and a simple forecast")
cL, cR = st.columns(2)
mena_ts = countries[countries.mena].groupby("year").gap.mean().reset_index()
world_ts = df[df.entity == "World"][["year", "gap"]].rename(columns={"gap": "World"})
comp = mena_ts.merge(world_ts, on="year").rename(columns={"gap": "MENA average"})
fc1 = px.line(comp.melt("year", var_name="series", value_name="gap"),
              x="year", y="gap", color="series", markers=True)
fc1.add_vline(x=2020, line_dash="dot", line_color="gray")
fc1.update_layout(height=360, margin=dict(t=10), yaxis_title="Gap (yrs)",
                  legend_title_text="")
cL.markdown("**MENA average vs. World**")
cL.plotly_chart(fc1, use_container_width=True)

ent_opts = sorted(countries.entity.unique())
idx = ent_opts.index("Lebanon") if "Lebanon" in ent_opts else 0
ent = cR.selectbox("Forecast country", ent_opts, index=idx)
s = df[(df.entity == ent) & (df.year <= 2019)].dropna(subset=["gap"])
if len(s) >= 5:
    b, a = np.polyfit(s.year, s.gap, 1)
    fut = np.arange(2000, 2031)
    pred = a + b * fut
    actual = df[df.entity == ent][["year", "gap"]]
    fc2 = go.Figure()
    fc2.add_trace(go.Scatter(x=actual.year, y=actual.gap, mode="markers+lines",
                             name="Observed"))
    fc2.add_trace(go.Scatter(x=fut, y=pred, mode="lines", name="Trend → 2030",
                             line=dict(dash="dash")))
    fc2.update_layout(height=360, margin=dict(t=10), yaxis_title="Gap (yrs)",
                      legend_title_text="")
    cR.markdown(f"**{ent}: gap projected to 2030** (+{b*10:.2f} yrs/decade)")
    cR.plotly_chart(fc2, use_container_width=True)
else:
    cR.info("Not enough data to fit a trend for this entity.")

# ==========================================================================
# Key takeaways
# ==========================================================================
st.divider()
st.subheader("Key takeaways")
try:
    w0 = df[(df.entity == "World") & (df.year == 2000)].gap.iloc[0]
    w1 = df[(df.entity == "World") & (df.year == 2019)].gap.iloc[0]
    mena_now = countries[countries.mena & (countries.year == year)].gap.mean()
    widest = countries[countries.year == year].dropna(subset=["gap"]).nlargest(1, "gap").iloc[0]
    st.markdown(
        f"- The world's gap widened from **{w0:.1f}** years (2000) to **{w1:.1f}** "
        f"years (2019) — lifespan rose faster than healthspan.\n"
        f"- In {year}, the widest national gap is **{widest.entity} ({widest.gap:.1f} yrs)**; "
        f"the MENA average is **{mena_now:.1f} yrs**.\n"
        f"- The gap tends to widen as lifespan rises — longer lives bring more late-life "
        f"years exposed to chronic disease.\n"
        f"- The 2020–21 dip reflects COVID-19 shortening lifespan — it narrows the gap "
        f"without improving health, so the two curves must be read together.\n"
        f"- Women live longer almost everywhere, but those extra years are often less healthy."
    )
except Exception:
    pass

st.divider()
st.caption("MSBA382 Healthcare Analytics. Data: WHO Global Health Observatory (HALE) "
           "and UN World Population Prospects (life expectancy), via Our World in Data. "
           "Metric: gap = LE − HALE. Cross-source caveat applies; HALE is not published by sex.")
