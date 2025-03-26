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
    const voiceInputButton = document.getElementById('voice-input');
    const navigationPanel = document.getElementById('navigation-panel');

    // 내 위치 버튼 생성
    const myLocationButton = document.createElement('button');
    myLocationButton.id = 'my-location';
    myLocationButton.innerHTML = '<i class="fas fa-location-arrow"></i>';
    myLocationButton.title = '내 위치';
    myLocationButton.style.position = 'absolute';
    myLocationButton.style.top = '70px';
    myLocationButton.style.right = '10px';
    myLocationButton.style.zIndex = '1000';
    myLocationButton.style.width = '40px';
    myLocationButton.style.height = '40px';
    myLocationButton.style.borderRadius = '50%';
    myLocationButton.style.backgroundColor = 'white';
    myLocationButton.style.border = 'none';
    myLocationButton.style.boxShadow = '0 2px 5px rgba(0,0,0,0.3)';
    myLocationButton.style.cursor = 'pointer';
    myLocationButton.style.display = 'flex';
    myLocationButton.style.justifyContent = 'center';
    myLocationButton.style.alignItems = 'center';
    document.body.appendChild(myLocationButton);

     // 패널 토글 버튼 생성
    const panelToggleButton = document.createElement('button');
    panelToggleButton.id = 'panel-toggle';
    panelToggleButton.innerHTML = '<i class="fas fa-chevron-down"></i>';
    panelToggleButton.title = '패널 접기/펼치기';
    panelToggleButton.style.position = 'fixed'; // absolute에서 fixed로 변경
    panelToggleButton.style.top = '70px'; // 위치 조정 (내 위치 버튼과 겹치지 않도록)
    panelToggleButton.style.left = '15px'; // 왼쪽으로 이동
    panelToggleButton.style.transform = 'none'; // 중앙 정렬 해제
    panelToggleButton.style.zIndex = '1002'; // 더 높은 z-index
    panelToggleButton.style.width = '40px';
    panelToggleButton.style.height = '40px';
    panelToggleButton.style.borderRadius = '50%';
    panelToggleButton.style.backgroundColor = 'white';
    panelToggleButton.style.border = 'none';
    panelToggleButton.style.boxShadow = '0 2px 5px rgba(0,0,0,0.3)';
    panelToggleButton.style.cursor = 'pointer';
    panelToggleButton.style.display = 'flex';
    panelToggleButton.style.justifyContent = 'center';
    panelToggleButton.style.alignItems = 'center';

    // 패널에 토글 버튼 추가하지 않고 body에 직접 추가
    document.body.appendChild(panelToggleButton);

    // 내 위치 버튼 위치 조정도 함께 수정
    myLocationButton.style.top = '15px'; // 더 상단으로 이동
    myLocationButton.style.right = '15px';
    myLocationButton.style.zIndex = '1002'; // z-index 상향

    // 글로벌 변수 추가
    let sessionId = null;
    let lastVoiceGuidance = '';
    let speechSynthesis = window.speechSynthesis;
    let compassHeading = null;
    let voiceEnabled = true;
    let isLocationManuallySet = false;
    let recognition = null;
    let isListening = false;
    let conversationState = 'idle'; // 대화 상태: idle, asking_destination, confirming_destination
    let isMapCenteredOnUser = true; // 지도가 사용자 위치를 중심으로 하는지

    // 음성 인식 초기화
    function initSpeechRecognition() {
        if ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window) {
            // Speech Recognition API 지원 확인
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            recognition = new SpeechRecognition();
            recognition.lang = 'ko-KR';
            recognition.continuous = false;
            recognition.interimResults = false;

            // 음성 인식 결과 이벤트
            recognition.onresult = function(event) {
                const transcript = event.results[0][0].transcript;
                console.log('음성 인식 결과:', transcript);
                
                // 대화 상태에 따른 처리
                handleVoiceInput(transcript);
            };

            recognition.onerror = function(event) {
                console.error('음성 인식 오류:', event.error);
                if (event.error === 'no-speech') {
                    speakText("음성이 감지되지 않았습니다. 다시 시도해주세요.");
                } else {
                    speakText("음성 인식 중 오류가 발생했습니다. 다시 시도해주세요.");
                }
                stopListening();
            };

            recognition.onend = function() {
                isListening = false;
                voiceInputButton.textContent = '🎤 음성으로 목적지 입력';
                voiceInputButton.classList.remove('listening');
            };

            return true;
        } else {
            console.error('이 브라우저는 음성 인식을 지원하지 않습니다.');
            return false;
        }
    }

    // 음성 인식 시작
    function startListening() {
        if (recognition && !isListening) {
            try {
                recognition.start();
                isListening = true;
                voiceInputButton.textContent = '🔴 듣는 중...';
                voiceInputButton.classList.add('listening');
                return true;
            } catch (e) {
                console.error('음성 인식 시작 오류:', e);
                return false;
            }
        }
        return false;
    }

    // 음성 인식 중지
    function stopListening() {
        if (recognition && isListening) {
            recognition.stop();
            isListening = false;
            voiceInputButton.textContent = '🎤 음성으로 목적지 입력';
            voiceInputButton.classList.remove('listening');
        }
    }

    // 음성 입력 처리
    function handleVoiceInput(transcript) {
        switch (conversationState) {
            case 'idle':
                // 초기 상태인 경우 처리하지 않음
                break;
                
            case 'asking_destination':
                // 목적지 질문에 대한 응답 처리
                destinationInput.value = transcript;
                speakText(`목적지를 ${transcript}로 설정할까요? 네 또는 아니오로 대답해주세요.`);
                conversationState = 'confirming_destination';
                setTimeout(() => {
                    startListening();
                }, 3000); // TTS 재생 후 사용자 응답 듣기
                break;
                
            case 'confirming_destination':
                // 목적지 확인에 대한 응답 처리
                const response = transcript.toLowerCase();
                if (response.includes('네') || response.includes('예') || response.includes('응') || response.includes('좋아')) {
                    speakText("목적지를 검색합니다.");
                    conversationState = 'idle';
                    searchButton.click(); // 검색 실행
                } else if (response.includes('아니') || response.includes('아니오') || response.includes('아냐')) {
                    speakText("목적지를 다시 말씀해주세요.");
                    conversationState = 'asking_destination';
                    destinationInput.value = '';
                    setTimeout(() => {
                        startListening();
                    }, 2000);
                } else {
                    speakText("네 또는 아니오로 대답해주세요. 목적지를 설정할까요?");
                    setTimeout(() => {
                        startListening();
                    }, 2500);
                }
                break;
        }
    }

    // 음성 입력 버튼 이벤트 처리
    if (voiceInputButton) {
        voiceInputButton.addEventListener('click', function() {
            if (isListening) {
                stopListening();
                return;
            }
            
            if (!initSpeechRecognition()) {
                speakText("죄송합니다. 이 브라우저에서는 음성 인식이 지원되지 않습니다.");
                return;
            }
            
            // 대화 시작
            speakText("목적지를 말씀해주세요.");
            conversationState = 'asking_destination';
            
            // TTS 재생 후 음성 인식 시작
            setTimeout(() => {
                startListening();
            }, 1500);
        });
    }

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

    // 패널 토글 버튼 이벤트
    let isPanelCollapsed = false;
    panelToggleButton.addEventListener('click', function() {
        console.log("패널 토글 버튼 클릭됨");
        
        if (isPanelCollapsed) {
            // 패널 확장
            navigationPanel.style.height = '';
            navigationPanel.style.overflow = '';
            this.innerHTML = '<i class="fas fa-chevron-down"></i>';
            isPanelCollapsed = false;
            speakText("패널이 확장되었습니다.");
        } else {
            // 패널 접기
            navigationPanel.style.height = '30px';
            navigationPanel.style.overflow = 'hidden';
            this.innerHTML = '<i class="fas fa-chevron-up"></i>';
            isPanelCollapsed = true;
            speakText("패널이 최소화되었습니다.");
        }
    });

    // 내 위치 버튼 이벤트
    myLocationButton.addEventListener('click', function() {
        console.log("내 위치 버튼 클릭됨");
        
        if (currentPositionMarker) {
            map.setView(currentPositionMarker.getLatLng(), 17);
            isMapCenteredOnUser = true;
            speakText("현재 위치로 이동했습니다.");
        } else {
            updateCurrentPosition().then(() => {
                if (currentPositionMarker) {
                    map.setView(currentPositionMarker.getLatLng(), 17);
                    isMapCenteredOnUser = true;
                    speakText("현재 위치로 이동했습니다.");
                }
            }).catch(error => {
                speakText("현재 위치를 확인할 수 없습니다.");
            });
        }
    });

    // 지도 이동 감지하여 중심 모드 해제
    map.on('dragstart', function() {
        isMapCenteredOnUser = false;
    });

    // 음성 안내 함수 개선
    function speakText(text) {
        if (!text) return;
        
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
        
        // 디버깅
        console.log('TTS:', text);
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
            speakText("서버에 연결되었습니다.");
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
                speakText("경로를 이탈했습니다. 현재 위치를 수동으로 설정하거나 제자리에서 잠시 기다려주세요.");
            } else {
                // 경로 내에 있을 때는 숨김 
                if (!isLocationManuallySet) {
                    setLocationButton.style.display = 'none';
                }
            }
        };
        
        socket.onclose = function(event) {
            console.log("웹소켓 연결 종료");
            speakText("서버와의 연결이 끊어졌습니다. 다시 연결을 시도합니다.");
            // 자동 재연결 시도
            setTimeout(setupWebSocket, 1000);
        };
        
        socket.onerror = function(error) {
            console.log("웹소켓 오류:", error);
            speakText("서버 연결 중 오류가 발생했습니다.");
        };
    }

    // 위치 권한 요청 함수
    function requestLocationPermission() {
        return new Promise((resolve, reject) => {
            if (navigator.permissions && navigator.permissions.query) {
                navigator.permissions.query({ name: 'geolocation' })
                    .then(permissionStatus => {
                        console.log("위치 권한 상태:", permissionStatus.state);
                        
                        if (permissionStatus.state === 'granted') {
                            resolve();
                        } else if (permissionStatus.state === 'prompt') {
                            speakText("위치 정보 접근 권한이 필요합니다. 권한 요청 시 '허용'을 선택해주세요.");
                            navigator.geolocation.getCurrentPosition(
                                () => resolve(),
                                (error) => reject(error)
                            );
                        } else {
                            speakText("위치 정보 접근이 차단되었습니다. 브라우저 설정에서 위치 권한을 허용해주세요.");
                            reject(new Error("위치 권한이 차단되었습니다."));
                        }
                    });
            } else {
                // 권한 API 미지원 브라우저
                navigator.geolocation.getCurrentPosition(
                    () => resolve(),
                    (error) => reject(error)
                );
            }
        });
    }

    // 현재 위치 가져오기
    function getCurrentPosition() {
        return new Promise((resolve, reject) => {
            if (navigator.geolocation) {
                // 위치 요청 시작
                navigator.geolocation.getCurrentPosition(
                    position => {
                        console.log("위치 정보 획득 성공:", position.coords);
                        resolve(position);
                    }, 
                    error => {
                        console.error("위치 정보 획득 실패:", error);
                        reject(error);
                    }, 
                    {
                        enableHighAccuracy: true,
                        timeout: 15000,
                        maximumAge: 0
                    }
                );
            } else {
                reject(new Error('이 브라우저는 위치 정보를 지원하지 않습니다.'));
            }
        });
    }

    // 현재 위치 업데이트 및 표시
    async function updateCurrentPosition() {
        try {
            console.log("현재 위치 업데이트 시작...");
            const position = await getCurrentPosition();
            const { latitude, longitude, accuracy } = position.coords;
            
            console.log(`위치 정보 업데이트 - 위도: ${latitude}, 경도: ${longitude}, 정확도: ${accuracy}m`);
            
            // 정확도 정보 표시
            accuracyInfoDiv.textContent = `위치 정확도: ${Math.round(accuracy)}m`;
            accuracyInfoDiv.style.display = 'block';
            
            // 정확도가 너무 낮은 경우 경고
            if (accuracy > 100) {
                statusElement.innerHTML = `위치 정확도가 낮습니다(${Math.round(accuracy)}m). 수동 위치 설정을 사용해보세요.`;
                setLocationButton.style.display = 'block';
                speakText(`위치 정확도가 낮습니다. 실외로 이동하거나 수동 위치 설정을 사용해보세요.`);
            } else {
                if (!isLocationManuallySet) {
                    setLocationButton.style.display = 'none';
                }
                statusElement.innerHTML = '현재 위치를 확인했습니다.';
                speakText("현재 위치를 확인했습니다. 목적지를 설정하세요.");
            }
            
            // 현재 위치 마커 업데이트
            if (!currentPositionMarker) {
                currentPositionMarker = L.marker([latitude, longitude], { icon: currentPositionIcon }).addTo(map);
                map.setView([latitude, longitude], 17);
            } else {
                currentPositionMarker.setLatLng([latitude, longitude]);
                // 지도 중심 이동 (사용자 중심 모드일 때만)
                if (isMapCenteredOnUser) {
                    map.panTo([latitude, longitude]);
                }
            }
            
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
            speakText("위치 정보를 가져오는 데 실패했습니다. 위치 권한을 허용하고 다시 시도하거나, 수동 위치 설정을 사용해보세요.");
            throw error;
        }
    }

    // 위치 실시간 추적 시작 - 개선된 버전
    function startTracking() {
        if (watchId) {
            console.log("이미 위치 추적 중입니다");
            return;
        }
        
        console.log("위치 추적 시작...");
        statusElement.innerHTML = "GPS 위치를 추적 중입니다...";
        speakText("GPS 위치 추적을 시작합니다.");
        
        // 위치 정확도 표시 활성화
        accuracyInfoDiv.style.display = 'block';
        
        // 위치 추적 옵션
        const options = {
            enableHighAccuracy: true,
            maximumAge: 0,
            timeout: 15000
        };
        
        watchId = navigator.geolocation.watchPosition(
            function(position) {
                // 성공적으로 위치 정보 받았을 때 실행
                const { latitude, longitude, accuracy } = position.coords;
                
                console.log(`위치 업데이트: ${latitude}, ${longitude}, 정확도: ${accuracy}m`);
                
                // 수동으로 위치를 설정한 경우 무시
                if (isLocationManuallySet) return;
                
                // 정확도 정보 표시
                accuracyInfoDiv.textContent = `위치 정확도: ${Math.round(accuracy)}m`;
                
                // 정확도가 너무 낮은 경우 수동 위치 설정 버튼 표시
                if (accuracy > 100) {
                    statusElement.innerHTML = `위치 정확도가 낮습니다(${Math.round(accuracy)}m). 수동 위치 설정을 사용해보세요.`;
                    setLocationButton.style.display = 'block';
                } else {
                    if (!isLocationManuallySet) {
                        setLocationButton.style.display = 'none';
                    }
                }
                
                // 위치 마커 업데이트
                if (currentPositionMarker) {
                    currentPositionMarker.setLatLng([latitude, longitude]);
                } else {
                    currentPositionMarker = L.marker([latitude, longitude], { icon: currentPositionIcon }).addTo(map);
                }
                
                // 네비게이션 중이고 지도가 사용자 중심으로 설정된 경우에만 지도 중심 이동
                if (isNavigating && isMapCenteredOnUser) {
                    map.panTo([latitude, longitude]);
                }
                
                // 웹소켓으로 위치 업데이트 전송
                if (socket && socket.readyState === WebSocket.OPEN && isNavigating) {
                    socket.send(JSON.stringify({
                        latitude: latitude,
                        longitude: longitude,
                        accuracy: accuracy,
                        session_id: sessionId
                    }));
                }
            },
            function(error) {
                console.error("위치 추적 오류:", error.code, error.message);
                
                let errorMsg = "";
                switch (error.code) {
                    case error.PERMISSION_DENIED:
                        errorMsg = "위치 권한이 거부되었습니다. 브라우저 설정에서 위치 권한을 허용해주세요.";
                        break;
                    case error.POSITION_UNAVAILABLE:
                        errorMsg = "위치 정보를 사용할 수 없습니다. GPS 신호가 약한 지역일 수 있습니다.";
                        break;
                    case error.TIMEOUT:
                        errorMsg = "위치 정보 요청 시간이 초과되었습니다.";
                        break;
                    default:
                        errorMsg = `위치 추적 오류: ${error.message}`;
                }
                
                statusElement.innerHTML = errorMsg;
                speakText(errorMsg);
                
                // 오류 발생 시 수동 위치 설정 활성화
                setLocationButton.style.display = 'block';
            },
            options
        );
    }

    // 위치 추적 중지
    function stopTracking() {
        if (watchId) {
            navigator.geolocation.clearWatch(watchId);
            watchId = null;
            console.log("위치 추적 중지됨");
        }
        
        // 수동 위치 설정 비활성화
        isLocationManuallySet = false;
        setLocationButton.style.display = 'none';
    }

    // 수동 위치 설정 버튼 이벤트 핸들러
    setLocationButton.addEventListener('click', function() {
        speakText("지도를 클릭하여 현재 위치를 수동으로 설정하세요.");
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
            speakText("현재 위치를 수동으로 설정했습니다.");
            
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
                speakText("자동 위치 추적으로 돌아갑니다.");
                
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

    // 목적지 입력 필드에 엔터키 이벤트 추가
    destinationInput.addEventListener('keypress', function(event) {
        if (event.key === 'Enter') {
            event.preventDefault();
            searchButton.click(); // 검색 버튼 클릭 이벤트 트리거
        }
    });

    // 목적지 검색
    searchButton.addEventListener('click', async function() {
        const keyword = destinationInput.value.trim();
        if (!keyword) {
            speakText('목적지를 입력하세요.');
            return;
        }
        
        try {
            console.log("목적지 검색 시작:", keyword);
            statusElement.innerHTML = '목적지 검색 중...';
            speakText('목적지를 검색 중입니다.');
            
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
                        speakText('목적지가 설정되었습니다. 길 안내 시작 버튼을 눌러주세요.');
                        startNavigationButton.disabled = false;
                        
                        // 검색 결과 숨기기
                        if (searchResultsDiv) {
                            searchResultsDiv.style.display = 'none';
                        }
                        
                        return;
                    }
                }
            }
            
            // 위치 검색 API 호출 - 현재 위치 기반 검색 추가
            let searchUrl = `/api/search?keyword=${encodeURIComponent(keyword)}`;
            
            // 현재 위치가 있는 경우 해당 위치 기준으로 검색
            if (currentPositionMarker) {
                const pos = currentPositionMarker.getLatLng();
                searchUrl += `&lat=${pos.lat}&lng=${pos.lng}&radius=5000`;
            }
            
            console.log(`검색 API 호출: ${searchUrl}`);
            const response = await fetch(searchUrl);
            console.log("검색 응답 상태:", response.status);
            
            if (!response.ok) {
                throw new Error(`API 응답 오류: ${response.status}`);
            }
            
            const data = await response.json();
            console.log("검색 결과:", data);
            
            if (data.error) {
                speakText(data.error);
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
                speakText("검색 결과가 없습니다. 다른 키워드로 다시 시도해주세요.");
                return;
            }
            
            // 검색 결과 표시
            const resultsList = document.createElement('ul');
            resultsList.style.listStyle = 'none';
            resultsList.style.padding = '0';
            resultsList.style.margin = '0';
            
            // 검색 결과 멘트
            speakText(`${keyword}에 대해 ${data.places.length}개의 검색 결과가 있습니다. 원하는 장소를 선택해주세요.`);
            
            data.places.forEach((place, index) => {
                const listItem = document.createElement('li');
                listItem.style.padding = '8px';
                listItem.style.borderBottom = '1px solid #eee';
                listItem.style.cursor = 'pointer';
                
                // 현재 위치에서의 거리 계산
                let distanceText = '';
                if (currentPositionMarker) {
                    const currentPos = currentPositionMarker.getLatLng();
                    const placePos = L.latLng(place.lat, place.lng);
                    const distance = Math.round(currentPos.distanceTo(placePos));
                    distanceText = `<span style="color:#4285F4; font-weight:bold; font-size:12px;">내 위치에서 ${distance}m</span>`;
                }
                
                listItem.innerHTML = `
                    <strong>${place.name}</strong><br>
                    <small>${place.address}</small>
                    ${distanceText ? '<br>' + distanceText : ''}
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
                    speakText(`목적지가 ${place.name}으로 설정되었습니다. 길 안내 시작 버튼을 눌러주세요.`);
                    
                    // 길 안내 버튼 활성화
                    startNavigationButton.disabled = false;
                });
                
                // 항목 읽기 기능 추가 (항목 위에 오래 누르면 음성으로 읽어줌)
                listItem.addEventListener('contextmenu', function(e) {
                    e.preventDefault();
                    
                    let distanceInfo = '';
                    if (currentPositionMarker) {
                        const currentPos = currentPositionMarker.getLatLng();
                        const placePos = L.latLng(place.lat, place.lng);
                        const distance = Math.round(currentPos.distanceTo(placePos));
                        distanceInfo = `내 위치에서 ${distance}미터 떨어져 있습니다.`;
                    }
                    
                    speakText(`${index + 1}번째 결과: ${place.name}, ${place.address}. ${distanceInfo}`);
                });
                
                // 모바일 터치 오래 누르기 지원
                let touchTimer;
                listItem.addEventListener('touchstart', function(e) {
                    touchTimer = setTimeout(() => {
                        let distanceInfo = '';
                        if (currentPositionMarker) {
                            const currentPos = currentPositionMarker.getLatLng();
                            const placePos = L.latLng(place.lat, place.lng);
                            const distance = Math.round(currentPos.distanceTo(placePos));
                            distanceInfo = `내 위치에서 ${distance}미터 떨어져 있습니다.`;
                        }
                        
                        speakText(`${index + 1}번째 결과: ${place.name}, ${place.address}. ${distanceInfo}`);
                    }, 800);
                });
                
                listItem.addEventListener('touchend', function() {
                    clearTimeout(touchTimer);
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
            speakText('검색 중 오류가 발생했습니다. 다시 시도해주세요.');
        }
    });

    // 길 안내 시작
    startNavigationButton.addEventListener('click', async function() {
        if (!currentPositionMarker) {
            speakText('현재 위치를 확인할 수 없습니다.');
            return;
        }
        
        if (!destinationMarker) {
            speakText('목적지를 먼저 설정하세요.');
            return;
        }
        
        try {
            statusElement.innerHTML = '경로를 계산 중입니다...';
            speakText('경로를 계산 중입니다. 잠시만 기다려주세요.');
            
            const currentPosition = currentPositionMarker.getLatLng();
            const destinationPosition = destinationMarker.getLatLng();
            
            console.log(`경로 계산: ${currentPosition.lat},${currentPosition.lng} -> ${destinationPosition.lat},${destinationPosition.lng}`);
            
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
            
            if (!response.ok) {
                throw new Error(`경로 API 응답 오류: ${response.status}`);
            }
            
            const data = await response.json();
            console.log("경로 계산 결과:", data);
            
            if (data.error) {
                speakText(data.error);
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
            
            // 지도 중심을 사용자 위치로 설정
            if (currentPositionMarker) {
                map.setView(currentPositionMarker.getLatLng(), 17);
                isMapCenteredOnUser = true;
            }
            
            // 네비게이션 정보 표시
            distanceElement.textContent = `${data.total_distance}m`;
            timeElement.textContent = data.total_time;
            
            // 초기 안내 메시지 설정
            let initialGuidance = `목적지까지 총 ${data.total_distance}미터, 예상 소요 시간은 ${data.total_time}입니다. `;
            
            if (data.guidance && data.guidance.length > 0) {
                nextDirectionElement.textContent = data.guidance[0].description;
                initialGuidance += data.guidance[0].description;
            } else {
                nextDirectionElement.textContent = "안내 정보가 없습니다.";
                initialGuidance += "안내 정보가 없습니다.";
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
            
            // 첫 지시 음성 안내
            speakText(initialGuidance);
            
            // 나침반 초기화
            initializeCompass();
            
        } catch (error) {
            console.error('경로 계산 오류:', error);
            statusElement.innerHTML = '경로 계산 중 오류가 발생했습니다.';
            speakText('경로 계산 중 오류가 발생했습니다. 다시 시도해주세요.');
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
        speakText('길 안내가 종료되었습니다.');
    });
    
    // 음성 안내 켜기/끄기 기능
    if (document.getElementById('toggle-voice')) {
        document.getElementById('toggle-voice').addEventListener('click', function() {
            voiceEnabled = !voiceEnabled;
            this.textContent = voiceEnabled ? "음성 끄기" : "음성 켜기";
            
            if (!voiceEnabled) {
                speechSynthesis.cancel();  // 현재 재생 중인 음성 중지
                speakText("음성 안내를 끕니다.");
            } else {
                // 음성 켤 때 현재 안내 다시 읽기
                speakText("음성 안내를 켭니다. " + nextDirectionElement.textContent);
            }
        });
    }

    // 초기화 시 위치 권한 요청 및 추적 시작
    (async function initializeApp() {
        try {
            // 위치 권한 요청
            await requestLocationPermission();
            console.log("위치 권한 획득 성공");
            
            // 초기 위치 확인 및 추적 시작
            await updateCurrentPosition();
            startTracking();
            
            // 웹소켓 연결
            setupWebSocket();
            
            // 앱 시작 안내
            speakText("안녕하세요. 길 안내 서비스가 시작되었습니다. 음성으로 목적지를 입력하시려면 화면 상단의 마이크 버튼을 눌러주세요.");
        } catch (error) {
            console.error("앱 초기화 실패:", error);
            statusElement.innerHTML = "위치 정보를 가져오는 데 실패했습니다. 위치 권한을 허용해주세요.";
            speakText("위치 정보를 가져오는 데 실패했습니다. 위치 권한을 허용해주세요.");
        }
    })();
});