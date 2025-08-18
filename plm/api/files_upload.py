import asyncio
from pathlib import Path

from fastapi import APIRouter
from loguru import logger

from lightrag.kg.shared_storage import initialize_pipeline_status
from plm.core.rag import init_rag
from plm.utils.parser.docx_parser import DocxParser, do_parse

router = APIRouter()

doc_suffixes = [".docx", ".doc", ".pdf"]
image_suffixes = [".png", ".jpeg", ".jpg", ".webp", ".gif"]


@router.post(path="/files")
async def upload_files(input_path, output_dir):
    # , method, backend, lang, server_url,
    # # start_page_id, end_page_id, table_enable,
    # device_mode, virtual_vram, model_source, ** kwargs
    logger.info(f'Running Upload Pipeline...')
    logger.info(f'Current Processing File Path: {input_path}')
    logger.info(f'Output Save Path: {output_dir}')

    """ docx parse with python_docx """

    # def parse_docx():
    #     text = DocxParser()(fnm=input_path)
    #     return text

    def parse_doc(output_dir,
                  docx_file_paths: list[str]=None,
                  backend="pipeline",
                  lang = "ch", # ['ch', 'ch_server', 'ch_lite', 'en', 'korean', 'japan', 'chinese_cht', 'ta', 'te', 'ka', 'latin', 'arabic', 'east_slavic', 'cyrillic', 'devanagari']
                  parse_method="auto",
                  image_enable=True,
                  table_enable=True,
                  server_url=None,
                  start_page_id=0,
                  end_page_id=None,
                  **kwargs,
             ):
        try:
            docx_file_names = []
            docx_bytes_list = []
            lang_list = []
            for path in docx_file_paths:
                file_name = str(Path(path).stem)
                docx_file_names.append(file_name)
                lang_list.append(lang)
            do_parse(
                output_dir=output_dir,
                docx_file_paths = docx_file_paths,
                docx_bytes_list = docx_bytes_list,
                docx_file_names=docx_file_names,
                d_lang_list=lang_list,
                parse_method=parse_method,
                image_enable=image_enable,
                table_enable=table_enable,
                server_url=server_url,
                start_page_id=start_page_id,
                end_page_id=end_page_id,
                **kwargs,
            )
        except Exception as e:
            logger.exception(e)


    text = "test rag flow 2"
    logger.info(f'Docx Parse Result: {text}')

    # Initialize RAG
    rag = init_rag()
    # Initialize database connections
    await rag.initialize_storages()
    await initialize_pipeline_status()
    MAGIC_SPLIT_STR = "\n↔\n"
    rag_ainsert_reponse = await rag.ainsert(input=text,
                                            split_by_character=MAGIC_SPLIT_STR,
                                            split_by_character_only=False,
                                            ids=None,
                                            file_paths=input_path
                                            )
    logger.info(f'RAG ainsert Response: {rag_ainsert_reponse}')
    # asyncio.run(rag.query(query=text, param=QueryParam(mode="naive")))


if __name__ == '__main__':
    docx_path = r'C:\Users\houzhimingwx1\Documents\01-code\00-hik-yf\Intelligent_QA\PLM2.0\assets\plm_docx\BOM 审核申请.docx'
    asyncio.run(upload_files(input_path=docx_path, output_dir=Path(docx_path).parent))
