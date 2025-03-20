import os
import xml.etree.ElementTree as ET

# 데이터셋 기본 경로
base_path = r"object_detection\datasets\Bbox_1_new"

# 1부터 150까지 반복
for i in range(1, 151):
    folder_name = f"Bbox_{i:04d}"  # Bbox_0001 ~ Bbox_0150
    input_folder = os.path.join(base_path, folder_name)
    output_folder = os.path.join(input_folder, "changed_xml")

    # 📌 폴더가 없으면 스킵
    if not os.path.exists(input_folder):
        print(f"경고: {input_folder} 폴더가 없습니다. 스킵합니다.")
        continue

    # 📁 변환된 XML 저장 폴더 생성
    os.makedirs(output_folder, exist_ok=True)

    # 폴더 내 모든 XML 파일 찾기
    xml_files = [f for f in os.listdir(input_folder) if f.endswith(".xml")]

    # XML 변환 실행
    for xml_file in xml_files:
        xml_path = os.path.join(input_folder, xml_file)

        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            for image in root.findall("image"):
                filename = image.get("name")  # 이미지 파일명
                img_width = image.get("width")
                img_height = image.get("height")

                # 새로운 Pascal VOC 형식 XML 만들기
                annotation = ET.Element("annotation")
                ET.SubElement(annotation, "folder").text = "images"
                ET.SubElement(annotation, "filename").text = filename

                size = ET.SubElement(annotation, "size")
                ET.SubElement(size, "width").text = img_width
                ET.SubElement(size, "height").text = img_height
                ET.SubElement(size, "depth").text = "3"  # 기본값 (RGB 이미지)

                # 바운딩 박스 변환
                for box in image.findall("box"):
                    obj = ET.SubElement(annotation, "object")
                    ET.SubElement(obj, "name").text = box.get("label")

                    bndbox = ET.SubElement(obj, "bndbox")
                    ET.SubElement(bndbox, "xmin").text = str(int(float(box.get("xtl"))))
                    ET.SubElement(bndbox, "ymin").text = str(int(float(box.get("ytl"))))
                    ET.SubElement(bndbox, "xmax").text = str(int(float(box.get("xbr"))))
                    ET.SubElement(bndbox, "ymax").text = str(int(float(box.get("ybr"))))

                # 변환된 XML 저장
                output_xml_path = os.path.join(output_folder, filename.replace(".jpg", ".xml"))
                tree = ET.ElementTree(annotation)
                tree.write(output_xml_path)

            print(f"{xml_file} 변환 완료! → {output_folder}")

        except Exception as e:
            print(f"{xml_file} 변환 중 오류 발생: {e}")

print("모든 폴더에서 XML 변환이 완료되었습니다!")
