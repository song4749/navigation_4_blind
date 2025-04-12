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

        // 확장 기능
        this.autoRecognitionEnabled = false;
        this.confirmationDestinations = [];
        this.currentConfirmationIndex = 0;

        this.initVoices();
    }

    // 음성 합성 초기화
    initVoices() {
        if (this.synthesis.getVoices().length) {
            this.setPreferredVoice();
        }

        this.synthesis.onvoiceschanged = () => {
            this.setPreferredVoice();
        };
    }

    // 선호 음성 설정 (한국어 > 영어 우선)
    setPreferredVoice() {
        const voices = this.synthesis.getVoices();
        const koreanVoice = voices.find(v => /ko/i.test(v.lang));
        const englishVoice = voices.find(v => /en/i.test(v.lang));
        this.preferredVoice = koreanVoice || englishVoice || voices[0];
        console.log(`선택된 음성: ${this.preferredVoice?.name || '없음'}`);
    }

    // 텍스트를 음성으로 말하기
    speak(text, priority = 'normal') {
        if (!this.isVoiceEnabled) return;
        if (!this.synthesis || typeof this.synthesis.speak !== 'function') return;

        console.log(`[음성]: ${text} (${priority})`);

        try {
            if (priority === 'high' && this.isSpeaking) {
                this.synthesis.cancel();
                this.voiceQueue = [];
            }

            this.voiceQueue.push(text);
            if (!this.isSpeaking) this.processVoiceQueue();
        } catch (e) {
            console.error('음성 합성 오류:', e);
        }
    }

    // speak 별칭 (결과 반환 포함)
    speakText(text, priority = 'normal') {
        return this.speak(text, priority);
    }

    // 대기열 처리
    processVoiceQueue() {
        if (this.voiceQueue.length === 0) {
            this.isSpeaking = false;
            return;
        }

        this.isSpeaking = true;
        const text = this.voiceQueue.shift();
        const utterance = new SpeechSynthesisUtterance(text);

        if (this.preferredVoice) utterance.voice = this.preferredVoice;
        utterance.rate = 1.0;
        utterance.pitch = 1.0;
        utterance.volume = 1.0;

        utterance.onend = () => setTimeout(() => this.processVoiceQueue(), 100);
        utterance.onerror = (e) => {
            console.error('음성 오류:', e);
            setTimeout(() => this.processVoiceQueue(), 100);
        };

        this.synthesis.speak(utterance);
    }

    // 음성 인식 초기화
    initSpeechRecognition(callback) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            console.error("이 브라우저는 음성 인식을 지원하지 않습니다.");
            return;
        }

        this.recognition = new SpeechRecognition();
        this.recognition.lang = 'ko-KR';
        this.recognition.continuous = false;
        this.recognition.interimResults = false;

        this.recognition.onresult = (event) => {
            const last = event.results.length - 1;
            const transcript = event.results[last][0].transcript;
            console.log('음성 인식 결과:', transcript);
            if (callback) callback(transcript);
        };

        this.recognition.onend = () => {
            this.isListening = false;
            console.log('음성 인식 종료');
            if (this.autoRecognitionEnabled) {
                setTimeout(() => this.startListening(), 500);
            }
        };

        this.recognition.onerror = (event) => {
            this.isListening = false;
            console.error('음성 인식 오류:', event.error);

            let msg = '음성 인식 중 오류가 발생했습니다.';
            if (event.error === 'no-speech') {
                msg = '음성이 감지되지 않았습니다.';
            } else if (event.error === 'aborted') {
                msg = '음성 인식이 중단되었습니다.';
            } else if (event.error === 'audio-capture') {
                msg = '마이크를 찾을 수 없습니다.';
            } else if (event.error === 'network') {
                msg = '네트워크 오류로 음성 인식이 실패했습니다.';
            } else if (event.error === 'not-allowed') {
                msg = '마이크 사용 권한이 거부되었습니다.';
            }

            this.speak(msg);
        };
    }

    startListening() {
        if (!this.recognition) {
            console.error("음성 인식이 초기화되지 않았습니다.");
            return;
        }

        try {
            this.recognition.start();
            this.isListening = true;
            console.log("음성 인식 시작");
        } catch (e) {
            console.error('음성 인식 시작 오류:', e);
        }
    }

    stopListening() {
        if (this.recognition && this.isListening) {
            this.recognition.stop();
            this.isListening = false;
        }
    }

    // 음성 안내 On/Off
    setVoiceEnabled(enabled) {
        this.isVoiceEnabled = enabled;
        if (!enabled) {
            this.synthesis.cancel();
            this.voiceQueue = [];
            this.isSpeaking = false;
        }
    }

    // 🔁 자동 음성 인식 제어
    enableAutoRecognition() {
        this.autoRecognitionEnabled = true;
        if (!this.isListening && this.recognition) this.startListening();
    }

    disableAutoRecognition() {
        this.autoRecognitionEnabled = false;
    }

    // 🔊 목적지 3개 읽어주기
    readTopDestinations(destinations) {
        if (!Array.isArray(destinations)) {
            console.error("목적지 배열 아님");
            return;
        }

        const topThree = destinations.slice(0, 3);
        let message = "추천 목적지입니다. ";
        topThree.forEach((dest, i) => {
            message += `${i + 1}번: ${dest}. `;
        });
        this.speak(message, 'normal');
    }

    // ❓ 네/아니오로 목적지 선택 받기
    confirmDestinations(destinations, selectionCallback) {
        if (!Array.isArray(destinations) || destinations.length === 0) {
            console.error("확인할 목적지가 없습니다.");
            if (selectionCallback) selectionCallback(null);
            return;
        }

        this.confirmationDestinations = destinations.slice(0, 3);
        this.currentConfirmationIndex = 0;

        const askNext = () => {
            if (this.currentConfirmationIndex >= this.confirmationDestinations.length) {
                this.speak("목적지가 선택되지 않았습니다.", "high");
                if (selectionCallback) selectionCallback(null);
                return;
            }

            const dest = this.confirmationDestinations[this.currentConfirmationIndex];
            this.speak(`제안 ${this.currentConfirmationIndex + 1}: ${dest}. 이 목적지로 선택하시겠습니까? 네 또는 아니오로 대답해주세요.`, "normal");

            this.initSpeechRecognition((transcript) => {
                const answer = transcript.toLowerCase();
                if (answer.includes("네") || answer.includes("예") || answer.includes("좋아") || answer.includes("맞아요")) {
                    this.speak("선택되었습니다.", "normal");
                    if (selectionCallback) selectionCallback(dest);
                } else if (answer.includes("아니") || answer.includes("아니오") || answer.includes("아냐")) {
                    this.currentConfirmationIndex++;
                    askNext();
                } else {
                    this.speak("네 또는 아니오로 대답해주세요.", "normal");
                    askNext();
                }
            });

            this.startListening();
        };

        askNext();
    }
}

// 싱글톤 인스턴스 생성하여 내보내기
const speechService = new SpeechService();
export default speechService;

// === MP3 오디오 큐 (겹침 방지) ===
let mp3Queue = [];
let isMp3Playing = false;

// ✅ 최근 재생된 MP3 기록 (2초 이내 중복 방지)
let recentlyPlayedMp3 = [];

function enqueueMp3(src) {
    const now = Date.now();

    // 2초 이내에 같은 src 재생되었는지 확인
    if (recentlyPlayedMp3.some(item => item.src === src && now - item.timestamp < 2000)) {
        return;
    }

    // 기록 추가
    recentlyPlayedMp3.push({ src, timestamp: now });
    if (recentlyPlayedMp3.length > 10) {
        recentlyPlayedMp3.shift(); // 오래된 것 삭제
    }

    mp3Queue.push({ src, timestamp: now });
    playNextMp3();
}

function playNextMp3() {
    if (isMp3Playing || mp3Queue.length === 0) return;

    const now = Date.now();
    while (mp3Queue.length > 0 && now - mp3Queue[0].timestamp > 2000) {
        mp3Queue.shift(); // 너무 오래된 항목 제거
    }

    if (mp3Queue.length === 0) return;

    const { src } = mp3Queue.shift();
    const audio = new Audio(src);
    isMp3Playing = true;

    audio.addEventListener('ended', () => {
        isMp3Playing = false;
        setTimeout(playNextMp3, 100);
    });

    audio.play().catch(err => {
        console.warn("오디오 재생 실패:", err);
        isMp3Playing = false;
        setTimeout(playNextMp3, 100);
    });
}

// ✅ 전역에서도 사용 가능하도록 등록
window.enqueueMp3 = enqueueMp3;
export { enqueueMp3 };
