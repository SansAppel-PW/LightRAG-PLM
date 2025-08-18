from pathlib import Path
import nltk
import nltk.tokenize
from loguru import logger
import json

text = nltk.word_tokenize("they refuse to permit us to obtain the refuse permit")
print(text)
# nltk.download(download_dir='C:/Users/houzhimingwx1/download')

# nltk.data.find(r"C:/Users/houzhimingwx1/nltk_data")
nltk.data.path.insert(0, r"C:/Users/houzhimingwx1/nltk_data")
nltk.data.path.append(r"C:/Users/houzhimingwx1/nltk_data")

from unstructured.partition.docx import partition_docx

file_path = Path(r"C:\Users\houzhimingwx1\Documents\01-code\00-hik-yf\Intelligent_QA\PLM2.0\assets\plm_docx\BOM 审核申请.docx").as_posix()

def main():
    from unstructured.staging.base import convert_to_dict
    # print(Path(file_path)/ 'a/b')
    # 版本一：没有图片
    # elements = partition_docx(filename=Path(file_path).as_posix())
    # 版本二：设置extract_image_block_to_payload=True，但结果中没有图片信息
    # elements = partition_docx(filename=Path(file_path).as_posix(), extract_image_block_to_payload=True, infer_table_structure=False)
    elements = partition_docx(filename=Path(file_path).as_posix(),
                              extract_image_block_types=["Image", "Table"],
                              extract_image_block_to_payload=True,
                              extract_image_block_output_dir="images",
                              infer_table_structure=True, strategy="hi_res")
    for element in elements:
        print(f"{element.category}:{element.text}\n")
    dict_data = convert_to_dict(elements)
    logger.info(dict_data)
    with open("unstructured_result_image_table2.json", "w", encoding="utf-8") as f:
        json.dump(dict_data, f, ensure_ascii=False, indent=2)

if __name__=='__main__':
    main()