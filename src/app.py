import streamlit as st
import pandas as pd
import requests
import os
from dotenv import load_dotenv
import streamlit.components.v1 as components

# 페이지 설정
st.set_page_config(page_title="서울 관광지 검색 서비스", layout="wide")

# .env 파일 로드
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path)

KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY")
KAKAO_JS_API_KEY = os.getenv("KAKAO_JS_API_KEY")

@st.cache_data
def load_main_data():
    project_root = os.path.join(os.path.dirname(__file__), '..')
    file_path = os.path.join(project_root, 'data1', 'new_total_seoul_tour.csv')
    try:
        df = pd.read_csv(file_path)
        return df
    except Exception as e:
        st.error(f"데이터를 불러오는데 실패했습니다: {e}")
        return pd.DataFrame()


@st.cache_data
def get_coords(query):
    """카카오 로컬 API를 사용하여 위도/경도 반환"""
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}
    params = {"query": query}
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        if data['documents']:
            return float(data['documents'][0]['y']), float(data['documents'][0]['x'])
    except:
        pass
    return None, None

@st.cache_data
def get_default_map_data(df):
    """자치구별 상위 3개 관광지 추출 및 지오코딩"""
    top3_df = df.sort_values(['시/군/구', '검색건수'], ascending=[True, False]).groupby('시/군/구').head(3).reset_index(drop=True)
    
    map_data = []
    for _, row in top3_df.iterrows():
        query = f"서울 {row['시/군/구']} {row['관광지명']}"
        lat, lng = get_coords(query)
        if lat:
            map_data.append({
                'name': row['관광지명'],
                'category': row['소분류 카테고리'],
                'district': row['시/군/구'],
                'lat': lat,
                'lng': lng
            })
    return top3_df, map_data

def render_kakao_map(locations, height=700, level=8, show_my_location=False):
    """카카오 맵과 관광지 목록을 통합하여 렌더링"""
    if not locations:
        return st.info("지도에 표시할 데이터가 없습니다.")

    markers_js = ""
    list_items_html = ""
    valid_locs = [l for l in locations if l['lat'] and l['lng']]
    
    for i, loc in enumerate(valid_locs):
        markers_js += f"""
            {{
                title: '{loc['name']}', 
                latlng: new kakao.maps.LatLng({loc['lat']}, {loc['lng']}),
                category: '{loc.get('category', '')}',
                district: '{loc.get('district', '')}'
            }},"""
        
        list_items_html += f"""
            <div class="list-item" onclick="focusMarker({i})" id="item-{i}">
                <div class="item-name">{loc['name']}</div>
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
        var RED_MARKER_IMG = new kakao.maps.MarkerImage(
            'https://t1.daumcdn.net/localimg/localimages/07/mapapidoc/marker_red.png',
            new kakao.maps.Size(31, 35),
            {{offset: new kakao.maps.Point(13, 34)}}
        );

        function initMap() {{
            var mapContainer = document.getElementById('map');
            var loadingMsg = document.getElementById('loading-msg');
            if (loadingMsg) loadingMsg.style.display = 'none';

            var mapOption = {{ center: new kakao.maps.LatLng(37.5665, 126.9780), level: {level} }};
            map = new kakao.maps.Map(mapContainer, mapOption); 
            var positions = [{markers_js}];

            for (var i = 0; i < positions.length; i ++) {{
                var marker = new kakao.maps.Marker({{
                    map: map, position: positions[i].latlng, title : positions[i].title
                }});
                var content = '<div style="padding:10px;min-width:150px;font-size:12px;">' + 
                              '<strong>' + positions[i].title + '</strong><br>' + 
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
                    map.setLevel(4);
                }});
            }}
        }}

        function focusMarker(idx) {{
            for (var i = 0; i < markers.length; i++) {{
                markers[i].setImage(null);
                infowindows[i].close();
                document.getElementById('item-' + i).classList.remove('active');
            }}
            var targetMarker = markers[idx];
            targetMarker.setImage(RED_MARKER_IMG);
            infowindows[idx].open(map, targetMarker);
            map.panTo(targetMarker.getPosition());
            map.setLevel(4);
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
    st.markdown("자치구별 인기 명소와 카테고리별 검색 결과를 확인하세요.")

    df = load_main_data()

    # 1. 상위 검색 필터 (중분류 카테고리)
    categories = sorted(df['중분류 카테고리'].unique()) if not df.empty else []
    selected_categories = st.multiselect("📂 중분류 카테고리 선택 (미선택 시 자치구별 상위 3개 표시)", categories)

    # 데이터 준비
    is_filtered = len(selected_categories) > 0
    display_df = pd.DataFrame()
    map_data = []

    if is_filtered:
        # 필터링된 데이터 (new_total_seoul_tour.csv 기준 상위 30건)
        filtered_df = df[df['중분류 카테고리'].isin(selected_categories)].sort_values('검색건수', ascending=False).head(30)
        display_df = filtered_df
        
        with st.spinner("위치 정보를 수집 중입니다..."):
            for _, row in display_df.iterrows():
                query = f"서울 {row['시/군/구']} {row['관광지명']}"
                lat, lng = get_coords(query)
                if lat:
                    map_data.append({
                        'name': row['관광지명'],
                        'category': row['소분류 카테고리'],
                        'district': row['시/군/구'],
                        'lat': lat,
                        'lng': lng
                    })
    else:
        # 기본값: 자치구별 상위 3개 (new_total_seoul_tour.csv 활용)
        with st.spinner("자치구별 인기 명소를 불러오는 중입니다..."):
            display_df, map_data = get_default_map_data(df)

    # 지도 및 목록 통합 UI
    st.subheader("📍 서울 관광지 지도 (목록 연동)")
    
    # 내 위치 표시 토글
    show_my_loc = st.checkbox("📍 내 위치 표시 및 이동", value=False)
    
    # 통합 지도 렌더링 (목록 포함)
    render_kakao_map(map_data, height=700, show_my_location=show_my_loc)

if __name__ == "__main__":
    main()

