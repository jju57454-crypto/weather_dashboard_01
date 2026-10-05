"""날씨 × 카드 소비 대시보드 (수강생 버전).

실행: python3 my_dashboard.py              (내부에서 streamlit run 으로 다시 띄운다)
  또는 python3 -m streamlit run my_dashboard.py

  - data/card_daily.csv 와 data/weather_daily.csv 를 (date, region) 으로 조인한다.
  - 소비지수 = 지역 · 업종별 2025년 평균 금액을 100 으로 둔 값. 필터와 상관없이 전체 기간으로 계산한다.
  - 비 오는 날 = 일강수량(rainfall) 3mm 이상인 날. 맑은 날 = 그 외(3mm 미만) 날.
  - 비 오는 날 효과는 단순 비교와, 같은 지역 · 같은 달 · 같은 평일/주말끼리 비교한 통제 비교를 함께 보여준다.
  - 카드 소비는 가상 데이터, 날씨는 오픈 메테오 재분석 자료다.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
from plotly.subplots import make_subplots

from regions import REGIONS

HERE = Path(__file__).parent
DATA = HERE / "data"
GEO_URL = ("https://raw.githubusercontent.com/southkorea/southkorea-maps/master/"
           "kostat/2013/json/skorea_provinces_geo_simple.json")
GEO_CACHE = DATA / "skorea_provinces_geo_simple.json"  # 한 번 받으면 다음부터는 오프라인으로 쓴다
RAIN_MM = 3.0
STRATA = ["region", "month", "weekend"]  # 통제 비교의 층: 같은 지역 · 같은 달 · 같은 평일/주말
WEATHER_VARS = {"강수량 (mm)": "rainfall", "평균기온 (℃)": "temp", "평균 습도 (%)": "humidity"}
COLOR_MAIN, COLOR_SUB, COLOR_RAIN = "#2b6cb0", "#b8bec7", "#8fbce6"


# ---------------------------------------------------------------- 데이터
@st.cache_data
def load_data() -> tuple[pd.DataFrame, int]:
    weather = pd.read_csv(DATA / "weather_daily.csv", dtype={"stn_id": str})
    card = pd.read_csv(DATA / "card_daily.csv")
    df = card.merge(weather, on=["date", "region"], how="left", validate="m:1", indicator=True)
    unmatched = int((df.pop("_merge") != "both").sum())
    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.month
    df["weekend"] = df["date"].dt.weekday >= 5
    df["rain"] = df["rainfall"] >= RAIN_MM
    df["week"] = df["date"].dt.to_period("W-SUN").dt.start_time  # 월요일 시작 주
    df["idx"] = df["amount"] / df.groupby(["region", "industry"])["amount"].transform("mean") * 100
    df["geo"] = df["region"].map({k: v["geo"] for k, v in REGIONS.items()})
    return df, unmatched


@st.cache_data(show_spinner="시도 경계 파일을 불러오는 중...")
def load_geojson() -> dict | None:
    if GEO_CACHE.exists():
        return json.loads(GEO_CACHE.read_text(encoding="utf-8"))
    try:
        r = requests.get(GEO_URL, timeout=15)
        r.raise_for_status()
        geo = r.json()
    except (requests.RequestException, ValueError):
        return None  # 인터넷이 없으면 좌표 점 지도로 대신 그린다
    GEO_CACHE.write_text(json.dumps(geo, ensure_ascii=False), encoding="utf-8")
    return geo


def rain_effect(d: pd.DataFrame, by: str = "industry") -> pd.DataFrame:
    """by 별 비 오는 날 증감률(%).

    단순 비교: 비 오는 날 평균 지수 / 그 외 날 평균 지수 - 1
    통제 비교: 같은 지역 · 같은 달 · 같은 평일/주말 층마다 위 비율을 구해 층별 비 오는 날 수로 가중평균.
              비 오는 날과 그 외 날이 둘 다 있는 층만 쓴다.
    """
    s = d.groupby([by, "rain"])["idx"].mean().unstack("rain").reindex(columns=[True, False])
    keys = list(dict.fromkeys([by, *STRATA]))
    m = d.groupby(keys + ["rain"])["idx"].mean().unstack("rain").reindex(columns=[True, False]).dropna()
    m["n"] = d[d["rain"]].groupby(keys).size().reindex(m.index)
    m["w"] = (m[True] / m[False] - 1) * m["n"]
    g = m.groupby(level=by)[["w", "n"]].sum()
    return pd.DataFrame({
        "비 오는 날 지수": s[True],
        "맑은 날 지수": s[False],
        "단순 비교": (s[True] / s[False] - 1) * 100,
        "통제 비교": g["w"] / g["n"] * 100,
        "비 오는 날 수": d[d["rain"]].groupby(by).size(),
    }).dropna(subset=["단순 비교"])


def region_days(d: pd.DataFrame) -> pd.DataFrame:
    """지역-날짜 단위 날씨 (업종 수만큼 반복된 행을 하나로)."""
    return d.drop_duplicates(["date", "region"])


def josa(word: str, with_final: str, without_final: str) -> str:
    """끝 글자 받침에 맞춰 조사를 붙인다. 예: josa('부산', '이', '가') → '부산이', josa('패션', '은', '는') → '패션은'"""
    c = word[-1]
    has_final = "가" <= c <= "힣" and (ord(c) - 0xAC00) % 28 != 0
    return word + (with_final if has_final else without_final)


def fmt_won(v: float) -> str:
    if v >= 1e12:
        return f"{v / 1e12:,.1f}조 원"
    if v >= 1e8:
        return f"{v / 1e8:,.1f}억 원"
    return f"{v:,.0f}원"


def fmt_count(v: float) -> str:
    if v >= 1e8:
        return f"{v / 1e8:,.2f}억 건"
    if v >= 1e4:
        return f"{v / 1e4:,.0f}만 건"
    return f"{v:,.0f}건"


# ---------------------------------------------------------------- 화면 조각
def section_kpi(d: pd.DataFrame, eff: pd.DataFrame) -> None:
    amount, tx = d["amount"].sum(), d["tx_count"].sum()
    top = eff["통제 비교"].abs().idxmax()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("총 소비금액", fmt_won(amount), border=True,
              help="가상 카드 데이터의 합계라 실제 시장 규모로 해석하지 않는다.")
    c2.metric("승인 건수", fmt_count(tx), border=True)
    c3.metric("객단가", f"{amount / tx:,.0f}원", border=True, help="총 소비금액 ÷ 승인 건수")
    c4.metric("비 오는 날 증감률이 가장 큰 업종", top, delta=f"{eff.loc[top, '통제 비교']:+.1f}% (통제 비교)", border=True,
              help=f"절댓값 기준. 같은 지역 · 같은 달 · 같은 평일/주말끼리 비교한 소비지수 증감률. "
                   f"단순 비교는 {eff.loc[top, '단순 비교']:+.1f}%.")


def section_map(df_focus: pd.DataFrame, focus: str) -> None:
    st.subheader(f"시도별 {focus} 소비지수: 맑은 날 vs 비 오는 날")
    day = st.segmented_control("날씨", ["맑은 날", "비 오는 날"], default="비 오는 날", key="day_type") or "비 오는 날"
    col = f"{day} 지수"

    reg = rain_effect(df_focus, by="region").reset_index(names="region")
    reg["geo"] = reg["region"].map({k: v["geo"] for k, v in REGIONS.items()})
    reg["lat"] = reg["region"].map({k: v["lat"] for k, v in REGIONS.items()})
    reg["lon"] = reg["region"].map({k: v["lon"] for k, v in REGIONS.items()})
    span = max(abs(reg[["맑은 날 지수", "비 오는 날 지수"]] - 100).max().max(), 1)  # 두 상태에서 같은 색 범위
    style = dict(color=col, color_continuous_scale="RdBu", range_color=[100 - span, 100 + span], hover_name="region",
                 hover_data={"geo": False, "lat": False, "lon": False, "맑은 날 지수": ":.1f", "비 오는 날 지수": ":.1f",
                             "통제 비교": ":+.1f", "비 오는 날 수": True},
                 labels={col: "소비지수", "통제 비교": "통제 증감률(%)"})

    left, right = st.columns([3, 2])
    with left:
        geo = load_geojson()
        if geo:
            fig = px.choropleth(reg, geojson=geo, locations="geo", featureidkey="properties.name", **style)
        else:
            st.caption("시도 경계 파일을 받지 못해 시도 대표 좌표로 표시한다.")
            fig = px.scatter_geo(reg, lat="lat", lon="lon", size=[18] * len(reg), **style)
        fig.update_geos(fitbounds="locations", visible=False)
        fig.update_layout(height=520, margin=dict(l=0, r=0, t=10, b=0), coloraxis_colorbar=dict(title="소비지수"))
        st.plotly_chart(fig, key="map")
    with right:
        table = reg[["region", "맑은 날 지수", "비 오는 날 지수", "단순 비교", "통제 비교", "비 오는 날 수"]]
        st.dataframe(table.sort_values("통제 비교", ascending=False), hide_index=True, height=480, column_config={
            "region": "지역",
            "맑은 날 지수": st.column_config.NumberColumn(format="%.1f"),
            "비 오는 날 지수": st.column_config.NumberColumn(format="%.1f"),
            "단순 비교": st.column_config.NumberColumn("단순 증감률", format="%+.1f%%"),
            "통제 비교": st.column_config.NumberColumn("통제 증감률", format="%+.1f%%"),
            "비 오는 날 수": st.column_config.NumberColumn("비 오는 날(일)"),
        })
    st.caption("지도 색은 해당 날씨의 평균 소비지수(지역 · 업종별 연평균 = 100)다. 맑은 날 = 일강수량 3mm 미만. "
               "평균에는 계절 · 요일 효과가 섞여 있으니, 비 효과는 표의 통제 증감률(같은 지역 · 월 · 평일/주말끼리 비교)로 본다.")


def section_weekly(d: pd.DataFrame, df_focus: pd.DataFrame, focus: str) -> None:
    st.subheader("주간 소비와 주간 강수량")
    basis = st.segmented_control("소비 기준", ["필터 전체 소비금액", f"{focus} 소비지수"],
                                 default="필터 전체 소비금액", key="weekly_basis") or "필터 전체 소비금액"
    wd = region_days(d)
    days = wd.groupby("week")["date"].nunique()
    full = days[days == 7].index  # 1월 첫 주 · 12월 마지막 주처럼 7일이 안 되는 주는 뺀다
    rain = wd.groupby(["week", "region"])["rainfall"].sum().groupby("week").mean().reindex(full)
    if basis == "필터 전체 소비금액":
        spend = d.groupby("week")["amount"].sum().reindex(full)
        scale, unit = (1e12, "조 원") if spend.max() >= 1e12 else (1e8, "억 원")
        spend, name = spend / scale, "주간 소비금액"
    else:
        spend, name, unit = df_focus.groupby("week")["idx"].mean().reindex(full), f"{focus} 주간 소비지수", "지수"

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=rain.index, y=rain, name="주간 강수량 (지역 평균, mm)", marker_color=COLOR_RAIN,
                         opacity=0.7, hovertemplate="%{x|%m/%d} 주<br>%{y:.1f} mm<extra></extra>"), secondary_y=True)
    fig.add_trace(go.Scatter(x=spend.index, y=spend, name=f"{name} ({unit})", mode="lines+markers",
                             line=dict(color="#d64045", width=2), marker=dict(size=4),
                             hovertemplate=f"%{{x|%m/%d}} 주<br>%{{y:,.1f}} {unit}<extra></extra>"), secondary_y=False)
    fig.update_yaxes(title_text=f"{name} ({unit})", secondary_y=False, tickformat=",.2~f")
    fig.update_yaxes(title_text="강수량 (mm)", secondary_y=True, showgrid=False, tickmode="auto", rangemode="tozero")
    fig.update_layout(height=400, margin=dict(l=10, r=10, t=10, b=10), hovermode="x unified",
                      legend=dict(orientation="h", y=1.08, x=0))
    st.plotly_chart(fig, key="weekly")
    r = np.corrcoef(spend, rain)[0, 1]
    st.caption(f"7일이 다 있는 {len(full)}주 ({full.min():%m/%d} ~ {(full.max() + pd.Timedelta(days=6)):%m/%d}). "
               f"강수량은 선택 지역별 주간 합계의 평균. 주간 상관계수 r = {r:+.2f} (계절 효과가 섞인 참고값).")


def section_scatter(df_focus: pd.DataFrame, focus: str) -> None:
    st.subheader(f"날씨 변수와 {focus} 소비지수")
    label = st.segmented_control("날씨 변수", list(WEATHER_VARS), default="강수량 (mm)", key="scatter_var") or "강수량 (mm)"
    x = WEATHER_VARS[label]
    p = df_focus.assign(요일=np.where(df_focus["weekend"], "주말", "평일"), 날짜=df_focus["date"].dt.strftime("%Y-%m-%d"))
    fig = px.scatter(p, x=x, y="idx", color="요일", opacity=0.35, category_orders={"요일": ["평일", "주말"]},
                     color_discrete_map={"평일": "#8a96a3", "주말": "#e07b39"}, hover_data=["날짜", "region"],
                     labels={x: label, "idx": f"{focus} 소비지수", "region": "지역"})
    bins = (pd.cut(p[x], [-0.01, 0.0, RAIN_MM - 0.01, 10, 20, 40, np.inf]) if x == "rainfall"
            else pd.qcut(p[x], 10, duplicates="drop"))
    curve = p.groupby(bins, observed=True).agg(x=(x, "median"), y=("idx", "mean"), n=("idx", "size"))
    fig.add_trace(go.Scatter(x=curve["x"], y=curve["y"], mode="lines+markers", name="구간 평균",
                             line=dict(color="#222", width=2), customdata=curve["n"],
                             hovertemplate="구간 중앙값 %{x:.1f}<br>평균 지수 %{y:.1f}<br>%{customdata}일<extra></extra>"))
    if x == "rainfall":
        fig.add_vline(x=RAIN_MM, line_dash="dot", line_color="#555",
                      annotation_text="비 오는 날 기준 3mm", annotation_position="bottom right")
    fig.add_hline(y=100, line_color="#bbb", line_width=1)
    fig.update_layout(height=430, margin=dict(l=10, r=10, t=40, b=10),
                      legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0, title_text=""))
    st.plotly_chart(fig, key="scatter")
    rho = p[x].rank().corr(p["idx"].rank())  # 스피어만 순위 상관 (scipy 없이 순위의 피어슨 상관으로 계산)
    st.caption(f"점 하나 = 지역-날짜 하나 ({len(p):,}개). 검은 선은 {label} 구간별 평균 지수. "
               f"순위 상관계수 = {rho:+.2f}. 계절 · 요일 효과가 섞인 원자료라 인과로 읽지 않는다.")


def section_bars(eff: pd.DataFrame) -> None:
    st.subheader("업종별 비 오는 날 증감률")
    e = eff.sort_values("통제 비교")
    fig = go.Figure()
    for col, color in [("단순 비교", COLOR_SUB), ("통제 비교", COLOR_MAIN)]:
        fig.add_trace(go.Bar(y=e.index, x=e[col], orientation="h", name=col, marker_color=color,
                             text=e[col].map("{:+.1f}%".format), textposition="outside",
                             hovertemplate="%{y} · " + col + " %{x:+.1f}%<extra></extra>"))
    fig.add_vline(x=0, line_color="#888", line_width=1)
    lim = max(e[["단순 비교", "통제 비교"]].abs().max().max() * 1.25, 1)
    fig.update_layout(barmode="group", height=110 + 52 * len(e), margin=dict(l=10, r=10, t=10, b=10),
                      xaxis=dict(title="비 오는 날 소비지수 증감률 (%)", range=[-lim, lim], ticksuffix="%"),
                      legend=dict(orientation="h", y=1.06, x=0, traceorder="reversed"))
    st.plotly_chart(fig, key="bars")
    st.caption("단순 비교 = 비 오는 날 평균 지수 ÷ 맑은 날 평균 지수 - 1. "
               "통제 비교 = 같은 지역 · 같은 달 · 같은 평일/주말끼리 비교한 증감률의 가중평균(가중치 = 비 오는 날 수).")


def section_actions(d: pd.DataFrame, df_regions: pd.DataFrame, eff: pd.DataFrame) -> None:
    st.subheader("추천 액션")
    st.caption("숫자는 현재 필터로 계산한 [확인된 사실], 해석과 제안은 [추정]이다.")
    wd = region_days(d)
    n_rain, share = int(wd["rain"].sum()), wd["rain"].mean() * 100
    by_month = wd.groupby("month")["rain"].mean().mul(100).sort_values(ascending=False)
    cards = []

    up = eff[eff["통제 비교"] > 0]["통제 비교"]
    if not up.empty:
        u = up.idxmax()
        reg = rain_effect(df_regions[df_regions["industry"] == u], by="region")["통제 비교"]
        where = f" 지역별로는 {josa(reg.idxmax(), '이', '가')} {reg.max():+.1f}%로 가장 크다." if len(reg) > 1 else ""
        (m1, p1), (m2, p2) = list(by_month.items())[:2]
        cards.append((f"비 예보일 {u} 프로모션 강화",
                      f"비 오는 날 {u} 소비지수는 {eff.loc[u, '통제 비교']:+.1f}%다(단순 비교 {eff.loc[u, '단순 비교']:+.1f}%)."
                      f"{where} 비 오는 날 비율이 높은 달은 {m1}월({p1:.0f}%), {m2}월({p2:.0f}%)이다.",
                      f"비 예보가 있는 날, 특히 {m1} · {m2}월에 {u} 쿠폰 · 푸시를 늘리면 늘어나는 수요를 잡을 수 있다."))

    down = eff[eff["통제 비교"] < 0]["통제 비교"]
    if not down.empty:
        dn = down.idxmin()
        e = eff.loc[dn, "통제 비교"] / 100
        rows = d[(d["industry"] == dn)]
        lost = (rows.loc[rows["rain"], "amount"] * (1 / (1 + e) - 1)).sum()
        cards.append((f"비 오는 날 {dn} 매출 방어",
                      f"비 오는 날 {dn} 소비지수는 {eff.loc[dn, '통제 비교']:+.1f}%다(단순 비교 {eff.loc[dn, '단순 비교']:+.1f}%). "
                      f"선택 지역의 비 오는 날은 {n_rain:,}일(지역-날짜의 {share:.1f}%)이다.",
                      f"이 감소가 비 때문이라면, 비가 안 왔을 때보다 연간 {dn} 소비가 약 {lost / rows['amount'].sum() * 100:.1f}% 적었다. "
                      f"우천 할인 · 포장 및 배달 전환 혜택으로 일부를 되찾을 수 있다."))

    gap = (eff["단순 비교"] - eff["통제 비교"]).abs()
    g = gap.idxmax()
    mix = wd.assign(summer=wd["month"].between(6, 10)).groupby("rain")[["summer", "weekend"]].mean().mul(100)
    cards.append(("캠페인 성과는 같은 달 · 같은 요일끼리 비교",
                  f"{josa(g, '은', '는')} 단순 비교로 {eff.loc[g, '단순 비교']:+.1f}%지만, 같은 지역 · 월 · 평일/주말끼리 비교하면 "
                  f"{eff.loc[g, '통제 비교']:+.1f}%다(차이 {gap[g]:.1f}%p). 6~10월 비율은 비 오는 날 {mix.loc[True, 'summer']:.0f}% vs "
                  f"맑은 날 {mix.loc[False, 'summer']:.0f}%, 주말 비율은 {mix.loc[True, 'weekend']:.0f}% vs {mix.loc[False, 'weekend']:.0f}%다.",
                  "비 오는 날이 특정 계절 · 요일에 몰려 있어서, 날씨 캠페인 효과를 단순 비교로 재면 계절 · 요일 효과를 "
                  "캠페인 효과로 착각할 수 있다. 성과 리포트는 같은 달 · 같은 요일 유형끼리 비교한다."))

    for col, (title, fact, guess) in zip(st.columns(len(cards)), cards):
        with col.container(border=True, height="stretch"):
            st.markdown(f"**{title}**")
            st.markdown(f"**[확인된 사실]** {fact}")
            st.markdown(f"**[추정]** {guess}")


# ---------------------------------------------------------------- 페이지
def main() -> None:
    st.set_page_config(page_title="날씨 × 카드 소비 대시보드", page_icon="🌧️", layout="wide")
    df, unmatched = load_data()
    regions_all, industries_all = list(REGIONS), sorted(df["industry"].unique())

    with st.sidebar:
        st.header("필터")
        regions = st.multiselect("지역", regions_all, default=regions_all)
        industries = st.multiselect("업종", industries_all, default=industries_all)
        st.divider()
        options = industries or industries_all
        focus = st.selectbox("심층 분석 업종", options, index=options.index("배달") if "배달" in options else 0,
                             help="지도 · 주간 소비지수 · 산점도에 쓰인다.")
        st.divider()
        st.caption(f"비 오는 날 = 일강수량 {RAIN_MM:g}mm 이상\n\n소비지수 = 지역 · 업종별 2025년 평균 금액 = 100")

    st.title("날씨 × 카드 소비 대시보드")
    if not regions or not industries:
        st.warning("사이드바에서 지역과 업종을 하나 이상 고르세요.")
        st.stop()

    df_regions = df[df["region"].isin(regions)]
    d = df_regions[df_regions["industry"].isin(industries)]
    df_focus = df_regions[df_regions["industry"] == focus]
    wd = region_days(d)
    st.caption(f"기준: {d['date'].min():%Y-%m-%d} ~ {d['date'].max():%Y-%m-%d} ({d['date'].nunique()}일) · "
               f"시도 {len(regions)}개 · 업종 {len(industries)}개 · 조인 {len(d):,}행 (짝 안 맞는 행 {unmatched}) · "
               f"비 오는 날 {int(wd['rain'].sum()):,} / {len(wd):,} 지역-날짜 ({wd['rain'].mean() * 100:.1f}%)")

    eff = rain_effect(d)
    section_kpi(d, eff)
    st.divider()
    section_map(df_focus, focus)
    st.divider()
    section_weekly(d, df_focus, focus)
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        section_scatter(df_focus, focus)
    with c2:
        section_bars(eff)
    st.divider()
    section_actions(d, df_regions, eff)
    st.divider()
    st.caption("한계: 카드 소비는 실습용 가상 데이터라 금액을 실제 시장 규모로 해석하지 않는다. "
               "날씨는 오픈 메테오 재분석 자료(모델 추정값)라 기상청 관측값과 다를 수 있다. 공휴일은 평일로 분류했다.")


if __name__ == "__main__":
    from streamlit.runtime.scriptrunner import get_script_run_ctx

    if get_script_run_ctx(suppress_warning=True):
        main()
    else:  # python3 my_dashboard.py 로 실행하면 streamlit 으로 다시 띄운다
        from streamlit.web import cli as stcli

        sys.argv = ["streamlit", "run", str(Path(__file__).resolve())]
        sys.exit(stcli.main())
