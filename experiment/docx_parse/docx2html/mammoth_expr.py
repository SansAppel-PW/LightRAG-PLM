import os
from pathlib import Path

import mammoth

docx_dir = r"C:\Users\houzhimingwx1\Documents\01-code\00-hik-yf\Intelligent_QA\PLM2.0\assets\plm_docx"
method = "mammoth"
output_path = r"C:\Users\houzhimingwx1\Documents\01-code\00-hik-yf\Intelligent_QA\PLM2.0\experiment\output"

doc_suffixes = ['.docx']
output_file_ext = ".html"


def get_abs_image_name(doc_name, image_idx, ext):
    return (Path(output_path) / method / doc_name / "images" / f"image_{image_idx:02d}.{ext}").as_posix()


def get_rel_image_name(doc_name, image_idx, ext):
    return f"images/image_{image_idx:02d}.{ext}"


def get_output_file_name(doc_name):
    return (Path(output_path) / method / doc_name / f"{doc_name}{output_file_ext}").as_posix()


def get_output_html_file_name(doc_name):
    return (Path(output_path) / method / doc_name / f"{doc_name}_final{output_file_ext}").as_posix()


def get_output_dir(doc_name):
    return (Path(output_path) / method / doc_name / "images").as_posix()


def do_parse(doc_path: str):
    image_idx = 1
    doc_name = Path(doc_path).stem
    output_dir = get_output_dir(doc_name)

    def convert_image(image):
        nonlocal image_idx
        with image.open() as image_bytes:
            # 创建 images 目录
            os.makedirs(output_dir, exist_ok=True)
            # 生成文件名
            ext = image.content_type.split('/')[-1]
            image_abs_name = get_abs_image_name(doc_name, image_idx, ext)
            image_idx += 1
            with open(image_abs_name, "wb") as f:
                f.write(image_bytes.read())
            return {"src": get_rel_image_name(doc_name, image_idx, ext)}

    with open(doc_path, "rb") as docx_file:
        result = mammoth.convert_to_html(
            docx_file,
            convert_image=mammoth.images.img_element(convert_image)
        )

    html = result.value

    with open(get_output_file_name(doc_name), "w", encoding="utf-8") as html_file:
        html_file.write(html)

    prefix = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="UTF-8">
          <title>Title</title>
        </head>
        <body>
    """
    subfix = """
        </body>
    </html>
    """

    html = prefix + html.replace("<table>", "<table border='1px' cellspacing='0'>") + subfix

    with open(get_output_html_file_name(doc_name), "w", encoding="utf-8") as html_file:
        html_file.write(html)


def load_docs(sources_dir):
    doc_path_list = []
    for doc_path in Path(docx_dir).glob('*'):
        doc_path = Path(doc_path.as_posix())  # windows path covert '\' to '/'
        # if doc_path.suffix in doc_suffixes + image_suffixes:
        if doc_path.suffix in doc_suffixes:
            # do_parse(doc_path)
            doc_path_list.append(doc_path)
    return doc_path_list


def main():
    doc_path_list = load_docs(docx_dir)
    for doc_path in doc_path_list:
        os.makedirs(Path(output_path) / method / Path(doc_path).stem, exist_ok=True)
        do_parse(doc_path)


if __name__ == '__main__':
    main()
