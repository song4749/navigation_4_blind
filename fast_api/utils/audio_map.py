# 경고 문구별 오디오 파일 매핑
warning_audio_map = {
    "Stop sign detected! Please stop.": "정지 블록이 있습니다. 정지하세요.mp3",
    "Pause at the stop block.": "정지 블록 앞에서 잠시 멈추세요.mp3",
    "Pause and decide direction at stop block.": "정지 블록에서 방향을 결정하세요.mp3",
    "Danger Increasing! Be careful! Move RIGHT to avoid obstacle!": "장애물 접근중. 오른쪽으로 피하세요.mp3",
    "Danger Increasing! Be careful! Move LEFT to avoid obstacle!": "장애물 접근중. 왼쪽으로 피하세요.mp3",
    "Turn Left.": "좌회전하세요.mp3",
    "Turn Right.": "우회전하세요.mp3",
    "Off the guide block. Move left.": "점자블록을 벗어나고 있습니다. 왼쪽으로 이동하세요.mp3",
    "Off the guide block. Move right.": "점자블록을 벗어나고 있습니다. 오른쪽으로 이동하세요.mp3",
    "No guide block detected.": "점자블록이 탐지되지 않습니다.mp3",
    "Road detected on the LEFT. Move right to stay on the sidewalk.": "왼쪽차도.mp3",
    "Road detected on the RIGHT. Move left to stay on the sidewalk.": "오른쪽차도.mp3"
}

# 경고 문구 우선순위 정의 (낮을수록 우선)
priority_order = {
    "Stop sign detected! Please stop.": 0,
    "Pause at the stop block.": 1,
    "Pause and decide direction at stop block.": 1,
    "Danger Increasing! Be careful! Move RIGHT to avoid obstacle!": 2,
    "Danger Increasing! Be careful! Move LEFT to avoid obstacle!": 2,
    "Turn Left.": 3,
    "Turn Right.": 3,
    "Off the guide block. Move left.": 4,
    "Off the guide block. Move right.": 4,
    "No guide block detected.": 5,
    "Road detected on the LEFT. Move right to stay on the sidewalk.": 6,
    "Road detected on the RIGHT. Move left to stay on the sidewalk.": 6
}
