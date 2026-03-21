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
    # 자치구별 검색건수 상위 3개 추출
    top3_df = df.sort_values(['시/군/구', '검색건수'], ascending=[True, False]).groupby('시/군/구').head(3).reset_index(drop=True)
    
    map_data = []
    for _, row in top3_df.iterrows():
        query = f"서울 {row['시/군/구']} {row['관광지명']}"
        # get_coords는 이미 캐싱되어 있으므로 내부 호출도 효율적임
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

def render_kakao_map(locations, selected_name=None, height=600, level=8, show_my_location=False):
    """카카오 맵 JavaScript API를 사용하여 지도를 렌더링"""
    if not locations:
        return st.info("지도에 표시할 데이터가 없습니다.")

    markers_js = ""
    valid_locs = [l for l in locations if l['lat'] and l['lng']]
    
    # 선택된 장소가 있으면 해당 장소의 좌표를 중심으로 설정
    center_lat, center_lng = 37.5665, 126.9780
    if selected_name:
        for loc in valid_locs:
            if loc['name'] == selected_name:
                center_lat, center_lng = loc['lat'], loc['lng']
                level = 4 # 강조 시 더 가깝게 확대
                break
    elif valid_locs:
        # 기본적으로 첫 번째 마커 기준 (또는 서울 중심 유지 가능)
        pass

    for loc in valid_locs:
        markers_js += f"""
            {{
                title: '{loc['name']}', 
                latlng: new kakao.maps.LatLng({loc['lat']}, {loc['lng']}),
                category: '{loc.get('category', '')}',
                district: '{loc.get('district', '')}'
            }},"""

    html_code = f"""
    <head>
        <meta http-equiv="Content-Security-Policy" content="upgrade-insecure-requests">
    </head>
    <div id="map" style="width:100%;height:{height}px;background-color:#f8f9fa;border:1px solid #ddd;">
        <div id="loading-msg" style="text-align:center;padding-top:{height//2-10}px;color:#666;font-family:sans-serif;">지도를 불러오는 중...</div>
    </div>
    
    <script type="text/javascript" src="https://dapi.kakao.com/v2/maps/sdk.js?appkey={KAKAO_JS_API_KEY}&autoload=false"></script>
    <script>
        function initMap() {{
            var mapContainer = document.getElementById('map');
            var loadingMsg = document.getElementById('loading-msg');
            if (loadingMsg) loadingMsg.style.display = 'none';

            var mapOption = {{ 
                center: new kakao.maps.LatLng({center_lat}, {center_lng}), 
                level: {level}
            }};

            var map = new kakao.maps.Map(mapContainer, mapOption); 
            var positions = [{markers_js}];
            var selectedName = "{selected_name if selected_name else ''}";

            for (var i = 0; i < positions.length; i ++) {{
                var marker = new kakao.maps.Marker({{
                    map: map, 
                    position: positions[i].latlng,
                    title : positions[i].title
                }});
                
                var content = '<div style="padding:10px;min-width:150px;font-size:12px;">' + 
                              '<strong>' + positions[i].title + '</strong><br>' + 
                              (positions[i].district ? '<span>[' + positions[i].district + '] </span>' : '') +
                              '<span>' + positions[i].category + '</span>' +
                              '</div>';

                var infowindow = new kakao.maps.InfoWindow({{
                    content: content
                }});
                
                // 마우스 오버 시 이름 표시 (요청사항 6번)
                kakao.maps.event.addListener(marker, 'mouseover', (function(m, info) {{
                    return function() {{ info.open(map, m); }};
                }})(marker, infowindow));

                kakao.maps.event.addListener(marker, 'mouseout', (function(info) {{
                    return function() {{ info.close(); }};
                }})(infowindow));

                // 클릭 시 고정
                kakao.maps.event.addListener(marker, 'click', (function(m, info) {{
                    return function() {{ info.open(map, m); }};
                }})(marker, infowindow));

                // 선택된 관광지가 있으면 바로 표시
                if (positions[i].title === selectedName) {{
                    infowindow.open(map, marker);
                }}
            }}
            
            // 선택된 항목이 없을 때만 전체 범위 재설정
            if (!selectedName && positions.length > 0) {{
                var bounds = new kakao.maps.LatLngBounds();
                for (var i = 0; i < positions.length; i++) {{
                    bounds.extend(positions[i].latlng);
                }}
                map.setBounds(bounds);
            }}

            // 현재 위치 표시 및 이동 로직
            var showMyLocation = "{'true' if show_my_location else 'false'}";
            if (showMyLocation === 'true' && navigator.geolocation) {{
                navigator.geolocation.getCurrentPosition(function(position) {{
                    var lat = position.coords.latitude,
                        lon = position.coords.longitude;
                    
                    var locPosition = new kakao.maps.LatLng(lat, lon);
                    var message = '<div style="padding:10px;min-width:150px;font-size:12px;text-align:center;">' + 
                                  '<strong>내 현재 위치</strong>' + 
                                  '</div>';
                    
                    var imageSrc = "https://t1.daumcdn.net/localimg/localimages/07/mapapidoc/markerStar.png"; 
                    var imageSize = new kakao.maps.Size(24, 35); 
                    var markerImage = new kakao.maps.MarkerImage(imageSrc, imageSize); 
                    
                    var marker = new kakao.maps.Marker({{
                        map: map,
                        position: locPosition,
                        image: markerImage,
                        title: '내 현재 위치'
                    }});
                    
                    var infowindow = new kakao.maps.InfoWindow({{
                        content: message,
                        removable: true
                    }});
                    
                    kakao.maps.event.addListener(marker, 'click', function() {{
                        infowindow.open(map, marker);
                    }});

                    // 내 위치로 지도 중심 이동
                    map.setCenter(locPosition);
                    map.setLevel(4); // 내 위치 확인 시 확대
                }});
            }}
        }}

        if (typeof kakao !== 'undefined') {{
            kakao.maps.load(initMap);
        }} else {{
            document.getElementById('loading-msg').innerHTML = '<h4 style="color:red;">지도 SDK 로드 실패 (도메인 설정 확인)</h4>';
        }}
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

    # 지도 및 목록 상호작용
    col1, col2 = st.columns([2, 1])

    with col2:
        st.subheader("📋 관광지 목록")
        if not display_df.empty:
            # 관광지 선택 (클릭 효과 대체)
            list_options = ["선택 안 함"] + display_df['관광지명'].tolist()
            selected_spot = st.selectbox("목록에서 관광지를 선택하면 지도가 이동합니다.", list_options)
            
            st.dataframe(display_df[['시/군/구', '관광지명', '검색건수']], use_container_width=True, height=500)
        else:
            selected_spot = "선택 안 함"
            st.info("표시할 데이터가 없습니다.")

    with col1:
        st.subheader("📍 서울 지도")
        # 내 위치 표시 토글 추가
        show_my_loc = st.checkbox("📍 내 위치 표시 및 이동", value=False)
        target_name = selected_spot if selected_spot != "선택 안 함" else None
        render_kakao_map(map_data, selected_name=target_name, height=600, show_my_location=show_my_loc)

if __name__ == "__main__":
    main()
