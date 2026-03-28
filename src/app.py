import streamlit as st
import pandas as pd
import requests
import os
from dotenv import load_dotenv
import streamlit.components.v1 as components
import xml.etree.ElementTree as ET

# 페이지 설정
st.set_page_config(page_title="서울 관광지 검색 서비스", layout="wide")

# .env 파일 로드
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path)

# KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY") # 더 이상 사용하지 않음
KAKAO_JS_API_KEY = os.getenv("KAKAO_JS_API_KEY")
SEOUL_CITY_DATA_API_KEY = os.getenv("SEOUL_CITY_DATA_API_KEY")

@st.cache_data
def load_main_data():
    project_root = os.path.join(os.path.dirname(__file__), '..')
    file_path = os.path.join(project_root, 'data1', 'last_tour_enriched.csv')
    try:
        df = pd.read_csv(file_path)
        return df
    except Exception as e:
        st.error(f"데이터를 불러오는데 실패했습니다: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=600)  # 10분마다 캐시 갱신
def get_seoul_city_data(location_id):
    """서울시 실시간 도시 데이터 API 호출 (AREA_CD 또는 AREA_NM 사용)"""
    if not SEOUL_CITY_DATA_API_KEY:
        return {"error": "API KEY가 설정되지 않았습니다."}
    
    # 공백 제거 및 인코딩
    location_id = location_id.strip()
    url = f"http://openapi.seoul.go.kr:8088/{SEOUL_CITY_DATA_API_KEY}/xml/citydata/1/5/{location_id}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        # XML 파싱
        root = ET.fromstring(response.content)
        
        # 결과 코드 확인
        result = root.find(".//RESULT/CODE")
        if result is not None and result.text != "INFO-000":
            msg = root.find(".//RESULT/MESSAGE")
            return {"error": msg.text if msg is not None else "Unknown error"}
            
        # 데이터 추출
        stts = root.find(".//LIVE_PPLTN_STTS/LIVE_PPLTN_STTS")
        if stts is not None:
            data = {
                "area_cd": root.findtext(".//AREA_CD"),
                "area_nm": root.findtext(".//AREA_NM"),
                "congestion_lvl": stts.findtext("AREA_CONGEST_LVL"),
                "congestion_msg": stts.findtext("AREA_CONGEST_MSG"),
                "update_time": stts.findtext("PPLTN_TIME")
            }
            return data
    except Exception as e:
        return {"error": str(e)}
    
    return {"error": "데이터를 찾을 수 없습니다."}


@st.cache_data
def load_area_master():
    """122개 주요 장소 목록 로드"""
    project_root = os.path.join(os.path.dirname(__file__), '..')
    file_path = os.path.join(project_root, 'data1', 'area_master.csv')
    try:
        df = pd.read_csv(file_path)
        return df
    except:
        return pd.DataFrame()

def get_default_map_data(df):
    """자치구별 상위 3개 관광지 추출 (CSV 내 lat/lng 활용)"""
    top3_df = df.sort_values(['시/군/구', '검색건수'], ascending=[True, False]).groupby('시/군/구').head(3).reset_index(drop=True)
    
    map_data = []
    for _, row in top3_df.iterrows():
        lat, lng = row.get('lat'), row.get('lng')
        if pd.notnull(lat) and pd.notnull(lng):
            map_data.append({
                'name': row['관광지명'],
                'category': row['소분류 카테고리'],
                'district': row['시/군/구'],
                'lat': lat,
                'lng': lng,
                'area_cd': row.get('area_cd', '')
            })
    return top3_df, map_data


def get_area_nm_by_cd(area_cd):
    """AREA_CD를 기반으로 AREA_NM 조회"""
    if not area_cd:
        return None
    area_df = load_area_master()
    if not area_df.empty:
        match = area_df[area_df['AREA_CD'] == area_cd]
        if not match.empty:
            return match.iloc[0]['AREA_NM']
    return None

def render_kakao_map(locations, height=700, level=8, show_my_location=False, center_lat=None, center_lng=None):
    """카카오 맵과 관광지 목록을 통합하여 렌더링"""
    if not locations:
        return st.info("지도에 표시할 데이터가 없습니다.")

    markers_js = ""
    list_items_html = ""
    valid_locs = [l for l in locations if l['lat'] and l['lng']]
    
    for i, loc in enumerate(valid_locs):
        cong_lvl = loc.get('congestion_lvl', '정보없음')
        markers_js += f"""
            {{
                title: '{loc['name']}', 
                latlng: new kakao.maps.LatLng({loc['lat']}, {loc['lng']}),
                category: '{loc.get('category', '')}',
                district: '{loc.get('district', '')}',
                congestion: '{cong_lvl}'
            }},"""
        
        # 리스트에 혼잡도 뱃지 추가
        cong_colors = {"여유": "#2ecc71", "보통": "#f1c40f", "약간 붐빔": "#e67e22", "붐빔": "#e74c3c", "정보없음": "#95a5a6"}
        badge_color = cong_colors.get(cong_lvl, "#95a5a6")
        
        list_items_html += f"""
            <div class="list-item" onclick="focusMarker({i})" id="item-{i}">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div class="item-name">{loc['name']}</div>
                    <span style="font-size: 10px; padding: 2px 6px; background: {badge_color}; color: white; border-radius: 10px;">{cong_lvl}</span>
                </div>
                <div class="item-info">[{loc.get('district', '')}] {loc.get('category', '')}</div>
            </div>"""

    html_code = f"""
    <head>
        <meta http-equiv="Content-Security-Policy" content="upgrade-insecure-requests">
        <style>
            .container {{ display: flex; width: 100%; height: {height}px; font-family: 'Pretendard', sans-serif; border: 1px solid #eee; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            #sidebar {{ width: 300px; height: 100%; overflow-y: auto; background: #fff; border-right: 1px solid #eee; }}
            #map {{ flex: 1; height: 100%; }}
            .sidebar-header {{ padding: 15px; background: #f8f9fa; border-bottom: 2px solid #eee; font-weight: bold; position: sticky; top: 0; z-index: 10; }}
            .list-item {{ padding: 12px 15px; border-bottom: 1px solid #f0f0f0; cursor: pointer; transition: background 0.2s; }}
            .list-item:hover {{ background: #f1f3f5; }}
            .list-item.active {{ background: #e7f5ff; border-left: 4px solid #228be6; }}
            .item-name {{ font-size: 14px; font-weight: 600; color: #333; }}
            .item-info {{ font-size: 12px; color: #868e96; margin-top: 4px; }}
            #loading-msg {{ text-align: center; padding-top: {height//2-10}px; color: #666; }}
            ::-webkit-scrollbar {{ width: 6px; }}
            ::-webkit-scrollbar-thumb {{ background: #dee2e6; border-radius: 3px; }}
        </style>
    </head>
    <div class="container">
        <div id="sidebar">
            <div class="sidebar-header">📋 관광지 목록 ({len(valid_locs)}곳)</div>
            {list_items_html}
        </div>
        <div id="map">
            <div id="loading-msg">지도를 불러오는 중...</div>
        </div>
    </div>
    
    <script type="text/javascript" src="https://dapi.kakao.com/v2/maps/sdk.js?appkey={KAKAO_JS_API_KEY}&autoload=false"></script>
    <script>
        var map, markers = [], infowindows = [];
        
        // 상태별 마커 이미지 설정
        var ICON_URLS = {{
            '여유': 'http://maps.google.com/mapfiles/ms/icons/green-dot.png',
            '보통': 'http://maps.google.com/mapfiles/ms/icons/yellow-dot.png',
            '약간 붐빔': 'http://maps.google.com/mapfiles/ms/icons/orange-dot.png',
            '붐빔': 'http://maps.google.com/mapfiles/ms/icons/red-dot.png',
            '정보없음': 'http://maps.google.com/mapfiles/ms/icons/blue-dot.png'
        }};

        function initMap() {{
            var mapContainer = document.getElementById('map');
            var loadingMsg = document.getElementById('loading-msg');
            if (loadingMsg) loadingMsg.style.display = 'none';

            var centerLat = {center_lat if center_lat else 37.5665};
            var centerLng = {center_lng if center_lng else 126.9780};
            var mapLevel = {2 if center_lat else level};

            var mapOption = {{ center: new kakao.maps.LatLng(centerLat, centerLng), level: mapLevel }};
            map = new kakao.maps.Map(mapContainer, mapOption); 
            var positions = [{markers_js}];

            for (var i = 0; i < positions.length; i ++) {{
                var markerImg = new kakao.maps.MarkerImage(
                    ICON_URLS[positions[i].congestion] || ICON_URLS['정보없음'],
                    new kakao.maps.Size(32, 32)
                );

                var marker = new kakao.maps.Marker({{
                    map: map, 
                    position: positions[i].latlng, 
                    title : positions[i].title,
                    image: markerImg
                }});
                
                var congColor = (positions[i].congestion === '붐빔') ? 'red' : ((positions[i].congestion === '여유') ? 'green' : 'orange');
                var content = '<div style="padding:10px;min-width:150px;font-size:12px;">' + 
                              '<strong>' + positions[i].title + '</strong><br>' + 
                              '<span style="color:' + congColor + ';font-weight:bold;">실시간: ' + positions[i].congestion + '</span><br>' +
                              (positions[i].district ? '<span>[' + positions[i].district + '] </span>' : '') +
                              '<span>' + positions[i].category + '</span>' +
                              '</div>';
                var infowindow = new kakao.maps.InfoWindow({{ content: content }});
                markers.push(marker);
                infowindows.push(infowindow);

                (function(m, info, idx) {{
                    kakao.maps.event.addListener(m, 'click', function() {{ focusMarker(idx); }});
                    kakao.maps.event.addListener(m, 'mouseover', function() {{ info.open(map, m); }});
                    kakao.maps.event.addListener(m, 'mouseout', function() {{ info.close(); }});
                }})(marker, infowindow, i);
            }}

            if (positions.length > 0) {{
                var bounds = new kakao.maps.LatLngBounds();
                for (var i = 0; i < positions.length; i++) {{ bounds.extend(positions[i].latlng); }}
                map.setBounds(bounds);
            }}

            var showMyLocation = "{'true' if show_my_location else 'false'}";
            if (showMyLocation === 'true' && navigator.geolocation) {{
                navigator.geolocation.getCurrentPosition(function(position) {{
                    var lat = position.coords.latitude, lon = position.coords.longitude;
                    var locPosition = new kakao.maps.LatLng(lat, lon);
                    var starImg = new kakao.maps.MarkerImage('https://t1.daumcdn.net/localimg/localimages/07/mapapidoc/markerStar.png', new kakao.maps.Size(24, 35));
                    new kakao.maps.Marker({{ map: map, position: locPosition, image: starImg, title: '내 위치' }});
                    map.setCenter(locPosition);
                    map.setLevel(2);
                }});
            }}
        }}

        function focusMarker(idx) {{
            for (var i = 0; i < markers.length; i++) {{
                infowindows[i].close();
                document.getElementById('item-' + i).classList.remove('active');
            }}
            var targetMarker = markers[idx];
            infowindows[idx].open(map, targetMarker);
            map.panTo(targetMarker.getPosition());
            map.setLevel(2);
            var item = document.getElementById('item-' + idx);
            item.classList.add('active');
            item.scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});
        }}

        if (typeof kakao !== 'undefined') {{ kakao.maps.load(initMap); }}
        else {{ document.getElementById('loading-msg').innerHTML = '<h4 style="color:red;">지도 SDK 로드 실패</h4>'; }}
    </script>
    """
    components.html(html_code, height=height + 20)

def main():
    st.title("🏙️ 서울 관광지 맞춤형 추천 서비스")
    
    df = load_main_data()
    if df.empty:
        return

    # 1. 사이드바 필터링 대시보드
    st.sidebar.header("🔍 검색 필터")
    
    # 중분류 카테고리
    categories = sorted(df['중분류 카테고리'].unique())
    selected_categories = st.sidebar.multiselect("📂 중분류 선택", categories)
    
    # 소분류 카테고리 (중분류에 종속)
    sub_categories = []
    if selected_categories:
        sub_categories = sorted(df[df['중분류 카테고리'].isin(selected_categories)]['소분류 카테고리'].unique())
    else:
        sub_categories = sorted(df['소분류 카테고리'].unique())
    selected_subcategories = st.sidebar.multiselect("🏷️ 소분류 선택", sub_categories)

    # 데이터 필터링 로직
    display_df = df.copy()
    if selected_categories:
        display_df = display_df[display_df['중분류 카테고리'].isin(selected_categories)]
    if selected_subcategories:
        display_df = display_df[display_df['소분류 카테고리'].isin(selected_subcategories)]
    
    # 상위 30건 제한 (성능 및 시각화 최적화)
    display_df = display_df.sort_values('검색건수', ascending=False).head(30)
    
    # 2. 사이드바 - 관광지 선택 및 실시간 데이터
    st.sidebar.markdown("---")
    st.sidebar.header("📍 상세 정보 및 실시간 현황")
    
    selected_attraction = None
    center_lat, center_lng = None, None
    map_data = []

    if not display_df.empty:
        attraction_names = display_df['관광지명'].tolist()
        selected_attraction = st.sidebar.selectbox("🎯 관광지 선택", ["선택 안 함"] + attraction_names)
        
        # 선택된 관광지 정보 추출
        if selected_attraction != "선택 안 함":
            target_row = display_df[display_df['관광지명'] == selected_attraction].iloc[0]
            center_lat = target_row['lat']
            center_lng = target_row['lng']
            target_cd = target_row.get('area_cd')
            
            # 실시간 데이터 표시
            if target_cd:
                with st.sidebar:
                    with st.spinner(f"'{selected_attraction}' 현황 조회 중..."):
                        city_data = get_seoul_city_data(target_cd)
                        if "error" in city_data:
                            st.error(city_data["error"])
                        else:
                            color_map = {"여유": "#2ecc71", "보통": "#f1c40f", "약간 붐빔": "#e67e22", "붐빔": "#e74c3c"}
                            color = color_map.get(city_data['congestion_lvl'], "#bdc3c7")
                            st.markdown(f"""
                                <div style="padding: 15px; border-radius: 10px; border-left: 5px solid {color}; background-color: #f8f9fa; margin-bottom: 20px;">
                                    <h4 style="margin-top:0; color:#2c3e50; font-size: 1.1em;">{selected_attraction} 주변</h4>
                                    <div style="font-size: 1.2em; font-weight: bold; color: {color}; margin-bottom: 5px;">{city_data['congestion_lvl']}</div>
                                    <p style="font-size: 0.85em; color: #555; line-height: 1.5; margin-bottom: 0;">{city_data['congestion_msg']}</p>
                                </div>
                            """, unsafe_allow_html=True)
            else:
                st.sidebar.warning("실시간 데이터가 지원되지 않는 지역입니다.")

    # 3. 지도 데이터 준비 및 실시간 정보 일괄 매핑
    unique_cds = display_df['area_cd'].dropna().unique().tolist()
    realtime_status = {}
    if unique_cds:
        for cd in unique_cds:
            data = get_seoul_city_data(cd)
            if "congestion_lvl" in data:
                realtime_status[cd] = data["congestion_lvl"]

    for _, row in display_df.iterrows():
        if pd.notnull(row['lat']) and pd.notnull(row['lng']):
            cd = row.get('area_cd')
            map_data.append({
                'name': row['관광지명'],
                'category': row['소분류 카테고리'],
                'district': row['시/군/구'],
                'lat': row['lat'],
                'lng': row['lng'],
                'congestion_lvl': realtime_status.get(cd, '정보없음')
            })

    # 4. 지도 인터페이스 시각화
    st.subheader("📍 서울 관광지 지도 (목록 연동)")
    show_my_loc = st.checkbox("📍 내 위치 표시", value=False)
    
    render_kakao_map(
        map_data, 
        height=700, 
        show_my_location=show_my_loc,
        center_lat=center_lat,
        center_lng=center_lng
    )

if __name__ == "__main__":
    main()

