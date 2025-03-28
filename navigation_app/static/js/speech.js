// 음성 관련 기능을 모아놓은 모듈

class SpeechService {
    constructor() {
        this.synthesis = window.speechSynthesis;
        this.recognition = null;
        this.isListening = false;
        this.isVoiceEnabled = true;
        this.voiceQueue = [];
        this.isSpeaking = false;
        this.preferredVoice = null;
        
        // 음성 초기화
        this.initVoices();
    }
    
    // 음성 합성 초기화
    initVoices() {
        // 이미 로드된 경우
        if (this.synthesis.getVoices().length) {
            this.setPreferredVoice();
        }
        
        // 음성이 로드되면 호출되는 이벤트
        this.synthesis.onvoiceschanged = () => {
            this.setPreferredVoice();
        };
    }
    
    // 선호 음성 설정
    setPreferredVoice() {
        const voices = this.synthesis.getVoices();
        
        // 선호도 순서대로 음성 찾기: 한국어 > 영어
        const koreanVoice = voices.find(voice => /ko/i.test(voice.lang));
        const englishVoice = voices.find(voice => /en/i.test(voice.lang));
        
        this.preferredVoice = koreanVoice || englishVoice || voices[0];
        console.log(`선택된 음성: ${this.preferredVoice ? this.preferredVoice.name : '없음'}`);
    }
    
    // 텍스트를 음성으로 변환
    speak(text, priority = 'normal') {
        if (!this.isVoiceEnabled) return;
        
        // 음성 합성 지원 여부 확인
        if (!this.synthesis || typeof this.synthesis.speak !== 'function') {
            console.warn('음성 합성이 지원되지 않습니다');
            return;
        }
        
        // 중요한 메시지는 콘솔에 출력
        console.log(`[음성]: ${text} (${priority})`);
        
        try {
            // 우선순위가 높으면 현재 음성 중지
            if (priority === 'high' && this.isSpeaking) {
                this.synthesis.cancel();
                this.voiceQueue = [];
            }
            
            // 대기열에 추가
            this.voiceQueue.push(text);
            
            // 현재 말하고 있지 않으면 시작
            if (!this.isSpeaking) {
                this.processVoiceQueue();
            }
        } catch (error) {
            console.error('음성 합성 실행 오류:', error);
        }
    }
    
    // 기존 speak 함수 호출을 위한 별칭 함수 추가
    speakText(text, priority = 'normal') {
        return this.speak(text, priority);
    }
    
    // 음성 대기열 처리
    processVoiceQueue() {
        if (this.voiceQueue.length === 0) {
            this.isSpeaking = false;
            return;
        }
        
        this.isSpeaking = true;
        const text = this.voiceQueue.shift();
        
        // 음성 합성 생성
        const utterance = new SpeechSynthesisUtterance(text);
        
        // 음성 설정
        if (this.preferredVoice) {
            utterance.voice = this.preferredVoice;
        }
        
        utterance.rate = 1.0;
        utterance.pitch = 1.0;
        utterance.volume = 1.0;
        
        // 음성 종료 이벤트
        utterance.onend = () => {
            setTimeout(() => this.processVoiceQueue(), 100);
        };
        
        // 음성 오류 이벤트
        utterance.onerror = (event) => {
            console.error('음성 합성 오류:', event);
            setTimeout(() => this.processVoiceQueue(), 100);
        };
        
        // 말하기 시작
        this.synthesis.speak(utterance);
    }
    
    // 음성 인식 초기화
    initSpeechRecognition(callback) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        
        if (!SpeechRecognition) {
            console.error("음성 인식이 이 브라우저에서 지원되지 않습니다.");
            return;
        }
        
        this.recognition = new SpeechRecognition();
        this.recognition.lang = 'ko-KR';
        this.recognition.continuous = false;
        this.recognition.interimResults = false;
        
        // 음성 인식 결과 처리
        this.recognition.onresult = (event) => {
            const last = event.results.length - 1;
            const transcript = event.results[last][0].transcript;
            console.log('음성 인식 결과:', transcript);
            
            if (callback) {
                callback(transcript);
            }
        };
        
        // 음성 인식 종료 처리
        this.recognition.onend = () => {
            this.isListening = false;
            console.log('음성 인식 종료');
        };
        
        // 음성 인식 오류 처리
        this.recognition.onerror = (event) => {
            console.error('음성 인식 오류:', event.error);
            this.isListening = false;
            
            // 오류 메시지
            let errorMsg = '음성 인식 중 오류가 발생했습니다.';
            if (event.error === 'no-speech') {
                errorMsg = '음성이 감지되지 않았습니다.';
            } else if (event.error === 'aborted') {
                errorMsg = '음성 인식이 중단되었습니다.';
            } else if (event.error === 'audio-capture') {
                errorMsg = '마이크를 찾을 수 없습니다.';
            } else if (event.error === 'network') {
                errorMsg = '네트워크 오류로 음성 인식이 실패했습니다.';
            } else if (event.error === 'not-allowed') {
                errorMsg = '마이크 사용 권한이 거부되었습니다.';
            }
            
            this.speak(errorMsg);
        };
    }
    
    // 음성 인식 시작
    startListening() {
        if (!this.recognition) {
            console.error("음성 인식이 초기화되지 않았습니다.");
            return;
        }
        
        try {
            this.recognition.start();
            this.isListening = true;
            console.log('음성 인식 시작');
        } catch (error) {
            console.error('음성 인식 시작 오류:', error);
        }
    }
    
    // 음성 인식 중지
    stopListening() {
        if (this.recognition && this.isListening) {
            this.recognition.stop();
            this.isListening = false;
        }
    }
    
    // 음성 활성화/비활성화 설정
    setVoiceEnabled(enabled) {
        this.isVoiceEnabled = enabled;
        
        if (!enabled) {
            this.synthesis.cancel();
            this.voiceQueue = [];
            this.isSpeaking = false;
        }
    }
}

// 싱글톤 인스턴스 생성하여 내보내기
const speechService = new SpeechService();
export default speechService;