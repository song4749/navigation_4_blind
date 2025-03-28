// UI 관련 기능을 처리하는 모듈

class UIService {
    constructor() {
      // UI 요소 참조
      this.statusElement = document.getElementById('status');
      this.destinationInput = document.getElementById('destination');
      this.searchButton = document.getElementById('search');
      this.voiceButton = document.getElementById('voice-input');
      this.startNavigationButton = document.getElementById('start-navigation');
      this.stopNavigationButton = document.getElementById('stop-navigation');
      this.centerMapButton = document.getElementById('center-map');
      this.togglePanelButton = document.getElementById('toggle-panel');
      this.navigationPanel = document.getElementById('navigation-panel');
      this.navigationInfo = document.getElementById('navigation-info');
      this.destinationForm = document.getElementById('destination-form');
      this.distanceElement = document.getElementById('distance');
      this.timeElement = document.getElementById('time');
      this.nextDirectionElement = document.getElementById('next-direction');
      this.readInstructionButton = document.getElementById('read-instruction');
      this.toggleVoiceButton = document.getElementById('toggle-voice');
      this.searchResultsDiv = document.getElementById('search-results');
      
      // 위치 디버그 UI 초기화
      this.initLocationDebugUI();
      
      // 스타일 초기화
      this.initStyles();
    }
  
    // 위치 디버그 UI 초기화
    initLocationDebugUI() {
      const locationDebug = document.createElement('div');
      locationDebug.id = 'location-debug';
      locationDebug.style.cssText = `
      position: fixed;
      top: 10px;
      left: 10px;
      background: rgba(0,0,0,0.7);
      color: white;
      padding: 8px;
      border-radius: 5px;
      font-size: 11px;
      max-width: 200px;
      z-index: 1000;
      `;
      
      locationDebug.innerHTML = `
      <div>위치 권한: <span id="loc-permission">확인 중...</span></div>
      <div>현재 위도: <span id="loc-lat">N/A</span></div>
      <div>현재 경도: <span id="loc-lng">N/A</span></div>
      <div>정확도: <span id="loc-accuracy">N/A</span>m</div>
      <button id="refresh-location" style="font-size: 11px; padding: 3px 5px; margin-top: 5px;">위치 갱신</button>
      `;
      document.body.appendChild(locationDebug);
    }
  
    // 스타일 초기화
    initStyles() {
      const style = document.createElement('style');
      style.textContent = `
      .spinner {
          display: inline-block;
          width: 20px;
          height: 20px;
          border: 3px solid rgba(0,0,0,0.1);
          border-radius: 50%;
          border-top-color: #4a89dc;
          animation: spin 1s ease-in-out infinite;
          vertical-align: middle;
          margin-right: 8px;
      }
  
      @keyframes spin {
          to { transform: rotate(360deg); }
      }
      
      .voice-recording {
          background-color: #f44336 !important;
      }
      
      .current-position-marker {
          animation: pulse 1.5s infinite;
      }
      
      @keyframes pulse {
          0% { opacity: 1; }
          50% { opacity: 0.4; }
          100% { opacity: 1; }
      }
      
      #search-results {
          max-height: 300px;
          overflow-y: auto;
          background: white;
          border-radius: 8px;
          box-shadow: 0 2px 10px rgba(0,0,0,0.1);
      }
      
      #search-results ul {
          list-style: none;
          padding: 0;
          margin: 0;
      }
      
      #search-results li {
          padding: 10px 15px;
          border-bottom: 1px solid #eee;
          cursor: pointer;
      }
      
      #search-results li:hover {
          background-color: #f5f5f5;
      }
      
      .distance-info {
          color: #0066cc;
          font-weight: bold;
          margin-top: 5px;
      }
      
      .no-location {
          color: #cc0000; 
          font-style: italic;
      }
      `;
      document.head.appendChild(style);
    }
  
    // 위치 디버그 정보 업데이트
    updateLocationDebug(lat, lng, accuracy, permission) {
      const permElem = document.getElementById('loc-permission');
      const latElem = document.getElementById('loc-lat');
      const lngElem = document.getElementById('loc-lng');
      const accElem = document.getElementById('loc-accuracy');
      
      if (permission) permElem.textContent = permission;
      if (lat) latElem.textContent = lat.toFixed(6);
      if (lng) lngElem.textContent = lng.toFixed(6);
      if (accuracy) accElem.textContent = accuracy.toFixed(1);
    }
  
    // 상태 메시지 설정
    setStatus(message, isLoading = false) {
      if (isLoading) {
        this.statusElement.innerHTML = `<div class="spinner"></div> ${message}`;
      } else {
        this.statusElement.innerHTML = message;
      }
    }
  
    // 검색 결과 표시
    displaySearchResults(places, currentPosition, onSelectPlace) {
        if (!this.searchResultsDiv) {
          this.searchResultsDiv = document.getElementById('search-results');
        }
      
        // 결과 컨테이너 초기화
        this.searchResultsDiv.innerHTML = '';
        this.searchResultsDiv.style.display = 'block';
      
        // 경고 메시지가 있으면 표시
        if (places.warning) {
          const warningElement = document.createElement('div');
          warningElement.className = 'search-warning';
          warningElement.innerHTML = `<i class="fas fa-info-circle"></i> ${places.warning}`;
          warningElement.style.cssText = 'padding: 8px 12px; background-color: #FFF3CD; color: #856404; margin-bottom: 10px; border-radius: 4px; font-size: 14px;';
          this.searchResultsDiv.appendChild(warningElement);
        }
  
      // 결과 목록 생성
      const ul = document.createElement('ul');
  
      places.forEach((place) => {
        const li = document.createElement('li');
        
        // 거리 정보 처리
        let distanceText = '';
        if (place.distance) {
          const distanceValue = parseInt(place.distance);
          // 거리에 따라 다른 색상 적용
          let distanceColor = '#2196F3'; // 기본 파란색
          
          if (distanceValue < 500) {
            distanceColor = '#4CAF50'; // 500m 이내는 녹색
          } else if (distanceValue > 2000) {
            distanceColor = '#FF5722'; // 2km 이상은 주황색
          }
          
          // 거리 표시 형식 (1km 이상은 km 단위로)
          const formattedDistance = distanceValue < 1000 ? 
            `${distanceValue}m` : 
            `${(distanceValue / 1000).toFixed(1)}km`;
          
          distanceText = `<div class="distance-info" style="color: ${distanceColor};">
            현재 위치에서 ${formattedDistance}
          </div>`;
        } else {
          distanceText = '<div class="no-location">위치 정보 없음</div>';
        }
        
        li.innerHTML = `
          <strong>${place.name}</strong>
          <div>${place.address}</div>
          ${distanceText}
        `;
  
        // 클릭 이벤트
        li.addEventListener('click', () => {
          if (onSelectPlace) {
            onSelectPlace(place);
          }
        });
  
        ul.appendChild(li);
      });
  
      this.searchResultsDiv.appendChild(ul);
    }
  
    // 네비게이션 정보 업데이트
    updateNavigationInfo(distance, time, nextDirection) {
      this.distanceElement.textContent = distance;
      this.timeElement.textContent = time;
      
      if (nextDirection) {
        this.nextDirectionElement.textContent = nextDirection;
      }
    }
  
    // 네비게이션 모드 전환
    setNavigationMode(isNavigating) {
      if (isNavigating) {
        this.destinationForm.style.display = 'none';
        this.navigationInfo.style.display = 'block';
      } else {
        this.destinationForm.style.display = 'block';
        this.navigationInfo.style.display = 'none';
      }
    }
  
    // 버튼 활성화/비활성화
    setButtonEnabled(buttonId, enabled) {
      const button = document.getElementById(buttonId);
      if (button) {
        button.disabled = !enabled;
      }
    }
  
    // 검색창 값 설정
    setDestinationInput(value) {
      if (this.destinationInput) {
        this.destinationInput.value = value;
      }
    }
  
    // 검색창 값 가져오기
    getDestinationInput() {
      return this.destinationInput ? this.destinationInput.value : '';
    }
  
    // 검색 결과 숨기기
    hideSearchResults() {
      if (this.searchResultsDiv) {
        this.searchResultsDiv.style.display = 'none';
      }
    }
  
    // 음성 버튼 상태 설정
    setVoiceButtonRecording(isRecording) {
      if (isRecording) {
        this.voiceButton.classList.add('voice-recording');
      } else {
        this.voiceButton.classList.remove('voice-recording');
      }
    }
  
    // 패널 토글 상태 설정
    togglePanel() {
      this.navigationPanel.classList.toggle('collapsed');
      this.togglePanelButton.innerHTML = this.navigationPanel.classList.contains('collapsed') 
        ? '<i class="fas fa-chevron-down"></i>' 
        : '<i class="fas fa-chevron-up"></i>';
    }
  
    // 이벤트 리스너 등록
    registerEventListeners(handlers) {
      // 검색 버튼
      if (handlers.onSearch) {
        this.searchButton.addEventListener('click', handlers.onSearch);
      }
      
      // 음성 입력 버튼
      if (handlers.onVoiceInput) {
        this.voiceButton.addEventListener('click', handlers.onVoiceInput);
      }
      
      // 길 안내 시작 버튼
      if (handlers.onStartNavigation) {
        this.startNavigationButton.addEventListener('click', handlers.onStartNavigation);
      }
      
      // 길 안내 종료 버튼
      if (handlers.onStopNavigation) {
        this.stopNavigationButton.addEventListener('click', handlers.onStopNavigation);
      }
      
      // 현재 위치로 이동 버튼
      if (handlers.onCenterMap) {
        this.centerMapButton.addEventListener('click', handlers.onCenterMap);
      }
      
      // 패널 토글 버튼
      if (handlers.onTogglePanel) {
        this.togglePanelButton.addEventListener('click', handlers.onTogglePanel);
      } else {
        this.togglePanelButton.addEventListener('click', this.togglePanel.bind(this));
      }
      
      // 안내 읽기 버튼
      if (handlers.onReadInstruction) {
        this.readInstructionButton.addEventListener('click', handlers.onReadInstruction);
      }
      
      // 음성 토글 버튼
      if (handlers.onToggleVoice) {
        this.toggleVoiceButton.addEventListener('click', handlers.onToggleVoice);
      }
      
      // 위치 갱신 버튼
      const refreshLocationButton = document.getElementById('refresh-location');
      if (refreshLocationButton && handlers.onRefreshLocation) {
        refreshLocationButton.addEventListener('click', handlers.onRefreshLocation);
      }
    }
}
  
// 단일 인스턴스 생성하여 내보내기
const ui = new UIService();
export default ui;