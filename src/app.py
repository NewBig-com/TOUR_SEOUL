import streamlit as st
import pandas as pd
import requests
import os
import unicodedata
import base64
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
import streamlit.components.v1 as components
# from streamlit_option_menu import option_menu # Removed as no longer used
# from streamlit_geolocation import streamlit_geolocation # Removed as no longer used


# --- 1. Page Configuration & Styling ---
st.set_page_config(page_title="Seoul Beauty & Tour Dashboard", layout="wide", initial_sidebar_state="expanded")

# Load .env
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(BASE_DIR, '..')
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
IMG_DIR = os.path.join(PROJECT_ROOT, 'images')

KAKAO_JS_API_KEY = os.getenv("KAKAO_JS_API_KEY")
SEOUL_CITY_DATA_API_KEY = os.getenv("SEOUL_CITY_DATA_API_KEY")

# --- 2. Data Utilities ---
def inject_custom_css():
    st.markdown("""
        <style>
        @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
        
        html, body, [class*="css"] {
            font-family: 'Pretendard', -apple-system, sans-serif !important;
            background-color: #F8F9FD !important;
            color: #2D3436 !important;
        }
        
        [data-testid="stAppViewContainer"] {
            background-color: #F8F9FD !important;
        }

        .block-container {
            padding: 1.5rem 2.5rem !important;
        }

        /* Glassmorphism containers */
        .glass-card {
            background: rgba(255, 255, 255, 0.6);
            backdrop-filter: blur(15px);
            -webkit-backdrop-filter: blur(15px);
            border: 1px solid rgba(255, 255, 255, 0.4);
            border-radius: 20px;
            padding: 20px;
            box-shadow: 0 8px 32px rgba(31, 38, 135, 0.05);
            margin-bottom: 20px;
        }

        /* Best Label */
        .best-label {
            background: linear-gradient(135deg, #F93780 0%, #FF6B6B 100%);
            color: white;
            padding: 4px 12px;
            border-radius: 30px;
            font-weight: 700;
            font-size: 0.8rem;
            display: inline-block;
            margin-bottom: 10px;
        }

        /* Product Card */
        .product-card {
            background: white;
            border-radius: 15px;
            padding: 12px;
            text-align: center;
            border: 1px solid #EEF1F6;
            transition: all 0.3s ease;
            height: 100%;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            max-width: 160px; /* Consistently small like in the 5-column layout */
            margin: 0 auto;
        }
        .product-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 20px rgba(0,0,0,0.05);
            border-color: #F9378022;
        }
        .product-img {
            width: 100%;
            height: 120px; /* Fixed height to match Home tab feel */
            object-fit: contain;
            border-radius: 10px;
            margin-bottom: 10px;
            background-color: #f9f9f9;
        }
        .product-title {
            font-size: 0.8rem; /* Slightly smaller for consistent grid */
            font-weight: 600;
            color: #333;
            height: 2.8em;
            overflow: hidden;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            line-height: 1.4;
        }
        .product-brand {
            font-size: 0.7rem;
            color: #888;
            margin-bottom: 4px;
        }
        .product-price {
            font-size: 0.9rem;
            color: #F93780;
            font-weight: 700;
            margin-top: 5px;
        }

        /* Rankings Table */
        .ranking-row {
            display: flex;
            align-items: center;
            padding: 12px 15px;
            background: white;
            border-radius: 12px;
            margin-bottom: 8px;
            border: 1px solid #EEF1F6;
        }
        .rank-num {
            width: 30px;
            font-weight: 800;
            color: #F93780;
            font-size: 1.1rem;
        }

        /* Custom Tabs Styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 24px;
            background-color: transparent;
        }
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            white-space: pre-wrap;
            border-radius: 10px 10px 0 0;
            font-weight: 700;
            font-size: 1.1rem;
            color: #636E72;
        }
        .stTabs [aria-selected="true"] {
            color: #F93780 !important;
            border-bottom-color: #F93780 !important;
        }
        .badge-여유 { background: #00B894; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: 700; margin-left: 5px; }
        .badge-보통 { background: #6C5CE7; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: 700; margin-left: 5px; }
        .badge-약간붐빔 { background: #E17055; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: 700; margin-left: 5px; }
        .badge-붐빔 { background: #D63031; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: 700; margin-left: 5px; }
        .badge-정보없음 { background: #B2BEC3; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: 700; margin-left: 5px; }
        </style>
    """, unsafe_allow_html=True)

def safe_read_csv(path, **kwargs):
    try:
        return pd.read_csv(path, encoding='utf-8', **kwargs)
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding='cp949', **kwargs)
    except Exception as e:
        return pd.DataFrame()

@st.cache_data
def load_data(filename):
    path = os.path.join(DATA_DIR, filename)
    return safe_read_csv(path)

def get_base64_img(path):
    if not path or not os.path.exists(path): return None
    with open(path, 'rb') as f:
        return base64.b64encode(f.read()).decode()

def find_image_path(product_name, brand):
    folder = 'oliveyoung_best' if brand == 'oliveyoung' else 'daiso_best'
    target_dir = os.path.join(IMG_DIR, folder)
    if not os.path.exists(target_dir): return None
    name_norm = unicodedata.normalize('NFC', str(product_name).strip()).replace(' ', '')
    for f in os.listdir(target_dir):
        if name_norm in unicodedata.normalize('NFC', f).replace(' ', ''):
            return os.path.join(target_dir, f)
    return None

# --- 3. City Data API ---
@st.cache_data(ttl=600)
def get_congestion_data(location_id):
    if not location_id or not SEOUL_CITY_DATA_API_KEY: return {"lvl": "정보없음", "color": "#B2BEC3"}
    url = f"http://openapi.seoul.go.kr:8088/{SEOUL_CITY_DATA_API_KEY}/xml/citydata/1/5/{location_id}"
    try:
        res = requests.get(url)
        root = ET.fromstring(res.content)
        stts = root.find(".//LIVE_PPLTN_STTS/LIVE_PPLTN_STTS")
        if stts is not None:
            lvl = stts.findtext("AREA_CONGEST_LVL")
            colors = {"여유": "#00B894", "보통": "#6C5CE7", "약간 붐빔": "#E17055", "붐빔": "#D63031"}
            return {"lvl": lvl, "color": colors.get(lvl, "#B2BEC3")}
    except: pass
    return {"lvl": "정보없음", "color": "#B2BEC3"}

# --- 4. Map Rendering ---
def render_map(locations, stores=None, center=(37.5665, 126.9780), zoom=7, height=450):
    marker_js = ""
    for loc in locations:
        lvl_tag = f"[{loc.get('lvl', '정보없음')}]" if 'lvl' in loc else ""
        marker_js += f"{{lat:{loc['lat']},lng:{loc['lng']},title:'{loc['name']} {lvl_tag}',type:'tour'}},"
    
    if stores:
        for s in stores:
            marker_js += f"{{lat:{s['위도']},lng:{s['경도']},title:'{s['매장명']}',type:'{s['메이커명'].lower()}'}},"

    html = f"""
    <div id="map" style="width:100%; height:{height}px; border-radius:15px;"></div>
    <script type="text/javascript" src="https://dapi.kakao.com/v2/maps/sdk.js?appkey={KAKAO_JS_API_KEY}"></script>
    <script>
        window.onload = function() {{
            var container = document.getElementById('map');
            var options = {{
                center: new kakao.maps.LatLng({center[0]}, {center[1]}),
                level: {zoom}
            }};
            var map = new kakao.maps.Map(container, options);
            var icons = {{
                tour: 'http://maps.google.com/mapfiles/ms/icons/green-dot.png',
                oliveyoung: 'http://maps.google.com/mapfiles/ms/icons/blue-dot.png',
                daiso: 'http://maps.google.com/mapfiles/ms/icons/red-dot.png'
            }};
            var positions = [{marker_js}];
            positions.forEach(function(p) {{
                var marker = new kakao.maps.Marker({{
                    map: map, position: new kakao.maps.LatLng(p.lat, p.lng),
                    image: new kakao.maps.MarkerImage(icons[p.type] || icons.tour, new kakao.maps.Size(32, 32))
                }});
                var iw = new kakao.maps.InfoWindow({{ content: '<div style="padding:5px;font-size:12px;">'+p.title+'</div>' }});
                kakao.maps.event.addListener(marker, 'mouseover', function() {{ iw.open(map, marker); }});
                kakao.maps.event.addListener(marker, 'mouseout', function() {{ iw.close(); }});
            }});
        }};
    </script>
    """
    components.html(html, height=height)

# --- 5. Main UI ---
def main():
    inject_custom_css()
    
    # Load Data
    df_oy = load_data('oliveyoung_best_integrated.csv')
    df_daiso = load_data('daiso_march_best.csv')
    df_tour = load_data('last_tour_enriched.csv')
    df_stores = load_data('seoul_cosmetic.csv')

    # Session State
    if 'oy_more' not in st.session_state: st.session_state.oy_more = False
    if 'daiso_more' not in st.session_state: st.session_state.daiso_more = False

    t_home, t_cosmo, t_tour = st.tabs(["🏠 HOME", "💄 COSMETICS", "📍 TOURIST"])

    # --- HOME TAB ---
    with t_home:
        # Filter Menus
        f1, f2 = st.columns(2)
        with f1:
            oy_cats = df_oy['카테고리 이름'].unique() if not df_oy.empty else []
            sel_cos_cat = st.selectbox("💄 Favorite Cosmetic Category", ["All"] + list(oy_cats))
        with f2:
            tour_cats = df_tour['중분류 카테고리'].unique() if not df_tour.empty else []
            sel_tour_cat = st.selectbox("🏙️ Favorite Attraction Category", ["All"] + list(tour_cats))

        # Best 5 (OY vs Daiso)
        st.markdown("<h3 style='margin-bottom:20px;'>🔥 Brand Best 5</h3>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        
        brand_params = [
            ('oliveyoung', df_oy, '상품명', '할인 가격', c1),
            ('daiso', df_daiso, 'goods_name', 'price', c2)
        ]
        
        for brand, df, name_col, price_col, col in brand_params:
            with col:
                st.markdown(f"<div class='glass-card'><h4>{brand.upper()} Bestsellers</h4>", unsafe_allow_html=True)
                if sel_cos_cat != "All":
                    cat_col = '카테고리 이름' if brand == 'oliveyoung' else 'category'
                    df_filtered = df[df[cat_col].str.contains(sel_cos_cat, na=False)]
                else: 
                    df_filtered = df
                
                best_5 = df_filtered.head(5)
                sub_cols = st.columns(5)
                for i, (_, row) in enumerate(best_5.iterrows()):
                    with sub_cols[i]:
                        name = row[name_col]
                        price = int(row[price_col])
                        img_path = find_image_path(name, brand)
                        img_tag = f'<img src="data:image/jpeg;base64,{get_base64_img(img_path)}" class="product-img">' if img_path else '<div class="product-img" style="background:#eee; line-height:100px; font-size:10px;">No Image</div>'
                        st.markdown(f"""
                            <div class="product-card">
                                {img_tag}
                                <div class="product-title">{name}</div>
                                <div class="product-price">{price:,}원</div>
                            </div>
                        """, unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

        # Tourist Top 10 + Map
        st.markdown("<h3 style='margin-top:40px;'>📍 Tourist Best 10 & Map</h3>", unsafe_allow_html=True)
        gc = st.container()
        with gc:
            l_col, r_col = st.columns([1, 2])
            with l_col:
                tour_filtered = df_tour.copy()
                if sel_tour_cat != "All":
                    tour_filtered = tour_filtered[tour_filtered['중분류 카테고리'] == sel_tour_cat]
                top_10 = tour_filtered.head(10)
                for i, (_, row) in enumerate(top_10.iterrows()):
                    congest = get_congestion_data(row.get('area_cd'))
                    cls = congest['lvl'].replace(" ", "")
                    st.markdown(f"""
                    <div class="ranking-row">
                        <div class="rank-num">{i+1}</div>
                        <div style="flex:1;">
                            <div style="font-weight:700; font-size:0.9rem;">
                                {row['관광지명']} 
                                <span class="badge-{cls}">{congest['lvl']}</span>
                            </div>
                            <div style="font-size:0.75rem; color:#888;">{row['시/군/구']} | {row['소분류 카테고리']}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            with r_col:
                map_locs = []
                for _, r in top_10.iterrows():
                    congest = get_congestion_data(r.get('area_cd'))
                    map_locs.append({'lat': r['lat'], 'lng': r['lng'], 'name': r['관광지명'], 'lvl': congest['lvl']})
                render_map(map_locs, height=500)

    # --- COSMETICS TAB ---
    with t_cosmo:
        st.markdown("<h2 style='text-align:center;'>💄 K-Beauty Trend Search</h2>", unsafe_allow_html=True)
        
        # Summary Area
        bc1, bc2 = st.columns(2)
        
        brand_info = [
            ('oliveyoung', df_oy, bc1),
            ('daiso', df_daiso, bc2)
        ]
        
        for brand, df, bcol in brand_info:
            with bcol:
                st.markdown(f"### {brand.upper()} March Best 100")
                name_col = '상품명' if brand == 'oliveyoung' else 'goods_name'
                price_col = '할인 가격' if brand == 'oliveyoung' else 'price'
                
                show_full = st.session_state.get(f'{brand}_more', False)
                count = 100 if show_full else 3
                
                items = df.head(count)
                # Adjusted to 3 columns for half-width layout
                grid_cols = st.columns(3) 
                for i, (_, row) in enumerate(items.iterrows()):
                    with grid_cols[i % 3]:
                        name = row[name_col]
                        price = int(row[price_col])
                        img_path = find_image_path(name, brand)
                        img_tag = f'<img src="data:image/jpeg;base64,{get_base64_img(img_path)}" class="product-img">' if img_path else '<div class="product-img" style="line-height:120px;">No Image</div>'
                        st.markdown(f"""
                            <div class="product-card" style="margin-bottom:15px;">
                                <div class="best-label" style="font-size:0.6rem; padding:2px 8px;">TOP {i+1}</div>
                                {img_tag}
                                <div class="product-title" style="font-size:0.7rem;">{name}</div>
                                <div class="product-price" style="font-size:0.8rem;">{price:,}원</div>
                            </div>
                        """, unsafe_allow_html=True)
                
                # View More Toggle
                if not show_full:
                    if st.button(f"View All {brand.upper()} List", key=f"btn_{brand}"):
                        st.session_state[f'{brand}_more'] = True
                        st.rerun()
                else:
                    if st.button("Hide Full List", key=f"hide_{brand}"):
                        st.session_state[f'{brand}_more'] = False
                        st.rerun()


        # Ranking Comparison
        st.markdown("---")
        st.markdown("### 📊 Real-time Ranking Comparison")
        
        if not df_oy.empty and not df_daiso.empty:
            rc1, rc2 = st.columns(2)
            with rc1:
                st.markdown("<div class='glass-card'><h4>Olive Young Top 10</h4>", unsafe_allow_html=True)
                for i, row in df_oy.head(10).iterrows():
                    st.markdown(f"""
                    <div class="ranking-row">
                        <div class="rank-num">{i+1}</div>
                        <div style="flex:1;">
                            <div style="font-weight:700; font-size:0.85rem;">{row['상품명']}</div>
                            <div style="font-size:0.7rem; color:#888;">{row['브랜드 이름']} | {int(row['할인 가격']):,}원</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
            
            with rc2:
                st.markdown("<div class='glass-card'><h4>Daiso Top 10</h4>", unsafe_allow_html=True)
                for i, row in df_daiso.head(10).iterrows():
                    st.markdown(f"""
                    <div class="ranking-row">
                        <div class="rank-num">{i+1}</div>
                        <div style="flex:1;">
                            <div style="font-weight:700; font-size:0.85rem;">{row['goods_name']}</div>
                            <div style="font-size:0.7rem; color:#888;">{row['brand_name']} | {int(row['price']):,}원</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)


    # --- TOURIST TAB ---
    with t_tour:
        st.markdown("## 🏙️ Seoul Tourist Insights")
        
        # District Filter & Map
        col_f1, col_f2 = st.columns([1, 2.5])
        with col_f1:
            st.markdown("#### 🔍 Search by District")
            gu_list = sorted(df_tour['시/군/구'].unique().tolist())
            sel_gu = st.selectbox("Select District", ["All"] + gu_list)
            
            cat_list = sorted(df_tour['중분류 카테고리'].unique().tolist())
            sel_cat = st.multiselect("Category Filter", cat_list)
            
            st.markdown("---")
            st.markdown(f"#### 🏆 {sel_gu if sel_gu != 'All' else 'Seoul All'} Top 5 Attractions")
            gu_data = df_tour.copy()
            if sel_gu != "All": gu_data = gu_data[gu_data['시/군/구'] == sel_gu]
            if sel_cat: gu_data = gu_data[gu_data['중분류 카테고리'].isin(sel_cat)]
            
            top_5_gu = gu_data.head(5)
            for i, (_, row) in enumerate(top_5_gu.iterrows()):
                congest = get_congestion_data(row.get('area_cd'))
                cls = congest['lvl'].replace(" ", "")
                st.markdown(f"""
                <div class="ranking-row">
                    <div class="rank-num">{i+1}</div>
                    <div style="flex:1;">
                        <div style="font-weight:700; font-size:0.85rem;">
                            {row['관광지명']}
                            <span class="badge-{cls}">{congest['lvl']}</span>
                        </div>
                        <div style="font-size:0.7rem; color:#888;">{row['소분류 카테고리']}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        with col_f2:
            st.markdown("#### 🗺️ Unified Interactive Map (Stores & Attractions)")
            map_stores = df_stores.to_dict('records')
            map_tour_items = []
            for _, r in gu_data.head(50).iterrows():
                congest = get_congestion_data(r.get('area_cd'))
                map_tour_items.append({'lat': r['lat'], 'lng': r['lng'], 'name': r['관광지명'], 'lvl': congest['lvl']})
            render_map(map_tour_items, stores=map_stores, height=600, zoom=7)

if __name__ == "__main__":
    main()



