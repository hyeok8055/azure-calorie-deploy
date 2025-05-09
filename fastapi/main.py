import logging
import sys
import os
import random
import re
from typing import List, Dict, Optional, Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
import requests
from bs4 import BeautifulSoup
import json

# 로그 디렉토리 생성
os.makedirs("/app/logs", exist_ok=True)

# 로그 설정
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
logging.basicConfig(
    level=logging.DEBUG,
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler("/app/logs/server.log", mode="a", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 운영 환경에서는 도메인 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 다양한 User-Agent 리스트
USER_AGENTS = [
    # Android
    'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36',
    'Mozilla/5.0 (Linux; Android 13; SM-S908B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36', # Samsung Galaxy S22 Ultra
    'Mozilla/5.0 (Linux; Android 13; Pixel 7 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36', # Google Pixel 7 Pro
    'Mozilla/5.0 (Linux; Android 12; moto g pure) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36', # Motorola Moto G Pure
    'Mozilla/5.0 (Linux; Android 12; Redmi Note 9 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36', # Xiaomi Redmi Note 9 Pro
    'Mozilla/5.0 (Linux; Android 10; VOG-L29) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36', # Huawei P30 Pro
    'Opera/9.80 (Android; Opera Mini/7.6.35766/35.5706; U; en) Presto/2.8.119 Version/11.10', # Opera Mini on Android
    'Mozilla/5.0 (Linux; Android 13; SM-A536B) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/21.0 Chrome/110.0.5481.154 Mobile Safari/537.36', # Samsung Browser on Android

    # iPhone
    'Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/602.1.50 (KHTML, like Gecko) Version/10.0 Mobile/19A346 Safari/602.1', # iPhone 13 Pro Max
    'Mozilla/5.0 (iPhone; CPU iPhone OS 12_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/12.0 Mobile/15E148 Safari/604.1', # iPhone XR
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/99.0.4844.47 Mobile/15E148 Safari/604.1', # Chrome on iPhone
    'Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) FxiOS/114.1 Mobile/15E148 Safari/605.1.15', # Firefox on iPhone

    # Windows Phone
    'Mozilla/5.0 (Windows Phone 10.0; Android 6.0.1; Microsoft; RM-1152) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Mobile Safari/537.36 Edge/15.15254', # Microsoft Lumia 650
    'Mozilla/5.0 (compatible; MSIE 9.0; Windows Phone OS 7.5; Trident/5.0; IEMobile/9.0)' # IE Mobile on Windows Phone
]

@app.get("/search", response_class=HTMLResponse)
async def search_food(keyword: str = Query(..., description="검색할 음식 키워드")):
    logger.info(f"HTML 검색 요청: {keyword}")

    if not keyword:
        logger.warning("빈 키워드 HTML 요청 발생")
        raise HTTPException(status_code=400, detail="키워드를 입력해주세요.")

    url = f"https://mobile.fatsecret.kr/칼로리-영양소/search?q={keyword}"
    headers = {'User-Agent': random.choice(USER_AGENTS)}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        # Return the raw HTML content
        return HTMLResponse(content=response.text, status_code=200)
    except requests.exceptions.RequestException as e:
        logger.error(f"요청 오류 (HTML): {e}")
        raise HTTPException(status_code=500, detail=f"데이터를 가져오는 중 오류 발생: {e}")

@app.get("/food_info")
async def food_info(keyword: str = Query(..., description="검색할 음식 키워드")):
    logger.info(f"음식 정보 검색 요청: {keyword}")

    if not keyword:
        logger.warning("빈 키워드 음식 정보 요청 발생")
        raise HTTPException(status_code=400, detail="키워드를 입력해주세요.")

    food_data = []
    page = 0

    # 최대 2 페이지까지만 조회하여 최대 20개 항목 제한
    while len(food_data) < 20 and page < 2:
        page_url = f"https://mobile.fatsecret.kr/칼로리-영양소/search?q={keyword}"
        if page > 0:
            page_url += f"&pg={page}"

        headers = {'User-Agent': random.choice(USER_AGENTS)}

        try:
            response = requests.get(page_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            body = soup.select_one("table.list")

            # 총 검색 결과 수 확인
            summary_element = body.select_one("tr:nth-child(1) > th.page-summary")
            total_count = 0
            if summary_element and '중' in summary_element.text:
                total_count_match = re.search(r'(\d+)중', summary_element.text)
                if total_count_match:
                    total_count = int(total_count_match.group(1))
            
            
            # 음식 항목 추출 (페이징 요소 제외)
            food_elements = body.select("tr:not(.paging)")
            
            # 첫 번째 요소는 요약 정보이므로 제외
            if food_elements and food_elements[0].select_one('th.page-summary'):
                food_elements = food_elements[1:]
                
            logger.info(f"음식 항목 수: {len(food_elements)}")
            
            for item in food_elements:
                # 음식 항목만 처리
                food_cell = item.select_one("td[colspan='3']")
                if not food_cell:
                    continue
                    
                try:
                    # 음식 이름과 브랜드 추출
                    food_name_elem = food_cell.select_one("div.next-link a.inner-link")
                    if not food_name_elem:
                        continue
                        
                    food_name = food_name_elem.get_text(strip=True)
                    brand = ""
                    
                    brand_elem = food_cell.select_one("div.next-link a.brand")
                    if brand_elem:
                        brand = brand_elem.get_text(strip=True).strip('()')
                        
                    # 영양소 정보 추출
                    nutrient_info = food_cell.select_one("div.next-link div.nowrap.small-text")
                    if not nutrient_info:
                        continue
                        
                    nutrient_text = nutrient_info.get_text()
                    
                    # 기준 단위 및 무게 추출
                    serving_match = re.search(r'(\d+\s*\w+당|\d+인분\s*\(\d+[.]?\d*g\)|\d+팩\s*\(\d+[.]?\d*g\)|\d+회\s*\(\d+[.]?\d*g\)|\d+\s*\w+\s*\(\d+[.]?\d*g\))', nutrient_text)
                    serving = serving_match.group(1) if serving_match else ""
                    
                    # 무게 추출 (괄호 안 숫자+g 또는 ml 형태로 있는 경우)
                    weight_match = re.search(r'\((\d+[.]?\d*(?:g|ml))\)', nutrient_text)
                    weight = weight_match.group(1) if weight_match else ""
                    
                    # serving이 ~g당 또는 ~ml당 형식일 경우 weight 설정
                    if not weight and serving:
                        g_per_match = re.search(r'(\d+[.]?\d*(?:g|ml))당', serving)
                        if g_per_match:
                            weight = g_per_match.group(1)
                    
                    # 무게가 없는 경우 serving에서 숫자+ml 패턴 찾기
                    if not weight:
                        ml_match = re.search(r'(\d+[.]?\d*ml)', serving)
                        if ml_match:
                            weight = ml_match.group(1)
                    
                    # 무게가 없는 경우 다른 크기 정보에서 계산
                    if not weight:
                        other_sizes = food_cell.select("div.next-link div.nowrap.small-text")
                        if len(other_sizes) > 1:
                            other_sizes_text = other_sizes[1].get_text()
                            # 100g당 또는 100ml당 칼로리 정보 찾기
                            per_100_match = re.search(r'100\s*(?:g|ml)\s*[-]\s*(\d+[.]?\d*)kcal', other_sizes_text)
                            if per_100_match and '칼로리:' in nutrient_text:
                                per_100_cal = float(per_100_match.group(1))
                                main_cal_match = re.search(r'칼로리:\s*(\d+[.]?\d*)kcal', nutrient_text)
                                if main_cal_match:
                                    main_cal = float(main_cal_match.group(1))
                                    # 중량 계산: (주 칼로리 / 100g당 칼로리) * 100g
                                    calculated_weight = round((main_cal / per_100_cal) * 100)
                                    # 원본 텍스트에서 단위(g 또는 ml) 파악
                                    unit = "g"
                                    if "ml" in nutrient_text or "ml" in other_sizes_text:
                                        unit = "ml"
                                    weight = f"{calculated_weight}{unit}"
                    
                    # 영양소 추출
                    calories_match = re.search(r'칼로리:\s*(\d+[.]?\d*)kcal', nutrient_text)
                    carbs_match = re.search(r'탄수화물:\s*(\d+[.]?\d*)g', nutrient_text)
                    protein_match = re.search(r'단백질:\s*(\d+[.]?\d*)g', nutrient_text)
                    fat_match = re.search(r'지방:\s*(\d+[.]?\d*)g', nutrient_text)
                    
                    calories = calories_match.group(1) if calories_match else ""
                    carbs = carbs_match.group(1) if carbs_match else ""
                    protein = protein_match.group(1) if protein_match else ""
                    fat = fat_match.group(1) if fat_match else ""
                    
                    # weight가 있으면 serving을 인분으로 표준화
                    if weight and (weight.endswith('g') or weight.endswith('ml')):
                        # g당 형식은 무조건 1인분으로 처리
                        if "g당" in serving or "ml당" in serving:
                            serving = "1인분"
                        else:
                            # 다른 단위는 숫자 부분만 추출하여 인분으로 변환
                            serving_num_match = re.search(r'^(\d+)', serving)
                            serving_num = serving_num_match.group(1) if serving_num_match else "1"
                            serving = f"{serving_num}인분"
                    
                    food_info = {
                        "name": food_name,
                        "brand": brand if brand else None,
                        "serving": serving,
                        "weight": weight,
                        "calories": calories,
                        "carbs": carbs,
                        "protein": protein,
                        "fat": fat
                    }
                    
                    # 일단 모든 데이터 수집 (weight 유무 상관없이)
                    food_data.append(food_info)
                    
                    # 최대 20개만 수집
                    if len(food_data) >= 20:
                        break
                except Exception as e:
                    logger.warning(f"항목 파싱 오류: {e}")
                    continue
            
            # 현재 페이지에서 10개가 안 나오면 더 이상 조회하지 않음
            if len(food_elements) < 10:
                break
                
            # 총 개수가 10개 이하면 더 이상 조회하지 않음
            if total_count <= 10:
                break
                
            page += 1
            
        except requests.exceptions.RequestException as e:
            logger.error(f"요청 오류 (음식 정보): {e}")
            raise HTTPException(status_code=500, detail=f"데이터를 가져오는 중 오류 발생: {e}")
    
    # weight가 있는 항목만 필터링
    filtered_data = [item for item in food_data if item["weight"]]
    if not filtered_data:
        logger.warning(f"중량 정보가 있는 항목이 없음: {keyword}")
    
    logger.info(f"음식 정보 검색 결과: 총 {len(food_data)}개 항목 중 {len(filtered_data)}개 반환")
    return JSONResponse(content={"items": filtered_data, "count": len(filtered_data)})

@app.get("/ping")
async def ping():
    logger.info("ping 요청 수신")
    return {"message": "pong"}
