"""17개 시도 기준 정보. 날씨 수집 · 카드 데이터 생성 · 대시보드가 함께 쓴다.

조인 키는 (date, region) 이다. region 은 아래 딕셔너리의 키(시도 약칭)와 같다.
  stn  : 기상청 ASOS 대표 지점번호      lat/lon : Open-Meteo 대체 수집용 좌표
  pop  : 인구(만 명, 카드 소비 규모용)   geo     : 지도 경계 파일의 시도 이름
  zone : 권역                            metro   : 특별 · 광역시 여부
"""

REGIONS = {
    "서울": {"stn": "108", "stn_name": "서울", "lat": 37.57, "lon": 126.97, "pop": 933, "geo": "서울특별시", "zone": "수도권", "metro": True},
    "부산": {"stn": "159", "stn_name": "부산", "lat": 35.10, "lon": 129.03, "pop": 327, "geo": "부산광역시", "zone": "영남권", "metro": True},
    "대구": {"stn": "143", "stn_name": "대구", "lat": 35.88, "lon": 128.65, "pop": 236, "geo": "대구광역시", "zone": "영남권", "metro": True},
    "인천": {"stn": "112", "stn_name": "인천", "lat": 37.48, "lon": 126.62, "pop": 302, "geo": "인천광역시", "zone": "수도권", "metro": True},
    "광주": {"stn": "156", "stn_name": "광주", "lat": 35.17, "lon": 126.89, "pop": 141, "geo": "광주광역시", "zone": "호남권", "metro": True},
    "대전": {"stn": "133", "stn_name": "대전", "lat": 36.37, "lon": 127.37, "pop": 144, "geo": "대전광역시", "zone": "충청권", "metro": True},
    "울산": {"stn": "152", "stn_name": "울산", "lat": 35.58, "lon": 129.33, "pop": 110, "geo": "울산광역시", "zone": "영남권", "metro": True},
    "세종": {"stn": "239", "stn_name": "세종", "lat": 36.49, "lon": 127.24, "pop": 39, "geo": "세종특별자치시", "zone": "충청권", "metro": True},
    "경기": {"stn": "119", "stn_name": "수원", "lat": 37.26, "lon": 126.98, "pop": 1370, "geo": "경기도", "zone": "수도권", "metro": False},
    "강원": {"stn": "101", "stn_name": "춘천", "lat": 37.90, "lon": 127.74, "pop": 152, "geo": "강원도", "zone": "강원 · 제주", "metro": False},
    "충북": {"stn": "131", "stn_name": "청주", "lat": 36.64, "lon": 127.44, "pop": 159, "geo": "충청북도", "zone": "충청권", "metro": False},
    "충남": {"stn": "177", "stn_name": "홍성", "lat": 36.66, "lon": 126.69, "pop": 214, "geo": "충청남도", "zone": "충청권", "metro": False},
    "전북": {"stn": "146", "stn_name": "전주", "lat": 35.84, "lon": 127.12, "pop": 174, "geo": "전라북도", "zone": "호남권", "metro": False},
    "전남": {"stn": "165", "stn_name": "목포", "lat": 34.82, "lon": 126.38, "pop": 179, "geo": "전라남도", "zone": "호남권", "metro": False},
    "경북": {"stn": "136", "stn_name": "안동", "lat": 36.57, "lon": 128.71, "pop": 253, "geo": "경상북도", "zone": "영남권", "metro": False},
    "경남": {"stn": "155", "stn_name": "창원", "lat": 35.17, "lon": 128.57, "pop": 322, "geo": "경상남도", "zone": "영남권", "metro": False},
    "제주": {"stn": "184", "stn_name": "제주", "lat": 33.51, "lon": 126.53, "pop": 67, "geo": "제주특별자치도", "zone": "강원 · 제주", "metro": False},
}
