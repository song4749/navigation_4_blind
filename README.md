# 시각장애인 보행 보조 & 내비게이션
핸드폰 카메라를 통해 장애물을 인식해 회피하도록 경고하고 목적지의 경로를 안내해주는 시각장애인 내비게이션 프로젝트 입니다.

> 웹페이지 링크: [blindnavi.store](blindnavi.store) (현재 비활성화)

> 프로젝트 보고서: https://docs.google.com/presentation/d/1f2KOzjYQMNhHM2csYlrJMZMJuZc30fTd/edit?usp=sharing&ouid=103445310719766259970&rtpof=true&sd=true

> 진행 과정: https://velog.io/@lone4749/%EC%8B%9C%EA%B0%81%EC%9E%A5%EC%95%A0%EC%9D%B8-%EB%82%B4%EB%B9%84%EA%B2%8C%EC%9D%B4%EC%85%98-%EA%B0%9C%EC%9A%94

## 주요 기능
1. 실시간으로 장애물(사람, 자동차 기둥 등)과 점자블록을 인식

2. 이를 통한 각종 위험 상황 음성 알림

3. 실시간 탐지 내비게이션으로 목적지까지의 항상된 경로 안내

<img src="README_images\5.JPG"/>

## 기대 효과
1. 기존의 시작장애인 분들은 흰지팡이와 동반자가 필요한 경우가 많다.<br>
-> 이 프로그램을 통해 흰지팡이와 동반자 없이도 단독 보행이 가능해진다.

2. 기존에는 보행도중 장애물과 출돌할 가능성이 많다.<br>
-> 실시간 장애물 객체인식을 통해 장애물이 있으면 경고해준다.

3. 기존에 잘 알려진 센서들(LiDAR)은 비용이 매우 비싸고 착용하고 다니기에도 불편하다.<br>
-> 누구나 있는 핸드폰과 핸드폰 목걸이를 통하여 사용이 가능하다.

4. 시각장애인 분들은 항상 어디로 가야할경우 사고에 대한 공포감을 가진다.<br>
-> 이 프로그램을 통해 자신감을 얻을수 있다.

<img src="README_images\4.jpg"/>

## 사용법
웹페이지 서버가 비활성화 상태일 경우 로컬로 실행해 볼 수 있습니다.
```bash
# 1. 저장소 클론
git clone https://github.com/song4749/navigation_4_blind.git
cd navigation_4_blind

# 2. 필요 라이브러리 설치
pip install -r requirements.txt

# 3. ONNX 모델 저장 폴더 생성
mkdir onnx_models

# 4. 아래 4개의 onnx 파일을 다운받아서 onnx_models 폴더에 넣으세요

# 5. 프로젝트 루트 디렉토리에 .env 파일을 생성한 뒤, 다음 내용을 입력하세요:
# TMAP_API_KEY=your_tmap_api_key_here
# OPENAI_API_KEY=your_openai_api_key_here

# 6. 실행
uvicorn combined_app:app --reload
```

## 모델 다운로드
[road_segmentation_yolo11seg_small.onnx](https://drive.google.com/file/d/1_QADMybb6H8rwB_GwpaL2ElGS7GjOf7J/view?usp=sharing)

[obstacle_detect_yolo12s.onnx](https://drive.google.com/file/d/1eDx47eYonGOwZOSsqGRQLlL66hdW772K/view?usp=sharing)

[guide_block_yolo11m.onnx](https://drive.google.com/file/d/1Kj10TIexsD7gQ6Mg0vY-ZyunUoxYEpY_/view?usp=sharing)

[depth_anything_v2_vitb.onnx](https://drive.google.com/file/d/1BbAu4-KgKkAY6i8A29X7MWD-LKlGraeE/view?usp=sharing)

## 기술 스택
<img src="README_images\3.JPG"/>

## 시연 이미지
<p align="center">
  <img src="README_images\1.JPG"/>
  <br>
  <em>실시간 탐지 화면</em>
  <br>
  <br>
  <img src="README_images\2.JPG"/>
  <br>
  <em>내비게이션 화면</em>
</p>

## 제작자
송호성, 지승훈