import os
import xml.etree.ElementTree as ET
import sys

# Windows 콘솔에서 UTF-8 출력 설정
sys.stdout.reconfigure(encoding='utf-8')

# XML 파일이 있는 폴더 경로 (Windows 경로 문제 해결)
xml_folder = "object_detection/2019-01-004.인도보행영상_sample/bbox"

# 모든 클래스 저장할 리스트
class_names = set()

# 폴더 확인
if not os.path.exists(xml_folder):
    print("오류: XML 폴더가 존재하지 않습니다!")
elif not any(file.endswith(".xml") for file in os.listdir(xml_folder)):
    print("오류: XML 파일이 없습니다!")
else:
    # XML 파일 읽어서 클래스 이름 추출
    for xml_file in os.listdir(xml_folder):
        if xml_file.endswith(".xml"):
            tree = ET.parse(os.path.join(xml_folder, xml_file))
            root = tree.getroot()

            # XML 구조 자동 탐색하여 <label> 태그에서 <name> 찾기
            for label in root.findall(".//label"):  
                class_name = label.find("name").text
                class_names.add(class_name)

    # 결과 출력 (UTF-8 인코딩 지원)
    print("클래스 리스트:", list(class_names))