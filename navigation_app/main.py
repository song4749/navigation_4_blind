from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import requests
from pyproj import Transformer
import json
import os
import math
import uuid
from typing import List, Dict, Any, Optional

# FastAPI 앱 초기화ㅜ
app = FastAPI(title="실시간 보행자 네비게이션")

# 정적 파일 및 템플릿 설정
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# API 키 설정
APP_KEY = 'zLgji89bB19xrdLEokv2e1nXzfXK9haz6i6s6ASE'

# 웹소켓 연결 관리
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

manager = ConnectionManager()

# 데이터 모델
class RouteRequest(BaseModel):
    start_lat: float
    start_lng: float
    end_lat: float
    end_lng: float

# 보행자 경로 계산 함수
def get_pedestrian_route(start_point, end_point):
    """
    보행자 경로 계산
    start_point: (위도, 경도) 형태의 출발지 좌표
    end_point: (위도, 경도) 형태의 도착지 좌표
    """
    url = f'https://apis.openapi.sk.com/tmap/routes/pedestrian?version=1&format=json'
    
    request_data = {
        'startX': start_point[1],  # 경도
        'startY': start_point[0],  # 위도
        'endX': end_point[1],      # 경도
        'endY': end_point[0],      # 위도
        'reqCoordType': 'WGS84GEO',
        'resCoordType': 'EPSG3857',
        'startName': '출발지',
        'endName': '도착지'
    }
    
    headers = {
        'appKey': APP_KEY
    }
    
    response = requests.post(url, json=request_data, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"API 요청 실패: {response.status_code}")
        return None

# EPSG:3857에서 WGS84(EPSG:4326)로 좌표 변환 함수 - 순서 보장
def convert_coordinates(x, y):
    transformer = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)
    lon, lat = transformer.transform(x, y)  # 순서 변경: x,y는 lon,lat 순서로 변환됨
    return lat, lon  # 위도, 경도 순서로 반환

# 하버사인 공식을 사용한 두 지점 간 거리 계산 (미터 단위)
def haversine_distance(point1, point2):
    """
    하버사인 공식으로 두 지점 간 거리 계산 (미터 단위)
    point1, point2: (위도, 경도) 형태의 좌표
    """
    lat1, lon1 = point1
    lat2, lon2 = point2
    
    # 라디안으로 변환
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # 하버사인 공식
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371000  # 지구 반경 (미터)
    
    return c * r

# 초를 hh:mm:ss 형식으로 변환하는 함수
def format_time(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

# 가장 가까운 경로 포인트와 다음 방향 안내 찾기
def find_navigation_guidance(current_location, route_coordinates, guidance_list):
    """
    현재 위치에 맞는 경로 안내 정보 찾기
    current_location: (위도, 경도) 형태의 현재 위치
    route_coordinates: 경로 좌표 목록
    guidance_list: 경로 안내 정보 목록
    """
    if not route_coordinates:
        return None, None, None
    
    # 가장 가까운 경로 포인트 찾기 - 하버사인 공식 사용
    min_distance = float('inf')
    nearest_idx = 0
    
    for i, coord in enumerate(route_coordinates):
        distance = haversine_distance(current_location, coord)
        if distance < min_distance:
            min_distance = distance
            nearest_idx = i
    
    # 사용자가 경로에서 너무 벗어난 경우 경고
    route_deviation_warning = None
    if min_distance > 50:  # 50m 이상 떨어진 경우
        route_deviation_warning = f"경로에서 {int(min_distance)}m 벗어났습니다. 경로로 돌아가세요."
    
    # 남은 거리 계산 - 하버사인 공식 사용
    remaining_distance = 0
    for i in range(nearest_idx, len(route_coordinates) - 1):
        distance = haversine_distance(route_coordinates[i], route_coordinates[i + 1])
        remaining_distance += distance
    
    # 이동 방향 계산 (다음 10개 포인트 확인)
    look_ahead = min(nearest_idx + 10, len(route_coordinates) - 1)
    if look_ahead > nearest_idx:
        curr_lat, curr_lon = current_location
        next_lat, next_lon = route_coordinates[look_ahead]
        
        # 방향 계산 (라디안)
        # 베어링 계산식 수정
        y = math.sin(math.radians(next_lon - curr_lon)) * math.cos(math.radians(next_lat))
        x = math.cos(math.radians(curr_lat)) * math.sin(math.radians(next_lat)) - \
            math.sin(math.radians(curr_lat)) * math.cos(math.radians(next_lat)) * \
            math.cos(math.radians(next_lon - curr_lon))
        bearing = math.atan2(y, x)
        
        # 라디안에서 도로 변환하고 정규화 (0-360)
        bearing = (math.degrees(bearing) + 360) % 360
        
        # 방향 변환 (북=0, 동=90, 남=180, 서=270)
        direction = ""
        if bearing > 337.5 or bearing <= 22.5:
            direction = "북쪽으로"
        elif bearing > 22.5 and bearing <= 67.5:
            direction = "북동쪽으로"
        elif bearing > 67.5 and bearing <= 112.5:
            direction = "동쪽으로"
        elif bearing > 112.5 and bearing <= 157.5:
            direction = "남동쪽으로"
        elif bearing > 157.5 and bearing <= 202.5:
            direction = "남쪽으로"
        elif bearing > 202.5 and bearing <= 247.5:
            direction = "남서쪽으로"
        elif bearing > 247.5 and bearing <= 292.5:
            direction = "서쪽으로"
        elif bearing > 292.5 and bearing <= 337.5:
            direction = "북서쪽으로"
    else:
        direction = "도착 지점 근처"
    
    # 가까운 안내 지점 찾기
    next_guidance = None
    min_guidance_distance = float('inf')
    
    for guidance in guidance_list:
        if 'distance' in guidance and guidance['distance'] > 0:
            distance_from_guidance = abs(guidance['distance'] - remaining_distance)
            if distance_from_guidance < min_guidance_distance and remaining_distance >= guidance['distance'] - 100:
                min_guidance_distance = distance_from_guidance
                next_guidance = guidance
    
    return int(remaining_distance), direction, next_guidance, route_deviation_warning

# 경로 세션 저장을 위한 데이터 구조
route_sessions = {}

# 루트 설정
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "api_key": APP_KEY})

# 장소 검색 함수 (POI 검색) 추가
def search_location(keyword, lat=None, lng=None, radius=5000):
    """
    키워드로 장소 검색 (POI 검색)
    keyword: 검색할 장소명 또는 주소
    lat, lng: 중심 위치 좌표 (선택적)
    radius: 검색 반경 (미터 단위)
    returns: 검색 결과 목록
    """
    url = f'https://apis.openapi.sk.com/tmap/pois?version=1&format=json'
    
    params = {
        'searchKeyword': keyword,
        'count': 10,
        'appKey': APP_KEY
    }
    
    # 위치 정보가 있으면 중심점 및 반경 추가
    if lat is not None and lng is not None:
        params.update({
            'centerLat': lat,
            'centerLon': lng,
            'radius': radius
        })
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"POI 검색 API 요청 실패: {response.status_code}")
        return None

# 장소 검색 API 엔드포인트 추가
@app.get("/api/search")
async def search_places(keyword: str, lat: float = None, lng: float = None, radius: int = 5000):
    print(f"검색 키워드: {keyword}, 위치: {lat}, {lng}, 반경: {radius}m")
    
    # 위치 정보가 있는 경우 함께 전달
    result = search_location(keyword, lat, lng, radius)
    
    if not result or 'searchPoiInfo' not in result:
        return {"error": "검색 결과가 없습니다."}
    
    # 검색 결과 처리 및 반환
    places = []
    if 'pois' in result['searchPoiInfo'] and 'poi' in result['searchPoiInfo']['pois']:
        for poi in result['searchPoiInfo']['pois']['poi']:
            places.append({
                'name': poi.get('name', ''),
                'address': poi.get('upperAddrName', '') + ' ' + poi.get('middleAddrName', '') + ' ' + poi.get('lowerAddrName', '') + ' ' + poi.get('detailAddrName', ''),
                'lat': float(poi.get('frontLat', 0)),
                'lng': float(poi.get('frontLon', 0))
            })
    
    return {"places": places}

# 장소 검색 API 엔드포인트 추가
@app.get("/api/search")
async def search_places(keyword: str):
    print(f"검색 키워드: {keyword}")
    result = search_location(keyword)
    
    if not result or 'searchPoiInfo' not in result:
        print(f"검색 결과 없음: {result}")
        return {"error": "검색 결과가 없습니다."}
    
    # 검색 결과 처리 및 반환
    places = []
    if 'pois' in result['searchPoiInfo'] and 'poi' in result['searchPoiInfo']['pois']:
        for poi in result['searchPoiInfo']['pois']['poi']:
            places.append({
                'name': poi.get('name', ''),
                'address': poi.get('upperAddrName', '') + ' ' + poi.get('middleAddrName', '') + ' ' + poi.get('lowerAddrName', '') + ' ' + poi.get('detailAddrName', ''),
                'lat': float(poi.get('frontLat', 0)),
                'lng': float(poi.get('frontLon', 0))
            })
    
    print(f"검색 결과 {len(places)}개 반환")
    return {"places": places}

# 경로 계산 API - 세션 저장 기능 추가
@app.post("/api/get_route")
async def calculate_route(route_req: RouteRequest):
    # 경로 계산
    route_data = get_pedestrian_route(
        (route_req.start_lat, route_req.start_lng), 
        (route_req.end_lat, route_req.end_lng)
    )
    
    if not route_data:
        return {"error": "경로를 찾을 수 없습니다."}
    
    # 경로 좌표 추출 및 변환
    coordinates = []
    for feature in route_data['features']:
        if feature['geometry']['type'] == 'LineString':
            for coord in feature['geometry']['coordinates']:
                lat, lon = convert_coordinates(coord[0], coord[1])
                coordinates.append([lat, lon])
    
    # 경로 정보
    total_distance = route_data['features'][0]['properties']['totalDistance']
    total_time = route_data['features'][0]['properties']['totalTime']
    time_formatted = format_time(total_time)
    
    # 안내 정보 추출
    guidance = []
    for feature in route_data['features']:
        if 'properties' in feature and 'description' in feature['properties']:
            if feature['properties']['description']:
                guidance.append({
                    'description': feature['properties']['description'],
                    'distance': feature['properties'].get('distance', 0)
                })
    
    # 세션 ID 생성 및 저장
    session_id = f"route_{uuid.uuid4().hex}"
    route_sessions[session_id] = {
        'coordinates': coordinates,
        'guidance': guidance,
        'total_distance': total_distance,
        'total_time': time_formatted
    }
    
    return {
        'session_id': session_id,
        'coordinates': coordinates,
        'total_distance': total_distance,
        'total_time': time_formatted,
        'guidance': guidance
    }

# 웹소켓 연결 - 실시간 경로 안내 추가
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    session_id = None
    
    try:
        while True:
            data = await websocket.receive_text()
            location_data = json.loads(data)
            
            # 세션 ID가 없으면 새로 생성
            if 'session_id' in location_data:
                session_id = location_data['session_id']
            
            # 세션이 존재하고 경로 정보가 있다면 실시간 안내 제공
            if session_id and session_id in route_sessions:
                session = route_sessions[session_id]
                current_location = (location_data["latitude"], location_data["longitude"])
                
                # 현재 위치에 맞는 안내 정보 찾기
                remaining_distance, direction, next_guidance, deviation_warning = find_navigation_guidance(
                    current_location, 
                    session['coordinates'], 
                    session['guidance']
                )
                
                # 다음 안내 메시지 구성
                next_direction = "계속 진행하세요."
                voice_guidance = ""
                
                # 경로 이탈 경고가 있다면 우선 처리
                if deviation_warning:
                    next_direction = deviation_warning
                    voice_guidance = deviation_warning
                elif next_guidance and 'description' in next_guidance:
                    distance_to_turn = min(100, remaining_distance - next_guidance['distance'])
                    if distance_to_turn < 30:  # 30m 이내면 턴 안내
                        next_direction = next_guidance['description']
                        voice_guidance = next_guidance['description']
                    elif distance_to_turn < 100:  # 100m 이내면 사전 알림
                        meters = int(distance_to_turn)
                        next_direction = f"{meters}m 앞에서 {next_guidance['description']}"
                        if meters <= 50:  # 50m 이내일 때만 음성 안내
                            voice_guidance = f"{meters}미터 앞에서 {next_guidance['description']}"
                elif direction:
                    next_direction = f"{direction} 계속 진행하세요."
                
                # 응답 데이터
                response_data = {
                    "status": "위치 업데이트 완료",
                    "latitude": location_data["latitude"],
                    "longitude": location_data["longitude"],
                    "remaining_distance": remaining_distance,
                    "next_direction": next_direction,
                    "voice_guidance": voice_guidance,  # 음성 안내용 텍스트
                    "off_route": True if deviation_warning else False
                }
                
                await manager.send_personal_message(json.dumps(response_data), websocket)
            else:
                # 단순 위치 업데이트만 응답
                await manager.send_personal_message(
                    json.dumps({
                        "status": "위치 업데이트 완료", 
                        "latitude": location_data["latitude"], 
                        "longitude": location_data["longitude"]
                    }),
                    websocket
                )
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        # 세션 정리 (선택적)
        if session_id and session_id in route_sessions:
            route_sessions.pop(session_id)

# 앱 실행
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
