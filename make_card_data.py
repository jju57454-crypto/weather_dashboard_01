"""날씨 데이터와 조인할 수 있는 실습용 가상 카드 소비 데이터를 만든다.

사용법: python make_card_data.py          (먼저 collect_weather.py 를 실행해 둔다)

  입력: data/weather_daily.csv  → 같은 날짜 · 같은 시도의 실제 날씨를 읽어 소비에 반영한다.
  출력: data/card_daily.csv     → date, region, industry, amount(원), tx_count(승인 건수), customers(이용 고객 수)

  조인 키는 (date, region). 출력 파일에는 날씨 컬럼을 넣지 않는다. 조인은 수강생이 직접 한다.
  실제 카드사 데이터가 아니라 가상 데이터다. 금액 수준을 실제 시장 규모로 해석하지 않는다.
"""
from pathlib import Path

import numpy as np
import pandas as pd

from regions import REGIONS

HERE = Path(__file__).parent
SEED = 42

# base   : 인구 1명당 하루 평균 소비액(원)       ticket : 평균 객단가(원)
# rain   : 비가 충분히 올 때의 최대 증감률        temp   : 기온 10℃ 상승당 증감률
# extreme: 쾌적 기온(15℃)에서 10℃ 벗어날 때 증감률 (덥거나 추우면 함께 움직이는 업종)
# weekend: 토 · 일 배수                           metro  : 광역시에서의 소비 집중도
INDUSTRIES = {
    "배달":   {"base": 2600, "ticket": 24000, "rain":  0.24, "temp": -0.02, "extreme":  0.08, "weekend": 1.25, "metro": 1.25},
    "편의점": {"base": 1900, "ticket":  7500, "rain": -0.06, "temp":  0.07, "extreme":  0.00, "weekend": 1.05, "metro": 1.05},
    "엔터":   {"base":  900, "ticket": 18000, "rain":  0.10, "temp":  0.00, "extreme":  0.05, "weekend": 1.60, "metro": 1.30},
    "교통":   {"base": 2200, "ticket":  9000, "rain":  0.05, "temp":  0.00, "extreme":  0.02, "weekend": 0.80, "metro": 1.20},
    "음식점": {"base": 8500, "ticket": 32000, "rain": -0.09, "temp":  0.01, "extreme": -0.04, "weekend": 1.20, "metro": 1.05},
    "카페":   {"base": 1600, "ticket":  8500, "rain": -0.12, "temp":  0.09, "extreme":  0.00, "weekend": 1.15, "metro": 1.15},
    "패션":   {"base": 2400, "ticket": 62000, "rain": -0.16, "temp": -0.03, "extreme": -0.06, "weekend": 1.45, "metro": 1.20},
}
HOLIDAYS_2025 = pd.to_datetime([
    "2025-01-01", "2025-01-27", "2025-01-28", "2025-01-29", "2025-01-30", "2025-03-01", "2025-03-03",
    "2025-05-05", "2025-05-06", "2025-06-03", "2025-06-06", "2025-08-15", "2025-10-03", "2025-10-06",
    "2025-10-07", "2025-10-08", "2025-10-09", "2025-12-25",
])


def weather_effect(c: dict, w: pd.DataFrame, metro: bool) -> np.ndarray:
    """날씨가 소비에 주는 배수. 강수 효과는 10mm 안팎에서 빠르게 커지고 이후 포화한다."""
    rain_strength = 1 - np.exp(-w["rainfall"].to_numpy() / 8)
    region_sens = 1.25 if metro else 0.80  # 대도시가 비에 더 민감하게 반응한다
    rain = 1 + c["rain"] * region_sens * rain_strength
    temp = w["temp"].to_numpy()
    heat = 1 + c["temp"] * (temp - 15) / 10 + c["extreme"] * np.abs(temp - 15) / 10
    return rain * heat


def make() -> pd.DataFrame:
    weather = pd.read_csv(HERE / "data" / "weather_daily.csv", parse_dates=["date"])
    rng = np.random.default_rng(SEED)
    frames = []
    for region, info in REGIONS.items():
        w = weather[weather["region"] == region].sort_values("date")
        w = w.assign(rainfall=w["rainfall"].fillna(0), temp=w["temp"].interpolate(limit_direction="both"))
        dates = w["date"]
        weekend = (dates.dt.weekday >= 5).to_numpy() | dates.isin(HOLIDAYS_2025).to_numpy()
        payday = dates.dt.day.isin([25, 26, 27]).to_numpy()
        trend = 1 + 0.04 * np.arange(len(dates)) / max(len(dates) - 1, 1)  # 연간 4% 완만한 성장
        for ind, c in INDUSTRIES.items():
            skew = c["metro"] if info["metro"] else 1 / c["metro"] ** 0.5
            amount = (c["base"] * info["pop"] * 10_000 * skew * trend
                      * np.where(weekend, c["weekend"], 1.0)
                      * np.where(payday, 1.06, 1.0)
                      * weather_effect(c, w, info["metro"])
                      * rng.normal(1, 0.05, len(dates)))
            tx = amount / (c["ticket"] * rng.normal(1, 0.03, len(dates)))
            frames.append(pd.DataFrame({
                "date": dates.dt.strftime("%Y-%m-%d"), "region": region, "industry": ind,
                "amount": amount.round(-3).astype("int64"),
                "tx_count": tx.round().astype("int64"),
                "customers": (tx * rng.uniform(0.78, 0.86, len(dates))).round().astype("int64"),
            }))
    return pd.concat(frames, ignore_index=True).sort_values(["date", "region", "industry"], ignore_index=True)


if __name__ == "__main__":
    card = make()
    out = HERE / "data" / "card_daily.csv"
    card.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"{len(card)}행 → {out}")
    print(f"기간 {card['date'].min()} ~ {card['date'].max()} · 시도 {card['region'].nunique()}개 · 업종 {card['industry'].nunique()}개")
