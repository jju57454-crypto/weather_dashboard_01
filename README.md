# 날씨 × 카드 소비 데이터 분석 대시보드 (실습 프로젝트)

날씨 API로 받은 실제 날씨와 실습용 가상 카드 소비 데이터를 조인해 Streamlit 대시보드로 보여준다.
진행 순서는 `student_guide.html` (실습 노트)을 브라우저로 열어 따라 한다.

```bash
python3 -m pip install -r requirements.txt   # Windows는 python -m pip ...
python3 collect_weather.py     # 1) 날씨 수집 → data/weather_daily.csv
python3 make_card_data.py      # 2) 카드 소비 생성 → data/card_daily.csv
python3 -m streamlit run app.py   # 3) 완성본 대시보드
```

`data/` 에 CSV 두 개가 이미 들어 있어서 1, 2번을 건너뛰어도 3번은 바로 된다.

| 파일 | 역할 |
|---|---|
| `CLAUDE.md` | Claude Code에게 주는 프로젝트 규칙 |
| `regions.py` | 17개 시도 기준 정보 (ASOS 지점번호 · 좌표 · 인구 · 권역) |
| `collect_weather.py` | 시도별 일별 날씨 수집. 오픈 메테오(키 불필요) 또는 기상청 ASOS 일자료 |
| `make_card_data.py` | 수집한 날씨를 반영한 가상 카드 소비 데이터 생성 (시드 고정) |
| `app.py` | 완성본 대시보드 |
| `my_dashboard.py` | 수강생이 Claude Code로 만드는 대시보드 (실습 4에서 생긴다) |
| `student_guide.html` | 수강생 실습 노트 |

`.claude/`, `.streamlit/`, `.env.example`, `.gitignore` 는 이름이 점(.)으로 시작해서 Finder · 탐색기에서 안 보일 수 있다. VS Code 탐색기에서는 보인다. 지우지 않는다.

## 데이터

조인 키는 `(date, region)` 이다.

| 파일 | 행 | 컬럼 |
|---|---|---|
| `data/weather_daily.csv` | 6,205 (17개 시도 × 365일) | `date, region, stn_id, temp, temp_max, temp_min, rainfall, humidity, wind, source` |
| `data/card_daily.csv` | 43,435 (× 업종 7개) | `date, region, industry, amount, tx_count, customers` |

- 단위: `temp` ℃ · `rainfall` mm · `humidity` % · `wind` m/s · `amount` 원 · `tx_count` 승인 건수 · `customers` 이용 고객 수
- 업종 7개: 배달 · 편의점 · 엔터 · 교통 · 음식점 · 카페 · 패션
- 날씨는 오픈 메테오(Open-Meteo) 재분석 자료다. 관측소 실측값이 아니라 모델 추정치라 기상청 값과 조금 다를 수 있다.
- 카드 소비는 가상 데이터다. 금액 수준을 실제 시장 규모로 해석하지 않는다.

## 기상청 API로 받기 (선택)

1. 공공데이터포털(data.go.kr)에서 "기상청_지상(종관, ASOS) 일자료 조회서비스" 활용 신청
2. `.env.example` 을 `.env` 로 복사하고 일반 인증키(Decoding)를 `DATA_GO_KR_KEY` 에 넣는다
3. `python3 collect_weather.py --source kma` → `python3 make_card_data.py`

날씨 소스를 바꾸면 카드 데이터도 다시 생성한다. 그러면 실습 노트의 정답 값과 숫자가 달라진다.
