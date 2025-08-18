import os
from pathlib import Path

from docx import Document
from io import BytesIO
from PIL import Image  # 需要安装: pip install pillow

docx_path = Path(r"C:\Users\houzhimingwx1\Documents\01-code\00-hik-yf\Intelligent_QA\PLM2.0\assets\plm_docx\BOM 审核申请.docx").as_posix()

def extract_images(doc, save_folder="extracted_images"):
    """
    提取文档中的所有图片并保存
    """
    os.makedirs(save_folder, exist_ok=True)
    image_count = 0

    for rel in doc.part.rels.values():
        if "image" in rel.reltype:
            image_count += 1
            image_blob = rel._target.part.blob
            image_ext = rel.target_ref.split('.')[-1].lower()  # 获取扩展名
            image_name = f"image_{image_count}.{image_ext}"

            image_path = os.path.join(save_folder, image_name)
            with open(image_path, 'wb') as f:
                f.write(image_blob)

            # 可选：使用 PIL 打印图片信息
            try:
                img = Image.open(BytesIO(image_blob))
                print(f"已保存图片: {image_path} ({img.size[0]}x{img.size[1]})")
            except:
                print(f"已保存图片: {image_path} (无法读取尺寸)")

    return image_count
import json
# 使用示例
doc = Document(docx_path)
print(doc)
# with open("output.json", "w", encoding="utf-8") as f:
#     json.dump(doc, f, ensure_ascii=False, indent=4)
# import pickle
#
# # 保存整个 Document 对象
# with open("doc.pickle", "wb") as f:
#     pickle.dump(doc, f)
# doc.save('python_docx_result.docx')
# # 读取
# with open("doc.pickle", "rb") as f:
#     doc = pickle.load(f)
# 尝试序列化
# import dill
# try:
#     with open("doc.dill", "wb") as f:
#         dill.dump(doc, f)
# except Exception as e:
#     print("仍然失败:", e)


# count = extract_images(doc, "images")
# print(f"共提取 {count} 张图片")
