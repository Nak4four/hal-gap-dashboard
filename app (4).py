"""
Lifespan vs. Healthspan — the Healthy Life Expectancy Gap
MSBA382 Healthcare Analytics · Individual Project · single-screen dashboard

Core metric: gap = life expectancy (LE) - healthy life expectancy (HALE)
             = the years a person lives in poor health.
All controls live in the sidebar; the main area is a clean dashboard grid.
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Lifespan vs. Healthspan", page_icon="🫀",
                   layout="wide", initial_sidebar_state="collapsed")
st.markdown("""<style>
.block-container{padding-top:1.1rem;padding-bottom:.4rem;}
[data-testid="stMetricValue"]{font-size:1.4rem;}
[data-testid="stMetricLabel"]{font-size:.75rem;}
h3{margin-bottom:.2rem;}
</style>""", unsafe_allow_html=True)

GREEN, RED, BLUE = "#2a9d8f", "#e76f51", "#577590"
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
        df["life_exp_male"] = np.nan; df["life_exp_female"] = np.nan
    df = df[(df.year >= start) & (df.year <= end)].copy()
    df["gap"] = (df.life_exp - df.hale).round(2)
    df["le_sex_gap"] = (df.life_exp_female - df.life_exp_male).round(2)
    df["is_aggregate"] = df.iso3.isna() | df.entity.str.contains(r"\(WHO\)", na=False)
    df["mena"] = df.iso3.isin(MENA_ISO3)
    df[["hale","life_exp"]] = df[["hale","life_exp"]].round(2)
    return df.sort_values(["entity","year"]).reset_index(drop=True)

def check_password():
    try:
        correct = st.secrets.get("password", "healthspan2026")
    except Exception:
        correct = "healthspan2026"
    if st.session_state.get("auth_ok"):
        return True
    st.markdown("<h1 style='text-align:center'>🫀 Lifespan vs. Healthspan</h1>",
                unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;color:gray'>The Healthy Life Expectancy "
                "Gap — years lived in poor health.<br>Enter the access password.</p>",
                unsafe_allow_html=True)
    c = st.columns([1, 1, 1])[1]
    with c:
        pw = st.text_input("Password", type="password",
                           label_visibility="collapsed", placeholder="Password")
        if pw:
            if pw == correct:
                st.session_state.auth_ok = True; st.rerun()
            else:
                st.error("Incorrect password.")
    return False

if not check_password():
    st.stop()

df = load_data()
df = df[df.iso3 != "ISR"].copy()                  # excluded from all charts
countries = df[~df.is_aggregate]
LATEST = int(df.year.max())

# ---- sidebar controls (keeps the dashboard area clean) ----
st.sidebar.title("Filters")
year = st.sidebar.slider("Year", int(df.year.min()), LATEST, LATEST)
scope = st.sidebar.radio("Country scope", ["All countries", "MENA only"])
fc_opts = sorted(df.entity.unique())
fc_ent = st.sidebar.selectbox("Forecast country",
                              fc_opts, index=fc_opts.index("Lebanon")
                              if "Lebanon" in fc_opts else 0)
st.sidebar.caption("Gap = life expectancy − healthy life expectancy = years in "
                   "poor health. Sources: WHO GHO (HALE) & UN WPP (LE) via OWID.")
scoped = countries[countries.mena] if scope == "MENA only" else countries

def show(fig, h=300):
    fig.update_layout(height=h, margin=dict(t=8, b=6, l=6, r=6),
                      font=dict(size=11), legend=dict(font=dict(size=10)))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ---- header + KPIs ----
st.markdown("### 🫀 Lifespan vs. Healthspan — the Healthy Life Expectancy Gap")
w  = df[(df.entity == "World") & (df.year == year)]
cy = scoped[scoped.year == year]
g0 = df[(df.entity == "World") & (df.year == 2000)].gap
g1 = df[(df.entity == "World") & (df.year == 2019)].gap
k = st.columns(5)
if not w.empty:
    k[0].metric("World life expectancy", f"{w.life_exp.iloc[0]:.1f}")
    k[1].metric("World healthy LE", f"{w.hale.iloc[0]:.1f}")
    k[2].metric("World gap (yrs)", f"{w.gap.iloc[0]:.1f}")
if not cy.empty:
    hi = cy.loc[cy.gap.idxmax()]
    k[3].metric(f"Widest gap ({'MENA' if scope!='All countries' else 'world'})",
                f"{hi.gap:.1f}", hi.entity)
k[4].metric("MENA average gap",
            f"{countries[countries.mena & (countries.year==year)].gap.mean():.1f}")
if len(g0) and len(g1):
    st.caption(f"**{year}.** The world's gap widened from {g0.iloc[0]:.1f} yrs (2000) "
               f"to {g1.iloc[0]:.1f} yrs (2019): lifespan rose faster than healthspan. "
               f"Longer-lived countries tend to carry the widest gaps.")

# ===================== ROW A: map · donut · trend =====================
a1, a2, a3 = st.columns([1.5, 1, 1])
with a1:
    st.markdown("**Gap by country**")
    mp = countries[countries.year == year].dropna(subset=["iso3"])
    fig = px.choropleth(mp, locations="iso3", color="gap", hover_name="entity",
                        color_continuous_scale="OrRd", range_color=(5, 15))
    fig.update_layout(coloraxis_colorbar_title="yrs",
                      geo=dict(showframe=False, projection_type="natural earth"))
    show(fig, 300)
with a2:
    st.markdown("**Anatomy of a lifespan — World**")
    aw = df[(df.entity == "World") & (df.year == year)]
    if not aw.empty:
        H, G, L = float(aw.hale.iloc[0]), float(aw.gap.iloc[0]), float(aw.life_exp.iloc[0])
        pct = H / L * 100 if L else 0
        donut = go.Figure(go.Pie(labels=["Healthy years", "Years in poor health"],
                                 values=[H, G], hole=.6, sort=False,
                                 marker_colors=[GREEN, RED], textinfo="value"))
        donut.update_layout(showlegend=True,
                            legend=dict(orientation="h", y=-.12),
                            annotations=[dict(text=f"{pct:.0f}%<br>healthy", x=.5, y=.5,
                                              font_size=16, showarrow=False)])
        show(donut, 300)
with a3:
    st.markdown("**World: lifespan vs. healthspan**")
    sub = df[df.entity == "World"]
    long = sub.melt(id_vars="year", value_vars=["life_exp", "hale"],
                    var_name="m", value_name="yrs")
    long.m = long.m.map({"life_exp": "Life expectancy", "hale": "Healthy LE"})
    ft = px.line(long, x="year", y="yrs", color="m",
                 color_discrete_map={"Life expectancy": BLUE, "Healthy LE": GREEN})
    ft.add_vline(x=2020, line_dash="dot", line_color="gray")
    ft.update_layout(legend=dict(orientation="h", y=-.2, title=""), yaxis_title="yrs")
    show(ft, 300)

# ===================== ROW B: ranking · scatter · gender =====================
b1, b2, b3 = st.columns(3)
cy2 = scoped[scoped.year == year].dropna(subset=["gap"])
with b1:
    st.markdown(f"**Widest gaps — {year}**")
    top = cy2.nlargest(12, "gap").sort_values("gap")
    fb = px.bar(top, x="gap", y="entity", orientation="h", color="gap",
                color_continuous_scale="OrRd")
    fb.update_layout(yaxis_title="", xaxis_title="gap (yrs)", coloraxis_showscale=False)
    show(fb, 320)
with b2:
    st.markdown("**Longer lives, bigger gaps?**")
    sc = countries[countries.year == year].dropna(subset=["gap", "life_exp"]).copy()
    sc["Region"] = np.where(sc.mena, "MENA", "Other")
    fsc = px.scatter(sc, x="life_exp", y="gap", color="Region", hover_name="entity",
                     color_discrete_map={"MENA": RED, "Other": BLUE}, opacity=.75)
    if len(sc) >= 5:
        b, a = np.polyfit(sc.life_exp, sc.gap, 1)
        xs = np.linspace(sc.life_exp.min(), sc.life_exp.max(), 50)
        fsc.add_trace(go.Scatter(x=xs, y=a + b * xs, mode="lines", name="trend",
                                 line=dict(color="gray", dash="dash")))
    fsc.update_layout(xaxis_title="life expectancy", yaxis_title="gap (yrs)",
                      legend=dict(orientation="h", y=-.2, title=""))
    show(fsc, 320)
with b3:
    st.markdown(f"**Extra years women live — {year}**")
    if countries.life_exp_female.notna().any():
        cy3 = scoped[scoped.year == year].dropna(subset=["le_sex_gap"]).nlargest(12, "le_sex_gap").sort_values("le_sex_gap")
        fg = px.bar(cy3, x="le_sex_gap", y="entity", orientation="h",
                    color="le_sex_gap", color_continuous_scale="Purpor")
        fg.update_layout(yaxis_title="", xaxis_title="F − M life exp (yrs)",
                         coloraxis_showscale=False)
        show(fg, 320)
    else:
        st.info("Sex split unavailable.")

# ===================== ROW C: MENA · forecast =====================
c1, c2 = st.columns([1.3, 1])
with c1:
    st.markdown(f"**MENA / Eastern Mediterranean — gap by country, {year}**")
    m = countries[countries.mena & (countries.year == year)].dropna(subset=["gap"]).sort_values("gap")
    fm = px.bar(m, x="gap", y="entity", orientation="h", color="gap",
                color_continuous_scale="OrRd")
    fm.update_layout(yaxis_title="", xaxis_title="gap (yrs)", coloraxis_showscale=False)
    show(fm, 380)
with c2:
    st.markdown(f"**{fc_ent}: gap projected to 2030**")
    s = df[(df.entity == fc_ent) & (df.year <= 2019)].dropna(subset=["gap"])
    if len(s) >= 5:
        b, a = np.polyfit(s.year, s.gap, 1)
        fut = np.arange(2000, 2031); pred = a + b * fut
        act = df[df.entity == fc_ent][["year", "gap"]]
        fc = go.Figure()
        fc.add_trace(go.Scatter(x=act.year, y=act.gap, mode="markers+lines", name="observed",
                                line=dict(color=BLUE)))
        fc.add_trace(go.Scatter(x=fut, y=pred, mode="lines", name="trend → 2030",
                                line=dict(color=RED, dash="dash")))
        fc.update_layout(yaxis_title="gap (yrs)",
                         legend=dict(orientation="h", y=-.2, title=""))
        show(fc, 380)
        st.caption(f"+{b*10:.2f} yrs per decade (fitted on 2000–2019).")
    else:
        st.info("Not enough data to fit a trend.")

st.caption("MSBA382 Healthcare Analytics · gap = LE − HALE · WHO GHO + UN WPP via "
           "Our World in Data · cross-source caveat applies; HALE not published by sex.")
