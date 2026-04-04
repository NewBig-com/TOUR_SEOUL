import pandas as pd
import requests
import os
import re
import unicodedata
from urllib.parse import urlparse, parse_qs

# 경로 설정
DATA_DIR = './data'
IMG_DIR = './images'
OY_IMG_DIR = os.path.join(IMG_DIR, 'oliveyoung_best')
DAISO_IMG_DIR = os.path.join(IMG_DIR, 'daiso_best')

# 폴더 생성
os.makedirs(OY_IMG_DIR, exist_ok=True)
os.makedirs(DAISO_IMG_DIR, exist_ok=True)

def sanitize_filename(filename):
    # 파일명에 사용할 수 없는 문자 제거 및 정규화
    filename = unicodedata.normalize('NFC', str(filename))
    return re.sub(r'[\\/*?:"<>|]', "", filename).strip()

def download_image(url, save_path):
    if os.path.exists(save_path):
        return True
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                f.write(response.content)
            return True
    except Exception as e:
        print(f"Error downloading {url}: {e}")
    return False

def process_daiso():
    print("Processing Daiso images...")
    df = pd.read_csv(os.path.join(DATA_DIR, 'daiso_march_best.csv'))
    for _, row in df.iterrows():
        name = sanitize_filename(row['goods_name'])
        url = row['image_url']
        if pd.isna(url): continue
        save_path = os.path.join(DAISO_IMG_DIR, f"{name}.jpg")
        if download_image(url, save_path):
            print(f"Downloaded: {name}")

def process_oliveyoung():
    print("Processing Olive Young images...")
    df = pd.read_csv(os.path.join(DATA_DIR, 'oliveyoung_best_integrated.csv'))
    for _, row in df.iterrows():
        name = sanitize_filename(row['상품명'])
        product_url = row['url']
        if pd.isna(product_url): continue
        
        # goodsNo 추출
        parsed_url = urlparse(product_url)
        params = parse_qs(parsed_url.query)
        goods_no = params.get('goodsNo', [None])[0]
        
        if not goods_no:
            # URL에서 직접 정규식으로 추출 시도
            match = re.search(r'goodsNo=([A-Z0-9]+)', product_url)
            if match:
                goods_no = match.group(1)
        
        if goods_no:
            # 패턴: https://image.oliveyoung.co.kr/uploads/images/goods/10/0000/00{prefix}/{goodsNo}.jpg
            # prefix는 goodsNo의 8-9번째 숫자 (7,8 인덱스)
            prefix = goods_no[7:9] 
            img_url = f"https://image.oliveyoung.co.kr/uploads/images/goods/10/0000/00{prefix}/{goods_no}.jpg"
            
            save_path = os.path.join(OY_IMG_DIR, f"{name}.jpg")
            if download_image(img_url, save_path):
                print(f"Downloaded OY: {name}")
            else:
                # 패턴 실패 시 대체 시도 (고정 0022 등 혹은 다른 경로)
                print(f"Failed OY: {name} ({img_url})")

if __name__ == "__main__":
    process_daiso()
    process_oliveyoung()
