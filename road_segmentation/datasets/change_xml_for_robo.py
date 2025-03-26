import xml.etree.ElementTree as ET
from pathlib import Path
import shutil

def convert_cvat_to_pascalvoc(dataset_root: Path):
    xml_files = list(dataset_root.glob("*.xml"))
    if not xml_files:
        print(f"XML 파일 없음: {dataset_root}")
        return
    
    for xml_file in xml_files:
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            if root.tag != "annotations":
                continue

            output_dir = dataset_root.parent / f"{dataset_root.name}_Roboflow_Ready"
            output_dir.mkdir(parents=True, exist_ok=True)
            print(f"변환 중: {dataset_root.name}")

            for image in root.findall("image"):
                filename = image.attrib["name"]
                width = image.attrib["width"]
                height = image.attrib["height"]

                annotation = ET.Element("annotation")
                ET.SubElement(annotation, "folder").text = "images"
                ET.SubElement(annotation, "filename").text = filename

                size = ET.SubElement(annotation, "size")
                ET.SubElement(size, "width").text = width
                ET.SubElement(size, "height").text = height
                ET.SubElement(size, "depth").text = "3"

                for polygon in image.findall("polygon"):
                    label = polygon.attrib["label"]
                    points_str = polygon.attrib["points"]
                    points = [tuple(map(float, pt.split(','))) for pt in points_str.split(';') if pt]

                    obj = ET.SubElement(annotation, "object")
                    ET.SubElement(obj, "name").text = label
                    ET.SubElement(obj, "pose").text = "Unspecified"
                    ET.SubElement(obj, "truncated").text = "0"
                    ET.SubElement(obj, "difficult").text = "0"

                    polygon_tag = ET.SubElement(obj, "polygon")
                    for x, y in points:
                        pt = ET.SubElement(polygon_tag, "pt")
                        ET.SubElement(pt, "x").text = str(int(x))
                        ET.SubElement(pt, "y").text = str(int(y))

                # 이미지 복사
                image_path = next(dataset_root.glob(filename), None)
                if image_path:
                    shutil.copy(image_path, output_dir / filename)

                # XML 저장
                out_xml = output_dir / filename.replace(".jpg", ".xml")
                ET.ElementTree(annotation).write(out_xml)

            print(f"완료: {dataset_root.name}")
        
        except Exception as e:
            print(f"오류 발생 {xml_file.name}: {e}")

# 🧠 상위 루트 폴더에 여러 데이터셋 폴더가 있는 경우
def process_all_datasets(parent_folder: Path):
    for dataset_dir in parent_folder.iterdir():
        if dataset_dir.is_dir():
            convert_cvat_to_pascalvoc(dataset_dir)


for i in range(1, 131):
    parent_path = Path(f"road_segmentation/datasets/Surface_1/Surface_{i:03d}")
    convert_cvat_to_pascalvoc(parent_path)
