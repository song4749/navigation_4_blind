document.addEventListener('DOMContentLoaded', function() {
    // DOM 요소
    const statusElement = document.getElementById('status');
    const destinationInput = document.getElementById('destination');
    const searchButton = document.getElementById('search');
    const startNavigationButton = document.getElementById('start-navigation');
    const stopNavigationButton = document.getElementById('stop-navigation');
    const destinationForm = document.getElementById('destination-form');
    const navigationInfo = document.getElementById('navigation-info');
    const distanceElement = document.getElementById('distance');
    const timeElement = document.getElementById('time');
    const nextDirectionElement = document.getElementById('next-direction');
    const searchResultsDiv = document.getElementById('search-results');

    // 글로벌 변수 추가
    let sessionId = null;
    let lastVoiceGuidance = '';
    let speechSynthesis = window.speechSynthesis;
    let compassHeading = null;
    let voiceEnabled = true;
    let isLocationManuallySet = false;

    // 지도 초기화
    const map = L.map('map').setView([37.5665, 126.9780], 15);  // 서울 시청 기준
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    // 마커 및 경로 레이어
    let currentPositionMarker = null;
    let destinationMarker = null;
    let routeLayer = null;
    let routeCoordinates = [];
    let watchId = null;
    let isNavigating = false;
    let socket = null;

    // 현재 위치 마커 스타일
    const currentPositionIcon = L.divIcon({
        className: 'current-position-icon',
        html: '<div style="background-color: #4285F4; border-radius: 50%; width: 15px; height: 15px; border: 3px solid white;"></div>',
        iconSize: [15, 15],
        iconAnchor: [7.5, 7.5]
    });

    // 목적지 마커 스타일
    const destinationIcon = L.icon({
        iconUrl: 'https://unpkg.com/leaflet@1.9.3/dist/images/marker-icon-2x-red.png',
        shadowUrl: 'https://unpkg.com/leaflet@1.9.3/dist/images/marker-shadow.png',
        iconSize: [25, 41],
        iconAnchor: [12, 41],
        popupAnchor: [1, -34],
        shadowSize: [41, 41]
    });

    // 위치 정확도 표시 UI 추가
    const accuracyInfoDiv = document.createElement('div');
    accuracyInfoDiv.id = 'accuracy-info';
    accuracyInfoDiv.style.position = 'absolute';
    accuracyInfoDiv.style.bottom = '10px';
    accuracyInfoDiv.style.left = '10px';
    accuracyInfoDiv.style.backgroundColor = 'rgba(255,255,255,0.8)';
    accuracyInfoDiv.style.padding = '5px';
    accuracyInfoDiv.style.borderRadius = '5px';
    accuracyInfoDiv.style.zIndex = '1000';
    accuracyInfoDiv.style.fontSize = '12px';
    accuracyInfoDiv.textContent = '위치 정확도: 확인 중...';
    document.body.appendChild(accuracyInfoDiv);

    // 수동 위치 설정 버튼 추가
    const setLocationButton = document.createElement('button');
    setLocationButton.id = 'set-location';
    setLocationButton.textContent = '현재 위치 수동 설정';
    setLocationButton.style.position = 'absolute';
    setLocationButton.style.bottom = '40px';
    setLocationButton.style.left = '10px';
    setLocationButton.style.zIndex = '1000';
    setLocationButton.style.padding = '8px';
    setLocationButton.style.backgroundColor = '#ff7043';
    setLocationButton.style.color = 'white';
    setLocationButton.style.border = 'none';
    setLocationButton.style.borderRadius = '4px';
    setLocationButton.style.display = 'none'; // 초기에는 숨김
    document.body.appendChild(setLocationButton);

    // 음성 안내 함수 추가
    function speakText(text) {
        if (!voiceEnabled || !text || text === lastVoiceGuidance) return;
        
        // 이전 음성 취소
        speechSynthesis.cancel();
        
        // 새 음성 안내 생성
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = 'ko-KR';  // 한국어
        utterance.volume = 1.0;    // 최대 볼륨
        utterance.rate = 1.0;      // 정상 속도
        utterance.pitch = 1.0;     // 정상 음높이
        
        // 음성 재생
        speechSynthesis.speak(utterance);
        lastVoiceGuidance = text;
    }

    // 나침반 초기화 함수 추가
    function initializeCompass() {
        if (window.DeviceOrientationEvent) {
            // iOS 13+ 요구사항
            if (typeof DeviceOrientationEvent.requestPermission === 'function') {
                document.getElementById('enable-compass').style.display = 'block';
                document.getElementById('enable-compass').addEventListener('click', function() {
                    DeviceOrientationEvent.requestPermission()
                        .then(permissionState => {
                            if (permissionState === 'granted') {
                                window.addEventListener('deviceorientation', handleOrientation);
                                this.style.display = 'none';
                            }
                        })
                        .catch(console.error);
                });
            } else {
                // 기타 기기
                window.addEventListener('deviceorientation', handleOrientation);
            }
        }
    }

    // 방향 처리 함수
    function handleOrientation(event) {
        // iOS와 안드로이드에서 방위각 값이 다르게 제공됨
        if (event.webkitCompassHeading) {
            // iOS
            compassHeading = event.webkitCompassHeading;
        } else if (event.alpha) {
            // 안드로이드
            compassHeading = 360 - event.alpha;
        }
        
        // 나침반 화살표 업데이트
        updateDirectionArrow();
    }

    // 방향 화살표 업데이트
    function updateDirectionArrow() {
        const arrow = document.getElementById('direction-arrow');
        if (arrow && compassHeading !== null) {
            arrow.style.transform = `rotate(${compassHeading}deg)`;
        }
    }

    // 웹소켓 연결 설정
    function setupWebSocket() {
        // 현재 호스트 기반으로 웹소켓 URL 구성
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${wsProtocol}//${window.location.host}/ws`;
        
        socket = new WebSocket(wsUrl);
        
        socket.onopen = function(e) {
            console.log("웹소켓 연결 설정");
        };
        
        socket.onmessage = function(event) {
            const data = JSON.parse(event.data);
            console.log("서버로부터 데이터 수신:", data);
            
            // 서버로부터 받은 데이터 처리
            if (data.status) {
                statusElement.textContent = data.status;
            }
            
            // 네비게이션 정보 업데이트
            if (data.next_direction) {
                nextDirectionElement.textContent = data.next_direction;
            }
            
            if (data.remaining_distance) {
                distanceElement.textContent = `${data.remaining_distance}m`;
            }
            
            // 음성 안내 처리
            if (data.voice_guidance && data.voice_guidance !== '') {
                speakText(data.voice_guidance);
            }
            
            // 경로 이탈 경고 처리
            if (data.off_route) {
                // 경로 이탈 시 버튼 표시
                setLocationButton.style.display = 'block';
            } else {
                // 경로 내에 있을 때는 숨김 
                if (!isLocationManuallySet) {
                    setLocationButton.style.display = 'none';
                }
            }
        };
        
        socket.onclose = function(event) {
            console.log("웹소켓 연결 종료");
            // 자동 재연결 시도
            setTimeout(setupWebSocket, 1000);
        };
        
        socket.onerror = function(error) {
            console.log("웹소켓 오류:", error);
        };
    }

    // 현재 위치 가져오기
    function getCurrentPosition() {
        return new Promise((resolve, reject) => {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(resolve, reject, {
                    enableHighAccuracy: true,
                    timeout: 10000,  // 타임아웃 증가
                    maximumAge: 0
                });
            } else {
                reject(new Error('Geolocation is not supported by this browser.'));
            }
        });
    }

    // 현재 위치 업데이트 및 표시
    async function updateCurrentPosition() {
        try {
            const position = await getCurrentPosition();
            const { latitude, longitude, accuracy } = position.coords;
            
            // 정확도 정보 표시
            accuracyInfoDiv.textContent = `위치 정확도: ${Math.round(accuracy)}m`;
            
            // 정확도가 너무 낮은 경우 경고
            if (accuracy > 100) {
                statusElement.innerHTML = `위치 정확도가 낮습니다(${Math.round(accuracy)}m). 수동 위치 설정을 사용해보세요.`;
                setLocationButton.style.display = 'block';
            } else {
                if (!isLocationManuallySet) {
                    setLocationButton.style.display = 'none';
                }
            }
            
            if (!currentPositionMarker) {
                currentPositionMarker = L.marker([latitude, longitude], { icon: currentPositionIcon }).addTo(map);
                map.setView([latitude, longitude], 17);
            } else {
                currentPositionMarker.setLatLng([latitude, longitude]);
            }
            
            statusElement.innerHTML = '현재 위치를 확인했습니다.';
            
            // 웹소켓이 열려 있고 네비게이션 중이라면 서버에 위치 업데이트 전송
            if (socket && socket.readyState === WebSocket.OPEN && isNavigating) {
                socket.send(JSON.stringify({
                    latitude: latitude,
                    longitude: longitude,
                    accuracy: accuracy,
                    session_id: sessionId
                }));
            }
            
            return { latitude, longitude, accuracy };
        } catch (error) {
            console.error('위치 정보를 가져오는 데 실패했습니다:', error);
            statusElement.innerHTML = '위치 정보를 가져오는 데 실패했습니다. 수동 위치 설정을 사용해보세요.';
            setLocationButton.style.display = 'block';
            throw error;
        }
    }

    // 위치 실시간 추적 시작 - 개선된 버전
    function startTracking() {
        if (watchId) return;
        
        // 위치 정확도 필터링을 위한 변수
        let positionHistory = [];
        const MAX_HISTORY = 3; // 평균을 계산할 위치 기록 수
        const MAX_ACCURACY = 25; // 최대 허용 정확도 (미터) - 낮을수록 정확함
        
        // 수동 위치 설정 버튼 표시
        setLocationButton.style.display = 'block';
        
        watchId = navigator.geolocation.watchPosition(
            function(position) {
                const { latitude, longitude, accuracy } = position.coords;
                
                // 수동으로 위치를 설정한 경우 무시
                if (isLocationManuallySet) return;
                
                // 정확도 및 위치 정보 로깅 (디버깅용)
                console.log(`현재 위치: ${latitude}, ${longitude}, 정확도: ${accuracy}m`);
                
                // 정확도 정보 표시
                accuracyInfoDiv.textContent = `위치 정확도: ${Math.round(accuracy)}m`;
                
                // 정확도가 너무 낮은 경우 수동 위치 설정 버튼 표시
                if (accuracy > 100) { // 100m 이상 정확도는 경고
                    statusElement.innerHTML = `위치 정확도가 낮습니다(${Math.round(accuracy)}m). 수동 위치 설정을 사용해보세요.`;
                    setLocationButton.style.display = 'block';
                    
                    // 너무 부정확한 경우(200m 이상)는 위치 업데이트 건너뛰기
                    if (accuracy > 200 && positionHistory.length > 0) {
                        return;
                    }
                } else {
                    setLocationButton.style.display = 'none';
                }
                
                // 위치 히스토리 추가
                positionHistory.push({latitude, longitude, accuracy});
                if (positionHistory.length > MAX_HISTORY) {
                    positionHistory.shift(); // 가장 오래된 위치 제거
                }
                
                // 가중 평균 계산 (정확도가 높은 위치에 더 큰 가중치 부여)
                let weightedLat = 0, weightedLng = 0, totalWeight = 0;
                
                positionHistory.forEach(pos => {
                    // 정확도의 역수를 가중치로 사용 (정확도가 높을수록 가중치 증가)
                    const weight = 1 / Math.max(1, pos.accuracy);
                    weightedLat += pos.latitude * weight;
                    weightedLng += pos.longitude * weight;
                    totalWeight += weight;
                });
                
                // 최종 보정된 위치
                const filteredLat = totalWeight > 0 ? weightedLat / totalWeight : latitude;
                const filteredLng = totalWeight > 0 ? weightedLng / totalWeight : longitude;
                
                // 위치 마커 업데이트
                if (currentPositionMarker) {
                    currentPositionMarker.setLatLng([filteredLat, filteredLng]);
                } else {
                    currentPositionMarker = L.marker([filteredLat, filteredLng], { icon: currentPositionIcon }).addTo(map);
                }
                
                // 네비게이션 중인 경우 지도 중심 이동
                if (isNavigating) {
                    map.panTo([filteredLat, filteredLng]);
                }
                
                // 웹소켓으로 위치 업데이트 전송
                if (socket && socket.readyState === WebSocket.OPEN && isNavigating) {
                    socket.send(JSON.stringify({
                        latitude: filteredLat,
                        longitude: filteredLng,
                        raw_latitude: latitude,
                        raw_longitude: longitude,
                        accuracy: accuracy,
                        session_id: sessionId,
                        filtered: true
                    }));
                }
            },
            function(error) {
                console.error("위치 추적 오류:", error);
                switch (error.code) {
                    case error.PERMISSION_DENIED:
                        statusElement.innerHTML = "위치 권한이 거부되었습니다. 브라우저 설정에서 위치 권한을 허용해주세요.";
                        break;
                    case error.POSITION_UNAVAILABLE:
                        statusElement.innerHTML = "위치 정보를 사용할 수 없습니다. GPS 신호가 약한 지역일 수 있습니다.";
                        break;
                    case error.TIMEOUT:
                        statusElement.innerHTML = "위치 정보 요청 시간이 초과되었습니다.";
                        break;
                    default:
                        statusElement.innerHTML = `위치 추적 오류: ${error.message}`;
                }
                
                // 오류 발생 시 수동 위치 설정 활성화
                setLocationButton.style.display = 'block';
            },
            {
                enableHighAccuracy: true, // 고정밀 위치 사용
                maximumAge: 0,            // 캐시된 위치 사용 안 함
                timeout: 10000,           // 10초 타임아웃
                distanceFilter: 2         // 2미터마다 업데이트 (일부 브라우저에서 지원)
            }
        );
    }

    // 위치 추적 중지
    function stopTracking() {
        if (watchId) {
            navigator.geolocation.clearWatch(watchId);
            watchId = null;
        }
        
        // 수동 위치 설정 비활성화
        isLocationManuallySet = false;
        setLocationButton.style.display = 'none';
    }

    // 수동 위치 설정 버튼 이벤트 핸들러
    setLocationButton.addEventListener('click', function() {
        alert("지도를 클릭하여 현재 위치를 수동으로 설정하세요.");
        isLocationManuallySet = true;
        this.textContent = "수동 위치 설정 모드";
        this.style.backgroundColor = "#f44336";
        
        // 임시 클릭 이벤트 핸들러 생성
        const manualLocationHandler = function(e) {
            const lat = e.latlng.lat;
            const lng = e.latlng.lng;
            
            // 현재 위치 마커 설정
            if (currentPositionMarker) {
                currentPositionMarker.setLatLng([lat, lng]);
            } else {
                currentPositionMarker = L.marker([lat, lng], { icon: currentPositionIcon }).addTo(map);
            }
            
            // 설정된 위치 정보를 서버에 전송
            if (socket && socket.readyState === WebSocket.OPEN && isNavigating) {
                socket.send(JSON.stringify({
                    latitude: lat,
                    longitude: lng,
                    session_id: sessionId,
                    manually_set: true,
                    accuracy: 5  // 수동 설정 위치는 정확도 높게 설정
                }));
            }
            
            // 상태 업데이트
            statusElement.innerHTML = `현재 위치를 수동으로 설정했습니다: ${lat.toFixed(6)}, ${lng.toFixed(6)}`;
            accuracyInfoDiv.textContent = "위치 정확도: 수동 설정됨";
            
            // 버튼 상태 업데이트
            setLocationButton.textContent = "자동 위치로 돌아가기";
            setLocationButton.style.backgroundColor = "#4CAF50";
            
            // 수동 위치 설정 모드 유지, 클릭 이벤트 제거
            map.off('click', manualLocationHandler);
            
            // 버튼 클릭 핸들러 변경 - 자동 모드로 돌아가기
            setLocationButton.onclick = function() {
                isLocationManuallySet = false;
                setLocationButton.textContent = "현재 위치 수동 설정";
                setLocationButton.style.backgroundColor = "#ff7043";
                setLocationButton.onclick = originalClickHandler;  // 원래 핸들러로 복원
                
                // 자동 위치 업데이트 다시 시작
                updateCurrentPosition();
                statusElement.innerHTML = "자동 위치 추적으로 돌아갑니다.";
                
                if (!isNavigating) {
                    setLocationButton.style.display = 'none';
                }
            };
        };
        
        // 원래 클릭 핸들러 저장
        const originalClickHandler = this.onclick;
        
        // 지도 클릭 이벤트 추가
        map.on('click', manualLocationHandler);
    });

    // 목적지 검색
    searchButton.addEventListener('click', async function() {
        const keyword = destinationInput.value.trim();
        if (!keyword) {
            alert('목적지를 입력하세요.');
            return;
        }
        
        try {
            statusElement.innerHTML = '목적지 검색 중...';
            
            // 좌표 형식인지 먼저 확인 ("위도,경도" 형식)
            if (keyword.includes(',')) {
                const parts = keyword.split(',');
                if (parts.length === 2) {
                    const lat = parseFloat(parts[0].trim());
                    const lng = parseFloat(parts[1].trim());
                    
                    if (!isNaN(lat) && !isNaN(lng)) {
                        // 유효한 좌표이면 바로 마커 설정
                        if (destinationMarker) {
                            destinationMarker.setLatLng([lat, lng]);
                        } else {
                            destinationMarker = L.marker([lat, lng], { icon: destinationIcon }).addTo(map);
                        }
                        
                        // 지도 뷰 조정
                        if (currentPositionMarker) {
                            const bounds = L.latLngBounds([currentPositionMarker.getLatLng(), [lat, lng]]);
                            map.fitBounds(bounds, { padding: [50, 50] });
                        } else {
                            map.setView([lat, lng], 15);
                        }
                        
                        statusElement.innerHTML = '목적지가 설정되었습니다.';
                        startNavigationButton.disabled = false;
                        
                        // 검색 결과 숨기기
                        if (searchResultsDiv) {
                            searchResultsDiv.style.display = 'none';
                        }
                        
                        return;
                    }
                }
            }
            
            // 위치 검색 API 호출
            const response = await fetch(`/api/search?keyword=${encodeURIComponent(keyword)}`);
            const data = await response.json();
            
            if (data.error) {
                alert(data.error);
                return;
            }
            
            if (!searchResultsDiv) {
                // 검색 결과 표시 영역이 없으면 생성
                searchResultsDiv = document.createElement('div');
                searchResultsDiv.id = 'search-results';
                searchResultsDiv.style.display = 'none';
                searchResultsDiv.style.maxHeight = '200px';
                searchResultsDiv.style.overflowY = 'auto';
                searchResultsDiv.style.marginBottom = '10px';
                searchResultsDiv.style.background = 'white';
                searchResultsDiv.style.border = '1px solid #ddd';
                searchResultsDiv.style.borderRadius = '5px';
                searchResultsDiv.style.marginTop = '5px';
                
                // 검색 결과 영역 삽입
                const formGroup = destinationInput.parentElement;
                formGroup.parentElement.insertBefore(searchResultsDiv, formGroup.nextSibling);
            }
            
            searchResultsDiv.innerHTML = '';
            
            if (data.places.length === 0) {
                searchResultsDiv.innerHTML = '<p style="padding: 10px; text-align: center;">검색 결과가 없습니다.</p>';
                searchResultsDiv.style.display = 'block';
                return;
            }
            
            // 검색 결과 표시
            const resultsList = document.createElement('ul');
            resultsList.style.listStyle = 'none';
            resultsList.style.padding = '0';
            resultsList.style.margin = '0';
            
            data.places.forEach(place => {
                const listItem = document.createElement('li');
                listItem.style.padding = '8px';
                listItem.style.borderBottom = '1px solid #eee';
                listItem.style.cursor = 'pointer';
                
                listItem.innerHTML = `
                    <strong>${place.name}</strong><br>
                    <small>${place.address}</small>
                `;
                
                // 항목 클릭 시 목적지로 설정
                listItem.addEventListener('click', function() {
                    if (destinationMarker) {
                        destinationMarker.setLatLng([place.lat, place.lng]);
                    } else {
                        destinationMarker = L.marker([place.lat, place.lng], { icon: destinationIcon }).addTo(map);
                    }
                    
                    // 지도 뷰 조정
                    if (currentPositionMarker) {
                        const bounds = L.latLngBounds([currentPositionMarker.getLatLng(), [place.lat, place.lng]]);
                        map.fitBounds(bounds, { padding: [50, 50] });
                    } else {
                        map.setView([place.lat, place.lng], 15);
                    }
                    
                    // 검색 결과 숨기기 및 선택된 목적지 표시
                    searchResultsDiv.style.display = 'none';
                    destinationInput.value = place.name;
                    statusElement.innerHTML = `목적지가 "${place.name}"으로 설정되었습니다.`;
                    
                    // 길 안내 버튼 활성화
                    startNavigationButton.disabled = false;
                });
                
                // 항목에 마우스 오버 효과
                listItem.addEventListener('mouseover', function() {
                    this.style.backgroundColor = '#f5f5f5';
                });
                
                listItem.addEventListener('mouseout', function() {
                    this.style.backgroundColor = '';
                });
                
                resultsList.appendChild(listItem);
            });
            
            searchResultsDiv.appendChild(resultsList);
            searchResultsDiv.style.display = 'block';
            
            statusElement.innerHTML = '검색 완료';
        } catch (error) {
            console.error('검색 오류:', error);
            statusElement.innerHTML = '검색 중 오류가 발생했습니다.';
        }
    });

    // 지도 클릭 이벤트 처리 - 직접 목적지 선택
    map.on('click', function(e) {
        // 수동 위치 설정 모드에서는 이 이벤트를 처리하지 않음
        if (isLocationManuallySet) return;
        
        const lat = e.latlng.lat;
        const lng = e.latlng.lng;
        
        // 목적지 마커 설정
        if (destinationMarker) {
            destinationMarker.setLatLng([lat, lng]);
        } else {
            destinationMarker = L.marker([lat, lng], { icon: destinationIcon }).addTo(map);
        }
        
        // 좌표 정보 표시
        destinationInput.value = `${lat.toFixed(6)}, ${lng.toFixed(6)}`;
        statusElement.innerHTML = `목적지 좌표: ${lat.toFixed(6)}, ${lng.toFixed(6)}`;
        
        // 길 안내 버튼 활성화
        startNavigationButton.disabled = false;
        
        // 검색 결과 숨기기
        if (searchResultsDiv) {
            searchResultsDiv.style.display = 'none';
        }
    });

    // 길 안내 시작
    startNavigationButton.addEventListener('click', async function() {
        if (!currentPositionMarker) {
            alert('현재 위치를 확인할 수 없습니다.');
            return;
        }
        
        if (!destinationMarker) {
            alert('목적지를 먼저 설정하세요.');
            return;
        }
        
        try {
            statusElement.innerHTML = '경로를 계산 중입니다...';
            
            const currentPosition = currentPositionMarker.getLatLng();
            const destinationPosition = destinationMarker.getLatLng();
            
            // 경로 요청
            const response = await fetch('/api/get_route', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    start_lat: currentPosition.lat,
                    start_lng: currentPosition.lng,
                    end_lat: destinationPosition.lat,
                    end_lng: destinationPosition.lng
                })
            });
            
            const data = await response.json();
            
            if (data.error) {
                alert(data.error);
                return;
            }
            
            // 세션 ID 저장
            sessionId = data.session_id;
            
            // 기존 경로 레이어 제거
            if (routeLayer) {
                map.removeLayer(routeLayer);
            }
            
            // 새로운 경로 그리기
            routeCoordinates = data.coordinates;
            routeLayer = L.polyline(routeCoordinates, {
                color: 'blue',
                weight: 5,
                opacity: 0.7
            }).addTo(map);
            
            // 지도 경계 조정
            map.fitBounds(routeLayer.getBounds(), { padding: [50, 50] });
            
            // 네비게이션 정보 표시
            distanceElement.textContent = `${data.total_distance}m`;
            timeElement.textContent = data.total_time;
            
            if (data.guidance && data.guidance.length > 0) {
                nextDirectionElement.textContent = data.guidance[0].description;
                // 첫 지시 음성 안내
                speakText(`안내를 시작합니다. ${data.guidance[0].description}`);
            } else {
                nextDirectionElement.textContent = "안내 정보가 없습니다.";
            }
            
            // UI 전환
            destinationForm.style.display = 'none';
            navigationInfo.style.display = 'block';
            
            // 네비게이션 상태 설정
            isNavigating = true;
            
            // 모바일 최적화 UI 표시
            if (document.getElementById('compass-container')) {
                document.getElementById('compass-container').style.display = 'flex';
            }
            
            // 위치 추적 시작
            startTracking();
            
            // 음성 켜기
            voiceEnabled = true;
            if (document.getElementById('toggle-voice')) {
                document.getElementById('toggle-voice').textContent = "음성 끄기";
            }
            
            statusElement.innerHTML = '길 안내를 시작합니다.';
            
            // 나침반 초기화
            initializeCompass();
            
        } catch (error) {
            console.error('경로 계산 오류:', error);
            statusElement.innerHTML = '경로 계산 중 오류가 발생했습니다.';
        }
    });

    // 길 안내 종료
    stopNavigationButton.addEventListener('click', function() {
        // 네비게이션 상태 초기화
        isNavigating = false;
        
        // 음성 중지
        if (window.speechSynthesis) {
            window.speechSynthesis.cancel();
        }
        
        // 위치 추적 중지
        stopTracking();
        
        // UI 전환
        navigationInfo.style.display = 'none';
        destinationForm.style.display = 'block';
        
        // 나침반 컨테이너 숨기기
        if (document.getElementById('compass-container')) {
            document.getElementById('compass-container').style.display = 'none';
        }
        
        // 정확도 표시 UI 및 수동 위치 버튼 숨기기
        accuracyInfoDiv.style.display = 'none';
        setLocationButton.style.display = 'none';
        
        statusElement.innerHTML = '길 안내가 종료되었습니다.';
    });
    
    // 음성 안내 켜기/끄기 기능
    if (document.getElementById('toggle-voice')) {
        document.getElementById('toggle-voice').addEventListener('click', function() {
            voiceEnabled = !voiceEnabled;
            this.textContent = voiceEnabled ? "음성 끄기" : "음성 켜기";
            
            if (!voiceEnabled) {
                speechSynthesis.cancel();  // 현재 재생 중인 음성 중지
            } else {
                // 음성 켤 때 현재 안내 다시 읽기
                speakText(nextDirectionElement.textContent);
            }
        });
    }

    // 초기 위치 설정 및 웹소켓 연결
    updateCurrentPosition();
    setupWebSocket();
    
    // 네비게이션 UI가 아닐 때는 정확도 정보 숨김
    if (!isNavigating) {
        accuracyInfoDiv.style.display = 'none';
    }
});