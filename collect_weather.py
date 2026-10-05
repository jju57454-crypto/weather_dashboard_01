"""17개 시도의 일별 날씨를 API로 받아 data/weather_daily.csv 로 저장한다.

사용법: python collect_weather.py [--start 2025-01-01] [--end 2025-12-31] [--source kma|open-meteo]

  kma        : 기상청 지상(종관, ASOS) 일자료 · 공공데이터포털 API. .env 의 DATA_GO_KR_KEY 필요.
  open-meteo : 인증키 없이 쓰는 대체 API(재분석 자료). 키 발급을 기다리는 동안 실습용으로 쓴다.
  --source 를 생략하면 키가 있을 때 kma, 없을 때 open-meteo 를 쓴다.

출력 컬럼: date, region, stn_id, temp(평균기온 ℃), temp_max, temp_min,
          rainfall(일강수량 mm), humidity(평균 상대습도 %), wind(평균 풍속 m/s), source
"""
import argparse
import datetime as dt
import os
import time
from pathlib import Path

import pandas as pd
import requests

from regions import REGIONS

HERE = Path(__file__).parent
OUT = HERE / "data" / "weather_daily.csv"
KMA_URL = "https://apis.data.go.kr/1360000/AsosDalyInfoService/getWthrDataList"
OM_URL = "https://archive-api.open-meteo.com/v1/archive"
PAGE_SIZE = 999  # 공공데이터포털 1회 요청 상한


def load_env() -> None:
    """.env 의 KEY=VALUE 를 환경변수로 올린다."""
    env = HERE / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def fetch_kma(stn_id: str, start: dt.date, end: dt.date) -> pd.DataFrame:
    """한 지점의 ASOS 일자료를 페이지 끝까지 받는다."""
    items, page = [], 1
    while True:
        params = {
            "serviceKey": os.environ["DATA_GO_KR_KEY"],  # Decoding 키
            "dataType": "JSON", "dataCd": "ASOS", "dateCd": "DAY",
            "startDt": f"{start:%Y%m%d}", "endDt": f"{end:%Y%m%d}",
            "stnIds": stn_id, "numOfRows": PAGE_SIZE, "pageNo": page,
        }
        r = requests.get(KMA_URL, params=params, timeout=30)
        try:
            data = r.json()
        except ValueError:  # 인증키 오류 등은 JSON 이 아닌 본문으로 온다
            raise RuntimeError(f"HTTP {r.status_code} · JSON 아님 → {r.text[:200]}")
        header = data["response"]["header"]
        if header["resultCode"] != "00":
            raise RuntimeError(f"resultCode {header['resultCode']} {header['resultMsg']}")
        body = data["response"]["body"]
        items += body["items"]["item"] if body["items"] else []
        if page * PAGE_SIZE >= body["totalCount"]:
            break
        page += 1
        time.sleep(0.2)
    raw = pd.DataFrame(items)
    num = lambda c: pd.to_numeric(raw[c], errors="coerce")
    return pd.DataFrame({
        "date": raw["tm"],
        "temp": num("avgTa"), "temp_max": num("maxTa"), "temp_min": num("minTa"),
        "rainfall": num("sumRn").fillna(0.0),  # 비가 안 온 날은 빈 문자열로 온다
        "humidity": num("avgRhm"), "wind": num("avgWs"),
    })


def fetch_open_meteo(lat: float, lon: float, start: dt.date, end: dt.date) -> pd.DataFrame:
    params = {
        "latitude": lat, "longitude": lon, "start_date": start.isoformat(), "end_date": end.isoformat(),
        "daily": "temperature_2m_mean,temperature_2m_max,temperature_2m_min,"
                 "precipitation_sum,relative_humidity_2m_mean,wind_speed_10m_mean",
        "timezone": "Asia/Seoul",
    }
    r = requests.get(OM_URL, params=params, timeout=30)
    r.raise_for_status()
    d = r.json()["daily"]
    return pd.DataFrame({
        "date": d["time"],
        "temp": d["temperature_2m_mean"], "temp_max": d["temperature_2m_max"], "temp_min": d["temperature_2m_min"],
        "rainfall": d["precipitation_sum"], "humidity": d["relative_humidity_2m_mean"],
        "wind": [None if v is None else round(v / 3.6, 1) for v in d["wind_speed_10m_mean"]],  # km/h → m/s
    })


if __name__ == "__main__":
    load_env()
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2025-01-01")
    ap.add_argument("--end", default="2025-12-31")
    ap.add_argument("--source", choices=["kma", "open-meteo"])
    a = ap.parse_args()
    start, end = dt.date.fromisoformat(a.start), dt.date.fromisoformat(a.end)
    source = a.source or ("kma" if os.environ.get("DATA_GO_KR_KEY") else "open-meteo")
    if source == "kma" and not os.environ.get("DATA_GO_KR_KEY"):
        raise SystemExit(".env 에 DATA_GO_KR_KEY 가 없습니다. .env.example 을 참고하세요.")
    print(f"수집 소스: {source} · 기간 {start} ~ {end}")

    frames = []
    for region, info in REGIONS.items():
        if source == "kma":
            df = fetch_kma(info["stn"], start, end)
        else:
            df = fetch_open_meteo(info["lat"], info["lon"], start, end)
        df.insert(1, "region", region)
        df.insert(2, "stn_id", info["stn"])
        df["source"] = source
        frames.append(df)
        print(f"  {region}({info['stn_name']} {info['stn']}): {len(df)}행")
        time.sleep(0.3)

    out = pd.concat(frames, ignore_index=True)
    OUT.parent.mkdir(exist_ok=True)
    out.to_csv(OUT, index=False, encoding="utf-8-sig")  # 같은 기간은 덮어쓰기 (멱등)
    print(f"{len(out)}행 → {OUT}")
    print("결측 건수:", out.isna().sum()[lambda s: s > 0].to_dict() or "없음")
