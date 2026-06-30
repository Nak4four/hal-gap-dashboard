"""
Lifespan vs. Healthspan — the Healthy Life Expectancy Gap
MSBA382 Healthcare Analytics · Individual Project

COORDINATED MULTIPLE-VIEWS dashboard (linked views / cross-filtering):
one shared selection — the "focus country" — is set by clicking the world
map or the sidebar picker, and EVERY other panel responds to it:
  • the KPI row, the lifespan donut, the lifespan-vs-healthspan trend and the
    2030 forecast all switch to the focus country;
  • the focus country is highlighted in the scatter, the widest-gaps ranking
    and the MENA bar.
The Year slider drives the cross-sectional snapshot (map, scatter, rankings).

Core metric: gap = life expectancy (LE) − healthy life expectancy (HALE)
             = the years a person lives in poor health.
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Lifespan vs. Healthspan", page_icon="🫀",
                   layout="wide", initial_sidebar_state="expanded")
st.markdown("""<style>
.block-container{padding-top:1.1rem;padding-bottom:.4rem;}
[data-testid="stMetricValue"]{font-size:1.35rem;}
[data-testid="stMetricLabel"]{font-size:.72rem;}
h3{margin-bottom:.2rem;}
</style>""", unsafe_allow_html=True)

GREEN, RED, BLUE, PURPLE = "#2a9d8f", "#e76f51", "#577590", "#9b5de5"
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
        df = pd.read_csv("hale_le_gap.csv")
    except Exception:
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
        df[["hale","life_exp"]] = df[["hale","life_exp"]].round(2)
    df["is_aggregate"] = (df.iso3.isna()
                          | df.iso3.astype(str).str.startswith("OWID_")
                          | df.entity.str.contains(r"\(WHO\)", na=False))
    df["mena"] = df.iso3.isin(MENA_ISO3)
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
df = df[df.iso3 != "ISR"].copy()                 # excluded from all charts
countries = df[~df.is_aggregate].copy()          # real countries only
LATEST = int(df.year.max())

ent_of = dict(zip(countries.iso3, countries.entity))
iso_of = dict(zip(countries.entity, countries.iso3))
DEFAULT = "LBN" if "LBN" in ent_of else countries.iso3.iloc[0]
if "focus" not in st.session_state:
    st.session_state.focus = DEFAULT

# ---- coordination: apply a NEW click on the map (change-detection) ----
sel = st.session_state.get("map")
if isinstance(sel, dict):
    pts = (sel.get("selection") or {}).get("points") or []
    if pts:
        iso = pts[0].get("location")
        if iso and iso in ent_of and iso != st.session_state.get("last_map_iso"):
            st.session_state.focus = iso
            st.session_state.last_map_iso = iso

# ---- sidebar controls ----
st.sidebar.title("Filters")
year = st.sidebar.slider("Year", int(df.year.min()), LATEST, LATEST)
scope = st.sidebar.radio("Country scope", ["All countries", "MENA only"])
opts = sorted(countries.entity.unique())
cur_ent = ent_of.get(st.session_state.focus, opts[0])
pick = st.sidebar.selectbox("Focus country", opts, index=opts.index(cur_ent))
if pick != cur_ent:                              # picker changes the focus
    st.session_state.focus = iso_of[pick]
focus = st.session_state.focus
fname = ent_of.get(focus, "—")
st.sidebar.caption("Gap = life expectancy − healthy life expectancy = years in "
                   "poor health.\n\n**Click a country on the map** or pick one above — "
                   "every panel on the right follows it. Sources: WHO GHO (HALE) & "
                   "UN WPP (LE) via Our World in Data.")

scoped = countries[countries.mena] if scope == "MENA only" else countries

def show(fig, h=300):
    fig.update_layout(height=h, margin=dict(t=8, b=6, l=6, r=6),
                      font=dict(size=11), legend=dict(font=dict(size=10)))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ---- header ----
st.markdown("### 🫀 Lifespan vs. Healthspan — the Healthy Life Expectancy Gap")
st.caption("**Coordinated view.** Click a country on the map (or use the sidebar picker) "
           "and the KPIs and the right-hand panels update to it, while it lights up across "
           "the other charts. Move the **Year** slider to change the snapshot.")

# ---- KPI row — coordinated to the focus country ----
fy = countries[(countries.iso3 == focus) & (countries.year == year)]
wy = df[(df.entity == "World") & (df.year == year)]
cy = scoped[scoped.year == year].dropna(subset=["gap"])
k = st.columns(5)
if not fy.empty:
    gapv = float(fy.gap.iloc[0])
    rank = int((cy.gap > gapv).sum()) + 1
    k[0].metric(f"{fname} · life expectancy", f"{fy.life_exp.iloc[0]:.1f}")
    k[1].metric(f"{fname} · healthy LE", f"{fy.hale.iloc[0]:.1f}")
    dvs = (gapv - float(wy.gap.iloc[0])) if not wy.empty else None
    k[2].metric(f"{fname} · gap (yrs)", f"{gapv:.1f}",
                f"{dvs:+.1f} vs world" if dvs is not None else None,
                delta_color="inverse")
    k[3].metric("Gap rank (widest)", f"#{rank} of {cy.iso3.nunique()}")
else:
    k[0].metric(f"{fname}", "no data")
k[4].metric("World gap (yrs)", f"{wy.gap.iloc[0]:.1f}" if not wy.empty else "—")

st.divider()

# ================= OVERVIEW (left, selectors) · DETAIL (right, follows focus) =================
L, Rr = st.columns([1.45, 1], gap="medium")

with L:
    st.markdown("**Gap by country** — click a country to select it")
    mp = countries[countries.year == year].dropna(subset=["iso3"])
    figm = px.choropleth(mp, locations="iso3", color="gap", hover_name="entity",
                         custom_data=["entity"], color_continuous_scale="OrRd",
                         range_color=(5, 15))
    figm.update_layout(height=330, margin=dict(t=6, b=6, l=6, r=6),
                       coloraxis_colorbar_title="yrs",
                       geo=dict(showframe=False, projection_type="natural earth"))
    try:
        st.plotly_chart(figm, use_container_width=True, key="map",
                        on_select="rerun", config={"displayModeBar": False})
    except TypeError:                            # older Streamlit: no click events
        st.plotly_chart(figm, use_container_width=True,
                        config={"displayModeBar": False})

    st.markdown("**Longer lives, bigger gaps?** — selected country starred")
    sc = scoped[scoped.year == year].dropna(subset=["gap", "life_exp"]).copy()
    sc["Region"] = np.where(sc.mena, "MENA", "Other")
    fsc = px.scatter(sc, x="life_exp", y="gap", color="Region", hover_name="entity",
                     color_discrete_map={"MENA": RED, "Other": BLUE}, opacity=.6)
    if len(sc) >= 5:
        b, a = np.polyfit(sc.life_exp, sc.gap, 1)
        xs = np.linspace(sc.life_exp.min(), sc.life_exp.max(), 50)
        fsc.add_trace(go.Scatter(x=xs, y=a + b * xs, mode="lines", name="trend",
                                 line=dict(color="gray", dash="dash")))
    ff = sc[sc.iso3 == focus]
    if not ff.empty:
        fsc.add_trace(go.Scatter(x=[ff.life_exp.iloc[0]], y=[ff.gap.iloc[0]],
                                 mode="markers+text", text=[fname],
                                 textposition="top center", name=fname,
                                 marker=dict(color=GREEN, size=16, symbol="star",
                                             line=dict(color="white", width=1))))
    fsc.update_layout(xaxis_title="life expectancy", yaxis_title="gap (yrs)",
                      legend=dict(orientation="h", y=-.2, title=""))
    show(fsc, 300)

    st.markdown(f"**Widest gaps — {year}** — selected country in teal")
    top = scoped[scoped.year == year].dropna(subset=["gap"]).nlargest(12, "gap").sort_values("gap")
    colors = [GREEN if i == focus else BLUE for i in top.iso3]
    fb = go.Figure(go.Bar(x=top.gap, y=top.entity, orientation="h", marker_color=colors,
                          text=[f"{g:.1f}" for g in top.gap], textposition="outside"))
    fb.update_layout(xaxis_title="gap (yrs)", yaxis_title="")
    show(fb, 320)

with Rr:
    st.markdown(f"**{fname} — anatomy of a lifespan, {year}**")
    if not fy.empty:
        H, G, Lv = float(fy.hale.iloc[0]), float(fy.gap.iloc[0]), float(fy.life_exp.iloc[0])
        pct = H / Lv * 100 if Lv else 0
        dn = go.Figure(go.Pie(labels=["Healthy years", "Years in poor health"],
                              values=[H, G], hole=.62, sort=False,
                              marker_colors=[GREEN, RED], textinfo="value"))
        dn.update_layout(showlegend=True, legend=dict(orientation="h", y=-.12),
                         annotations=[dict(text=f"{pct:.0f}%<br>healthy", x=.5, y=.5,
                                           font_size=15, showarrow=False)])
        show(dn, 250)
    else:
        st.info("No data for this country and year.")

    st.markdown(f"**{fname} — lifespan vs. healthspan**")
    sub = countries[countries.iso3 == focus]
    if not sub.empty:
        long = sub.melt(id_vars="year", value_vars=["life_exp", "hale"],
                        var_name="m", value_name="yrs")
        long.m = long.m.map({"life_exp": "Life expectancy", "hale": "Healthy LE"})
        ft = px.line(long, x="year", y="yrs", color="m",
                     color_discrete_map={"Life expectancy": BLUE, "Healthy LE": GREEN})
        ft.add_vline(x=year, line_dash="dot", line_color="gray")
        ft.update_layout(legend=dict(orientation="h", y=-.25, title=""), yaxis_title="yrs")
        show(ft, 250)

    st.markdown(f"**{fname} — gap projected to 2030**")
    sfc = countries[(countries.iso3 == focus) & (countries.year <= 2019)].dropna(subset=["gap"])
    if len(sfc) >= 5:
        b, a = np.polyfit(sfc.year, sfc.gap, 1)
        fut = np.arange(2000, 2031); pred = a + b * fut
        act = countries[countries.iso3 == focus][["year", "gap"]]
        fc = go.Figure()
        fc.add_trace(go.Scatter(x=act.year, y=act.gap, mode="markers+lines",
                                name="observed", line=dict(color=BLUE)))
        fc.add_trace(go.Scatter(x=fut, y=pred, mode="lines", name="trend → 2030",
                                line=dict(color=RED, dash="dash")))
        fc.update_layout(yaxis_title="gap (yrs)",
                         legend=dict(orientation="h", y=-.25, title=""))
        show(fc, 250)
        st.caption(f"+{b*10:.2f} yrs per decade (fitted on 2000–2019).")
    else:
        st.info("Not enough data to fit a trend for this country.")

st.divider()

# ================= secondary coordinated row: MENA · gender =================
s1, s2 = st.columns(2, gap="medium")
with s1:
    st.markdown(f"**MENA / Eastern Mediterranean — gap by country, {year}**")
    m = countries[countries.mena & (countries.year == year)].dropna(subset=["gap"]).sort_values("gap")
    mcolors = [GREEN if i == focus else RED for i in m.iso3]
    fmn = go.Figure(go.Bar(x=m.gap, y=m.entity, orientation="h", marker_color=mcolors,
                           text=[f"{g:.1f}" for g in m.gap], textposition="outside"))
    fmn.update_layout(xaxis_title="gap (yrs)", yaxis_title="")
    show(fmn, 360)
with s2:
    st.markdown(f"**Extra years women live — {year}**")
    if countries.life_exp_female.notna().any():
        g = scoped[scoped.year == year].dropna(subset=["le_sex_gap"]).nlargest(12, "le_sex_gap").sort_values("le_sex_gap")
        gcolors = [GREEN if i == focus else PURPLE for i in g.iso3]
        fg = go.Figure(go.Bar(x=g.le_sex_gap, y=g.entity, orientation="h", marker_color=gcolors,
                              text=[f"{v:.1f}" for v in g.le_sex_gap], textposition="outside"))
        fg.update_layout(xaxis_title="F − M life exp (yrs)", yaxis_title="")
        show(fg, 360)
    else:
        st.info("Sex split unavailable.")

st.caption("Coordinated multiple-views dashboard · gap = LE − HALE · WHO GHO (HALE) + "
           "UN WPP (life expectancy) via Our World in Data · cross-source caveat applies; "
           "HALE not published by sex; Israel excluded.")
