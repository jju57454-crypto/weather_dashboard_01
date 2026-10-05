# app.py
# 날씨 기반 소비 분석 대시보드 (날씨 API × 실습용 카드 소비 데이터)
# 실행: streamlit run app.py
# 준비: python collect_weather.py → python make_card_data.py

import json
from pathlib import Path
from urllib.request import urlopen

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from regions import REGIONS

DATA = Path(__file__).parent / "data"
RAIN_MM = 3  # 일강수량이 이 값 이상이면 '비 오는 날'로 본다

# ---------------------------------------------------------------------------
# 테마 (화이트 · 네이비 + 레드 포인트)
# ---------------------------------------------------------------------------
NAVY = "#1f3a5f"; NAVY_DK = "#16293f"
RED = "#d64045"; RED_DK = "#b22f34"
INK = "#1c2530"; SUB = "#5e6b7a"; SOFT = "#9aa6b2"
GRID = "#eef1f5"; LINE = "#e3e8ee"
PAPER = "#ffffff"; SOFTBG = "#f7f9fb"
UP = "#1f9d6b"; DN = "#d64045"
FILL = "rgba(31,58,95,0.10)"
PALETTE = ["#1f3a5f", "#d64045", "#e0a458", "#4f8a8b", "#7f9c6b", "#9b7baf", "#c97b84"]
IND_COLOR = {"배달": "#d64045", "편의점": "#4f8a8b", "엔터": "#9b7baf", "교통": "#8a96a3",
             "음식점": "#e0a458", "카페": "#7f9c6b", "패션": "#1f3a5f"}

st.set_page_config(page_title="날씨 기반 소비 분석 대시보드", page_icon="💳",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown(f"""
<style>
  .stApp {{ background:{PAPER}; }}
  .block-container {{ padding-top:1.6rem; padding-bottom:4rem; max-width:1320px; }}
  #MainMenu, footer, header {{ visibility:hidden; }}

  [data-testid="stSidebar"] {{ background:{NAVY_DK}; }}
  [data-testid="stSidebar"] * {{ color:#d6dee8 !important; }}
  [data-testid="stSidebar"] .stMultiSelect div, [data-testid="stSidebar"] .stSelectbox div {{ color:{INK} !important; }}
  [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{ color:#fff !important; }}

  .hl {{ font-size:2rem; font-weight:800; color:{INK}; display:flex; align-items:center; gap:10px; }}
  .hl .ic {{ color:{RED}; }}
  .lead {{ color:{SUB}; font-size:0.92rem; margin:3px 0 4px; }}
  .period {{ color:{SUB}; font-size:0.8rem; font-weight:600; margin-bottom:18px; }}

  .kpi {{ background:{PAPER}; border:1px solid {LINE}; border-radius:16px; padding:18px 20px 10px;
    box-shadow:0 3px 10px rgba(28,37,48,0.05); }}
  .kpi .lab {{ color:{SUB}; font-size:0.82rem; font-weight:600; }}
  .kpi .val {{ color:{INK}; font-size:1.95rem; font-weight:800; line-height:1.15; margin-top:3px; }}
  .badge {{ display:inline-block; font-size:0.74rem; font-weight:700; padding:2px 9px; border-radius:999px; margin-top:5px; }}
  .bup {{ background:#e3f4ec; color:{UP}; }} .bdn {{ background:#f9e5e6; color:{DN}; }}

  .qh {{ font-size:1.4rem; font-weight:800; color:{INK}; margin-top:10px; }}
  .qd {{ color:{SUB}; font-size:0.86rem; margin:3px 0 12px; }}
  .ct {{ color:{INK}; font-weight:700; font-size:1rem; margin-bottom:4px; }}

  .action {{ background:linear-gradient(135deg,{RED} 0%,{RED_DK} 100%); border-radius:16px;
    padding:24px 26px; color:#fff7f3; box-shadow:0 12px 30px -14px rgba(214,64,69,0.55); }}
  .action2 {{ background:linear-gradient(135deg,{NAVY} 0%,{NAVY_DK} 100%); }}
  .action .tag {{ font-size:0.72rem; font-weight:800; letter-spacing:0.08em; opacity:0.85; text-transform:uppercase; }}
  .action h3 {{ font-size:1.15rem; font-weight:800; margin:4px 0 14px; }}
  .act-item {{ background:rgba(255,255,255,0.14); border-radius:11px; padding:12px 15px; margin-bottom:10px; }}
  .act-item .h {{ font-weight:800; font-size:0.92rem; }}
  .act-item .d {{ font-size:0.82rem; opacity:0.92; margin-top:2px; }}
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_data():
    """카드 소비와 날씨를 (date, region) 으로 조인한다."""
    card = pd.read_csv(DATA / "card_daily.csv", parse_dates=["date"])
    weather = pd.read_csv(DATA / "weather_daily.csv", parse_dates=["date"])
    df = card.merge(weather, on=["date", "region"], how="inner")
    # 소비지수: 같은 지역 · 업종의 평소(기간 평균) 소비를 100 으로 둔 값. 지역 규모 차이를 없앤다.
    df["idx"] = df["amount"] / df.groupby(["region", "industry"])["amount"].transform("mean") * 100
    df["rainy"] = df["rainfall"] >= RAIN_MM
    df["zone"] = df["region"].map({r: v["zone"] for r, v in REGIONS.items()})
    return df


try:
    df_all = load_data()
except FileNotFoundError:
    st.error("data 폴더에 데이터가 없습니다. 먼저 아래 두 명령을 실행하세요.\n\n"
             "`python collect_weather.py` → `python make_card_data.py`")
    st.stop()

ALL_REGIONS = [r for r in REGIONS if r in set(df_all["region"])]
ALL_INDS = [i for i in IND_COLOR if i in set(df_all["industry"])]

# ---------------------------------------------------------------------------
# 사이드바
# ---------------------------------------------------------------------------
st.sidebar.markdown("## 💳 CardLab")
st.sidebar.divider()
st.sidebar.markdown("#### 🔎 Filters")
sel_regions = st.sidebar.multiselect("지역", ALL_REGIONS, default=ALL_REGIONS) or ALL_REGIONS
sel_inds = st.sidebar.multiselect("업종", ALL_INDS, default=ALL_INDS) or ALL_INDS
focus = st.sidebar.selectbox("심층 분석 업종", sel_inds, index=0)
df = df_all[df_all["region"].isin(sel_regions) & df_all["industry"].isin(sel_inds)].copy()
st.sidebar.divider()
weather_src = {"kma": "기상청 ASOS 일자료", "open-meteo": "Open-Meteo 재분석 자료"}.get(df_all["source"].iloc[0], "날씨 API")
st.sidebar.caption(f"날씨: {weather_src}\n\n카드 소비: 실습용 가상 데이터")

if df.empty:
    st.warning("선택 조건에 데이터가 없습니다."); st.stop()


# ---------------------------------------------------------------------------
# 분석 함수
# ---------------------------------------------------------------------------
def daily_pivot(frame):
    """전국 일별 요약: 업종별 소비 합계 + 지역 평균 날씨."""
    p = frame.pivot_table(index="date", columns="industry", values="amount", aggfunc="sum")
    w = frame.drop_duplicates(["date", "region"]).groupby("date")[["temp", "rainfall", "humidity"]].mean()
    return p.join(w)


def rain_change(frame):
    """비 오는 날 vs 그 외 날의 업종별 소비지수 증감률(%). 지역 · 날짜 단위로 비교한다."""
    g = frame.groupby(["industry", "rainy"])["idx"].mean().unstack()
    if True not in g.columns or False not in g.columns:
        return pd.Series(0.0, index=sel_inds)
    return ((g[True] / g[False] - 1) * 100).reindex(sel_inds).sort_values(ascending=False)


def corr_matrix(frame):
    rows = {}
    for ind, g in frame.groupby("industry"):
        rows[ind] = [round(g["rainfall"].corr(g["idx"]), 2), round(g["temp"].corr(g["idx"]), 2),
                     round(g["humidity"].corr(g["idx"]), 2)]
    return pd.DataFrame(rows, index=["강수", "기온", "습도"]).T.reindex(sel_inds)


def theme(fig, h=340, legend=True):
    fig.update_layout(height=h, margin=dict(l=6, r=12, t=8, b=6),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="sans-serif", size=12, color="#37424f"),
        hoverlabel=dict(bgcolor="white", bordercolor=LINE, font_size=12),
        showlegend=legend, legend=dict(orientation="h", y=-0.2, x=0, font=dict(size=11)),
        colorway=PALETTE)
    fig.update_xaxes(showgrid=False, showline=True, linecolor=LINE, ticks="outside", tickcolor=LINE)
    fig.update_yaxes(showgrid=True, gridcolor=GRID, zeroline=False, showline=False)
    return fig


def spark(series, color, kind="area"):
    f = go.Figure()
    x = list(range(len(series)))
    if kind == "bar":
        f.add_trace(go.Bar(x=x, y=series, marker_color=color, marker_line_width=0))
    else:
        f.add_trace(go.Scatter(x=x, y=series, mode="lines", line=dict(color=color, width=2),
                               fill="tozeroy", fillcolor=FILL))
        f.update_yaxes(range=[min(series) * 0.9, max(series) * 1.02])
    f.update_layout(height=66, margin=dict(l=0, r=0, t=4, b=0), plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)", showlegend=False,
                    xaxis=dict(visible=False), yaxis=dict(visible=False))
    return f


def recent_delta(daily):
    """최근 4주 평균이 직전 4주 평균보다 얼마나 변했는지(%)."""
    if len(daily) < 56:
        return 0.0
    return (daily.iloc[-28:].mean() / daily.iloc[-56:-28].mean() - 1) * 100


dp = daily_pivot(df)
rain_impact = rain_change(df); cmat = corr_matrix(df)
top_rain, low_rain = rain_impact.index[0], rain_impact.index[-1]

wk = df.copy(); wk["week"] = wk["date"].dt.to_period("W").apply(lambda r: r.start_time)
full_weeks = wk.groupby("week")["date"].nunique()[lambda s: s == 7].index  # 양 끝의 덜 찬 주는 뺀다
wk = wk[wk["week"].isin(full_weeks)]
wk_total = wk.groupby("week")["amount"].sum()
wk_tx = wk.groupby("week")["tx_count"].sum()

day_total = df.groupby("date")["amount"].sum()
day_tx = df.groupby("date")["tx_count"].sum()
total_sales = df["amount"].sum()
total_tx = df["tx_count"].sum()
weather_uplift = rain_impact[top_rain]
rain_days_share = df.drop_duplicates(["date", "region"])["rainy"].mean() * 100


# ===========================================================================
# 1) 헤더
# ===========================================================================
st.markdown("<div class='hl'><span class='ic'>📊</span> 날씨 기반 소비 분석 대시보드</div>", unsafe_allow_html=True)
st.markdown("<div class='lead'>날씨에 따라 어떤 업종이, 어느 지역에서 더 잘 팔리는지 한눈에 보여주는 카드 소비 분석 대시보드입니다.</div>",
            unsafe_allow_html=True)
st.markdown(f"<div class='period'>분석 기간 {df['date'].min():%Y-%m-%d} ~ {df['date'].max():%Y-%m-%d} · "
            f"{len(sel_regions)}개 지역 · {len(sel_inds)}개 업종 · 비 오는 날 {rain_days_share:.0f}%</div>",
            unsafe_allow_html=True)


# ===========================================================================
# 2) KPI (비즈니스 지표)
# ===========================================================================
def kpi_card(col, label, value, delta, note, series, kind="area"):
    up = delta >= 0
    with col:
        st.markdown(f"<div class='kpi'><div class='lab'>{label}</div><div class='val'>{value}</div>"
                    f"<span class='badge {'bup' if up else 'bdn'}'>{'▲' if up else '▼'} {delta:+.1f}% {note}</span></div>",
                    unsafe_allow_html=True)
        st.plotly_chart(spark(series, NAVY, kind), use_container_width=True, config={"displayModeBar": False})

k = st.columns(4)
kpi_card(k[0], "총 소비금액", f"{total_sales/1e12:,.1f}조원", recent_delta(day_total), "최근 4주", wk_total.values)
kpi_card(k[1], "승인 건수", f"{total_tx/1e8:,.1f}억 건", recent_delta(day_tx), "최근 4주", wk_tx.values)
kpi_card(k[2], "객단가", f"{total_sales/total_tx:,.0f}원", recent_delta(day_total/day_tx), "최근 4주", (wk_total/wk_tx).values)
kpi_card(k[3], f"비 오는 날 소비 ({top_rain})", f"{weather_uplift:+.0f}%", weather_uplift, "평소 대비",
         df[df["industry"] == top_rain].groupby("date")["idx"].mean().iloc[-60:].values, kind="bar")
st.write(""); st.write("")


# ===========================================================================
# 3) 지도 (KPI 바로 아래)
# ===========================================================================
st.markdown(f"<div class='qh'>🗺️ 비 오는 날, {focus} 소비가 늘어나는 지역은?</div>", unsafe_allow_html=True)
st.markdown("<div class='qd'>날씨를 바꿔보세요. 소비지수 100 은 그 지역의 평소 수준입니다.</div>", unsafe_allow_html=True)

@st.cache_data
def load_korea_geojson():
    url = "https://raw.githubusercontent.com/southkorea/southkorea-maps/master/kostat/2013/json/skorea_provinces_geo_simple.json"
    try:
        with urlopen(url, timeout=10) as rsp:
            return json.load(rsp)
    except Exception:
        return None

mw = st.radio("날씨", ["맑은 날", "비 오는 날"], horizontal=True, key="mapw", label_visibility="collapsed")
geo = load_korea_geojson()
fdf = df[df["industry"] == focus]
gdf = (fdf[fdf["rainy"] == (mw == "비 오는 날")].groupby("region")["idx"].mean()
       .reindex(sel_regions).rename("소비지수").reset_index())
gdf["geo"] = gdf["region"].map({r: v["geo"] for r, v in REGIONS.items()})
if geo is None:
    st.info("지도 경계 파일을 불러오지 못했습니다 (인터넷 연결 확인). 지도 외 분석은 정상 동작합니다.")
else:
    span = max(5.0, float((fdf.groupby(["region", "rainy"])["idx"].mean() - 100).abs().max()))
    fm = go.Figure(go.Choropleth(geojson=geo, locations=gdf["geo"], z=gdf["소비지수"], customdata=gdf["region"],
        featureidkey="properties.name", colorscale=[[0, "#7f9c6b"], [0.5, "#f3f6f9"], [1, NAVY]],
        zmin=100 - span, zmax=100 + span, marker_line_width=0.6, marker_line_color="white",
        colorbar=dict(thickness=10, len=0.7, outlinewidth=0),
        hovertemplate="%{customdata}<br>소비지수 %{z:.1f}<extra></extra>"))
    fm.update_geos(fitbounds="locations", visible=False, bgcolor="rgba(0,0,0,0)")
    fm.update_layout(height=520, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)", dragmode=False)
    st.plotly_chart(fm, use_container_width=True, config={"scrollZoom": False, "displayModeBar": False})
st.write(""); st.write("")


# ===========================================================================
# 4) 핵심 차트
# ===========================================================================
st.markdown("<div class='qh'>📈 날씨에 따라 소비는 어떻게 움직일까?</div>", unsafe_allow_html=True)
st.markdown("<div class='qd'>주간 소비 흐름과 강수 패턴을 함께 보면 관계가 보입니다.</div>", unsafe_allow_html=True)
wr = wk.drop_duplicates(["date", "region"]).groupby("week")["rainfall"].mean()
tr = go.Figure()
tr.add_trace(go.Bar(x=wr.index, y=wr.values, name="일평균 강수량(mm)", marker_color="#dbe3ec", yaxis="y2",
                    hovertemplate="강수 %{y:.1f}mm<extra></extra>"))
tr.add_trace(go.Scatter(x=wk_total.index, y=wk_total.values / 1e12, name="주간 총 소비(조원)", mode="lines",
                        line=dict(color=NAVY, width=3, shape="spline"),
                        hovertemplate="소비 %{y:.2f}조원<extra></extra>"))
tr.update_layout(height=380, margin=dict(l=6, r=10, t=6, b=6),
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    font=dict(family="sans-serif", size=12, color="#37424f"),
    hovermode="x unified", legend=dict(orientation="h", y=-0.16, x=0),
    yaxis=dict(title="주간 소비(조원)", gridcolor=GRID, zeroline=False),
    yaxis2=dict(title="강수(mm)", overlaying="y", side="right", showgrid=False))
tr.update_xaxes(showgrid=False, showline=True, linecolor=LINE)
st.plotly_chart(tr, use_container_width=True)
st.write("")

c1, c2 = st.columns(2)
with c1:
    var = st.radio("X축", ["강수량", "기온", "습도"], horizontal=True, label_visibility="collapsed")
    st.markdown(f"<div class='ct'>{var}에 따라 {focus} 소비는 어떻게 달라질까?</div>", unsafe_allow_html=True)
    st.markdown("<div class='qd'>점 하나는 날씨가 비슷한 날들의 평균입니다. 우상향이면 값이 클수록 소비가 늘어난다는 뜻이에요.</div>",
                unsafe_allow_html=True)
    xcol = {"강수량": "rainfall", "기온": "temp", "습도": "humidity"}[var]
    tmp = fdf[[xcol, "idx"]].dropna().copy()
    if xcol == "rainfall":  # 비 안 온 날이 대부분이라 구간을 직접 나눈다
        tmp["bin"] = pd.cut(tmp[xcol], [-0.1, 0.1, 1, 3, 5, 10, 15, 20, 30, 50, 1000], labels=False)
    else:
        tmp["bin"] = pd.qcut(tmp[xcol].rank(method="first"), 14, labels=False)
    binned = tmp.groupby("bin").agg(x=(xcol, "mean"), y=("idx", "mean")).dropna()
    x = binned["x"].to_numpy(float); y = binned["y"].to_numpy(float)
    r = tmp[xcol].corr(tmp["idx"])
    sc = go.Figure(go.Scatter(x=x, y=y, mode="markers",
        marker=dict(color=IND_COLOR[focus], size=12, opacity=0.85, line=dict(color="white", width=1)),
        hovertemplate=f"{var} %{{x:.1f}}<br>소비지수 %{{y:.1f}}<extra></extra>"))
    if len(x) > 1 and np.ptp(x) > 0:
        m, bb = np.polyfit(x, y, 1); xs = np.linspace(x.min(), x.max(), 50)
        sc.add_trace(go.Scatter(x=xs, y=m*xs+bb, mode="lines", line=dict(color=RED, dash="dot", width=2.5),
                                hoverinfo="skip"))
    sc.add_annotation(xref="paper", yref="paper", x=0.02, y=0.98, showarrow=False,
        text=f"<b>일별 상관 r = {r:+.2f}</b>", font=dict(size=12, color=INK),
        bgcolor="rgba(255,255,255,0.9)", borderpad=4)
    sc.update_xaxes(title=f"{var}"); sc.update_yaxes(title=f"{focus} 소비지수 (평소=100)")
    st.plotly_chart(theme(sc, 330, legend=False), use_container_width=True)
with c2:
    st.write(""); st.write("")
    st.markdown("<div class='ct'>비 오는 날, 어떤 업종이 웃고 울까?</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='qd'>비 오는 날(일강수량 {RAIN_MM}mm 이상)의 소비가 그 외 날보다 얼마나 늘거나 줄었는지입니다.</div>",
                unsafe_allow_html=True)
    sens_rank = rain_impact.sort_values()
    sr = go.Figure(go.Bar(x=sens_rank.values, y=sens_rank.index, orientation="h",
        text=[f"{v:+.1f}%" for v in sens_rank.values], textposition="auto", cliponaxis=False,
        marker_color=[IND_COLOR[i] for i in sens_rank.index],
        hovertemplate="%{y} %{x:+.1f}%<extra></extra>"))
    sr.add_vline(x=0, line_color=SOFT, line_width=1)
    sr.update_xaxes(title="비 오는 날 소비 증감률(%)", ticksuffix="%")
    st.plotly_chart(theme(sr, 330, legend=False), use_container_width=True)
st.write("")


# ===========================================================================
# 5) 상세 분석 (expander)
# ===========================================================================
with st.expander("🔍 상세 분석 보기 (히트맵 · 트리맵 · 캘린더 · 권역 구성)"):
    st.markdown("##### 날씨 변수 x 업종 상관계수")
    z = cmat[["강수", "기온", "습도"]].values
    hm = go.Figure(go.Heatmap(z=z, x=["강수", "기온", "습도"], y=list(cmat.index),
        zmid=0, zmin=-0.6, zmax=0.6, colorscale=[[0, "#7f9c6b"], [0.5, "#f3f6f9"], [1, NAVY]],
        text=[[f"{v:+.2f}" for v in r] for r in z], texttemplate="%{text}", textfont=dict(size=12),
        colorbar=dict(thickness=10, len=0.7, outlinewidth=0)))
    hm.update_layout(height=320, margin=dict(l=6, r=6, t=6, b=6), paper_bgcolor="rgba(0,0,0,0)",
                     plot_bgcolor="rgba(0,0,0,0)", font=dict(family="sans-serif", size=12))
    hm.update_yaxes(autorange="reversed")
    st.plotly_chart(hm, use_container_width=True)

    e1, e2 = st.columns(2)
    with e1:
        st.markdown("##### 업종별 소비 비중 (색: 비 오는 날 증감률)")
        spend_by = df.groupby("industry")["amount"].sum().reindex(sel_inds)
        sens = rain_impact.reindex(sel_inds)
        tm = go.Figure(go.Treemap(labels=spend_by.index, parents=[""]*len(spend_by), values=spend_by.values,
            marker=dict(colors=sens.values, colorscale=[[0, "#7f9c6b"], [0.5, "#eef2f6"], [1, NAVY]],
                        cmid=0, line=dict(width=2, color="white")),
            texttemplate="<b>%{label}</b><br>%{percentRoot}",
            hovertemplate="%{label}<br>%{percentRoot:.0%}<extra></extra>"))
        tm.update_layout(height=320, margin=dict(l=4, r=4, t=4, b=4), paper_bgcolor="rgba(0,0,0,0)",
                         font=dict(family="sans-serif", size=12))
        st.plotly_chart(tm, use_container_width=True)
    with e2:
        st.markdown("##### 업종 x 권역 소비 구성 (%)")
        reg = df.groupby(["industry", "zone"])["amount"].sum().unstack().reindex(sel_inds)
        reg_pct = reg.div(reg.sum(axis=1), axis=0) * 100
        order = reg.sum(axis=1).sort_values().index
        sb = go.Figure()
        for j, rgn in enumerate(reg_pct.columns):
            sb.add_trace(go.Bar(y=order, x=reg_pct.loc[order, rgn], name=rgn, orientation="h",
                                marker_color=PALETTE[j % len(PALETTE)],
                                hovertemplate=f"{rgn} %{{x:.0f}}%<extra></extra>"))
        sb.update_layout(barmode="stack"); sb.update_xaxes(ticksuffix="%")
        st.plotly_chart(theme(sb, 320), use_container_width=True)

    st.markdown("##### 날짜별 소비 / 강수 캘린더")
    cal_metric = st.radio("지표", [f"{focus} 소비", "강수량"], horizontal=True, key="calm", label_visibility="collapsed")
    cal = dp.reset_index()[["date"]].copy()
    cal["val"] = dp[focus].values / 1e8 if cal_metric.endswith("소비") else dp["rainfall"].values
    unit = "억원" if cal_metric.endswith("소비") else "mm"
    cal["dow"] = cal["date"].dt.weekday
    cal["wk_idx"] = (cal["date"] - pd.to_timedelta(cal["dow"], unit="D") - cal["date"].min()).dt.days // 7
    cal["wk_idx"] = cal["wk_idx"] - cal["wk_idx"].min()
    DOW = ["월", "화", "수", "목", "금", "토", "일"]
    scale = [[0, "#eef2f6"], [1, NAVY]] if cal_metric.endswith("소비") else [[0, "#eef0e2"], [1, "#4f8a8b"]]
    weeks = cal.groupby("wk_idx")["date"].min()
    ticktext = [pd.Timestamp(d).strftime("%m/%d") if i % 4 == 0 else "" for i, d in enumerate(weeks.values)]
    calfig = go.Figure(go.Heatmap(x=cal["wk_idx"], y=cal["dow"], z=cal["val"], colorscale=scale,
        xgap=3, ygap=3, colorbar=dict(thickness=10, len=0.8, outlinewidth=0),
        hovertemplate=f"%{{customdata|%Y-%m-%d}}<br>%{{z:,.1f}}{unit}<extra></extra>", customdata=cal["date"]))
    calfig.update_layout(height=260, margin=dict(l=6, r=6, t=6, b=6), paper_bgcolor="rgba(0,0,0,0)",
                         plot_bgcolor="rgba(0,0,0,0)", font=dict(family="sans-serif", size=11, color="#37424f"))
    calfig.update_yaxes(tickmode="array", tickvals=list(range(7)), ticktext=DOW, autorange="reversed",
                        showgrid=False, zeroline=False)
    calfig.update_xaxes(tickmode="array", tickvals=list(weeks.index), ticktext=ticktext, showgrid=False, zeroline=False)
    st.plotly_chart(calfig, use_container_width=True)

st.write("")


# ===========================================================================
# 6) 추천 액션
# ===========================================================================
st.markdown("<div class='qh'>🎯 그래서, 무엇을 하면 될까?</div>", unsafe_allow_html=True)
st.markdown("<div class='qd'>분석 결과를 바로 실행으로 옮기는 추천 액션입니다.</div>", unsafe_allow_html=True)
winners = ", ".join(rain_impact[rain_impact > 0].index[:2]) or top_rain
losers = ", ".join(rain_impact[rain_impact < 0].index[::-1][:2]) or low_rain
reg_gain = fdf.groupby(["region", "rainy"])["idx"].mean().unstack()
top_regions = ", ".join((reg_gain[True] - reg_gain[False]).sort_values(ascending=False).index[:3]) if True in reg_gain else "-"
a1, a2 = st.columns(2)
with a1:
    st.markdown(f"""<div class="action"><div class="tag">Recommended Actions</div>
      <h3>비 오는 날, 이렇게 움직이세요</h3>
      <div class="act-item"><div class="h">☔ 비 예보 시 {winners} 프로모션 자동 실행</div>
        <div class="d">일강수량 {RAIN_MM}mm 이상 예보가 뜨면 수혜 업종 캠페인을 자동 발동</div></div>
      <div class="act-item"><div class="h">🎟️ {losers} 업종은 우천 방어 쿠폰</div>
        <div class="d">비 예보 당일 아침, 소비가 줄어드는 업종의 타깃 고객에게 쿠폰 푸시</div></div>
      <div class="act-item"><div class="h">📍 {focus} 민감 지역에 예산 우선 배분</div>
        <div class="d">비 오는 날 {focus} 소비가 가장 크게 움직이는 지역: {top_regions}</div></div>
    </div>""", unsafe_allow_html=True)
with a2:
    st.markdown(f"""<div class="action action2"><div class="tag">Evidence & Validation</div>
      <h3>근거와 검증 방법</h3>
      <div class="act-item"><div class="h">비 오는 날 {top_rain} {rain_impact[top_rain]:+.1f}% · {low_rain} {rain_impact[low_rain]:+.1f}%</div>
        <div class="d">같은 지역 · 업종의 평소 소비 대비, 비 오는 날과 그 외 날의 평균 비교</div></div>
      <div class="act-item"><div class="h">핵심 측정 지표</div>
        <div class="d">강수일 vs 비강수일 업종별 거래액 증감률, 쿠폰 전환율</div></div>
      <div class="act-item"><div class="h">더 검증할 것</div>
        <div class="d">요일 · 계절 효과를 통제해도 차이가 남는지, 강수 예보 지역 A/B 분할로 증분 매출 비교</div></div>
    </div>""", unsafe_allow_html=True)

st.write("")
st.caption("CardLab Analytics · 카드 소비는 실습용 가상 데이터입니다.")
