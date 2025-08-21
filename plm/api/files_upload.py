import asyncio
import io
import os
from pathlib import Path

import mammoth
from fastapi import APIRouter, UploadFile, File, Depends
from loguru import logger

from lightrag.kg.shared_storage import initialize_pipeline_status
from plm.core.rag import init_rag
from plm.utils.parser.docx_parser import DocxParser
from plm.deepdoc.docx_parser import do_parse
from plm.conf.settings import file_settings
from plm.utils.schema import UploadResponse

router = APIRouter()

doc_suffixes = [".docx", ".doc", ".pdf"]
image_suffixes = [".png", ".jpeg", ".jpg", ".webp", ".gif"]


@router.post(path="/files")
async def upload_files(file_name: str, file: UploadFile=File(...)):
    # , method, backend, lang, server_url,
    # # start_page_id, end_page_id, table_enable,
    # device_mode, virtual_vram, model_source, ** kwargs

    # Check file type...
    if Path(file.filename).suffix not in doc_suffixes:
        logger.error('File type must be docx...')
        return

    doc_contents = await file.read()

    image_idx = 1
    doc_dir_name = file_name
    html_name = file_name
    output_dir_path = Path(Path(file_settings.FILE_PARSE_OUTPUT_PATH) / doc_dir_name).as_posix()
    images_dir_path = Path(output_dir_path) / "images"
    output_html_file_path = Path(Path(output_dir_path) / f"{html_name}.html").as_posix()
    # 创建 images 目录
    os.makedirs(output_dir_path, exist_ok=True)
    os.makedirs(images_dir_path, exist_ok=True)

    logger.info(f'Running Upload Pipeline...')

    def convert_image(image):
        nonlocal image_idx
        with image.open() as image_bytes:

            # 生成文件名
            ext = image.content_type.split('/')[-1]
            cur_image_id = image_idx
            image_abs_name = Path(images_dir_path / f"image_{cur_image_id:02d}.{ext}").as_posix()
            image_idx += 1
            # with open(image_abs_name, "wb") as f:
            #     f.write(image_bytes.read())
            # Asyncio save images
            asyncio.create_task(asyncio.to_thread(lambda: open(image_abs_name, "wb").write(image_bytes.read())))
            return {"src": f"images/image_{cur_image_id:02d}.{ext}"}
    logger.info(f'Running mammoth parse...')
    result = mammoth.convert_to_html(
        io.BytesIO(doc_contents),
        convert_image=mammoth.images.img_element(convert_image)
    )

    prefix = """
            <!DOCTYPE html>
            <html lang="zh-CN">
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
    html_text = prefix + result.value + subfix

    # with open(output_html_file_path, "w", encoding="utf-8") as html_file:
    #     html_file.write(html_text)

    # Asyncio save html
    asyncio.create_task(asyncio.to_thread(lambda: open(output_html_file_path, "w", encoding="utf-8").write(html_text)))


    logger.info(f'Docx Parse Result: {html_text}')

    # Initialize RAG
    rag = init_rag()
    # Initialize database connections
    await rag.initialize_storages()
    await initialize_pipeline_status()
    MAGIC_SPLIT_STR = "\n↔\n"
    # rag_ainsert_reponse = await rag.ainsert(input=html_text,
    #                                         split_by_character=MAGIC_SPLIT_STR,
    #                                         split_by_character_only=False,
    #                                         ids=None,
    #                                         file_paths=str(output_html_file_path)
    #                                         )
    # logger.info(f'RAG ainsert Response: {rag_ainsert_reponse}')
    # asyncio.run(rag.query(query=text, param=QueryParam(mode="naive")))
    asyncio.create_task(rag.ainsert(input=html_text,
                split_by_character=MAGIC_SPLIT_STR,
                split_by_character_only=False,
                ids=None,
                file_paths=str(output_html_file_path)
                ))
    return UploadResponse()

if __name__ == '__main__':
    docx_path = r'C:\Users\houzhimingwx1\Documents\01-code\00-hik-yf\Intelligent_QA\PLM2.0\assets\plm_docx\BOM 审核申请.docx'
    asyncio.run(upload_files(input_path=docx_path, output_dir=Path(docx_path).parent))
