import asyncio
import warnings
from pathlib import Path

from loguru import logger
from click.testing import CliRunner
import asyncclick as click
from plm.version import __version__
from plm.utils.parser.docx_parser import DocxParser
from plm.core.rag import init_rag
from lightrag import QueryParam


@click.command(context_settings=dict(ignore_unknown_options=True, allow_extra_args=True))
@click.pass_context
@click.version_option(__version__,
                      '--version',
                      '-v',
                      help='display the version and exit')
@click.option(
    '-p',
    '--path',
    'input_path',
    type=click.Path(exists=True),
    required=True,
    help='local filepath or directory. support docx, pdf, png, jpg, jpeg files',
)
@click.option(
    '-o',
    '--output',
    'output_dir',
    type=click.Path(),
    required=True,
    help='output local directory',
)
@click.option(
    '-m',
    '--method',
    'method',
    type=click.Choice(['auto', 'txt', 'ocr']),
    help="""the method for parsing docx:
    auto: Automatically determine the method based on the file type.
    txt: Use text extraction method.
    ocr: Use OCR method for image-based PDFs.
    Without method specified, 'auto' will be used by default.
    Adapted only for the case where the backend is set to "pipeline".""",
    default='auto',
)
@click.option(
    '-b',
    '--backend',
    'backend',
    type=click.Choice(['pipeline', 'vlm-transformers', 'vlm-sglang-engine', 'vlm-sglang-client']),
    help="""the backend for parsing pdf:
    pipeline: More general.
    vlm-transformers: More general.
    vlm-sglang-engine: Faster(engine).
    vlm-sglang-client: Faster(client).
    without method specified, pipeline will be used by default.""",
    default='pipeline',
)
@click.option(
    '-l',
    '--lang',
    'lang',
    type=click.Choice(['ch', 'ch_server', 'ch_lite', 'en', 'korean', 'japan', 'chinese_cht', 'ta', 'te', 'ka',
                       'latin', 'arabic', 'east_slavic', 'cyrillic', 'devanagari']),
    help="""
    Input the languages in the pdf (if known) to improve OCR accuracy.  Optional.
    Without languages specified, 'ch' will be used by default.
    Adapted only for the case where the backend is set to "pipeline".
    """,
    default='ch',
)
@click.option(
    '-u',
    '--url',
    'server_url',
    type=str,
    help="""
    When the backend is `sglang-client`, you need to specify the server_url, for example:`http://127.0.0.1:30000`
    """,
    default=None,
)
@click.option(
    '-s',
    '--start',
    'start_page_id',
    type=int,
    help='The starting page for PDF parsing, beginning from 0.',
    default=0,
)
@click.option(
    '-e',
    '--end',
    'end_page_id',
    type=int,
    help='The ending page for PDF parsing, beginning from 0.',
    default=None,
)
@click.option(
    '-t',
    '--table',
    'table_enable',
    type=bool,
    help='Enable table parsing. Default is True. Adapted only for the case where the backend is set to "pipeline".',
    default=True,
)
@click.option(
    '-d',
    '--device',
    'device_mode',
    type=str,
    help='Device mode for model inference, e.g., "cpu", "cuda", "cuda:0", "npu", "npu:0", "mps". Adapted only for the case where the backend is set to "pipeline". ',
    default=None,
)
@click.option(
    '--vram',
    'virtual_vram',
    type=int,
    help='Upper limit of GPU memory occupied by a single process. Adapted only for the case where the backend is set to "pipeline". ',
    default=None,
)
@click.option(
    '--source',
    'model_source',
    type=click.Choice(['huggingface', 'modelscope', 'local']),
    help="""
    The source of the model repository. Default is 'huggingface'.
    """,
    default='huggingface',
)
def upload_files(ctx,
                 input_path, output_dir, method, backend, lang, server_url,
                 #start_page_id, end_page_id, table_enable,
                 device_mode, virtual_vram, model_source, **kwargs):
    logger.info(f'Running Upload Pipeline...')
    logger.info(f'Current Processing File Path: {input_path}')
    logger.info(f'Output Save Path: {output_dir}')
    # 有问题：click.command装饰的函数中调用 asyncio.run 异步函数有问题：error:cannot perform operation: another operation is in progress
    # 有问题：asyncclick.command装饰的函数测试没有成功
    """ docx parse with python_docx """
    # text = DocxParser()(fnm=input_path)
    text = "test rag flow 2"
    logger.info(f'Docx Parse Result: {text}')

    rag = init_rag()
    # Initialize database connections
    asyncio.run(rag.initialize_storages())
    MAGIC_SPLIT_STR = "\n↔\n"
    # asyncio.run(rag.ainsert(input=text,split_by_character=MAGIC_SPLIT_STR,split_by_character_only=False,ids=None,file_paths=input_path))
    asyncio.run(rag.ainsert(input=text,split_by_character=MAGIC_SPLIT_STR,split_by_character_only=False,ids=None,file_paths=input_path))
    asyncio.run(rag.query(query=text, param=QueryParam(mode="naive")))
    # print(result)
    # <class 'asyncpg.exceptions._base.InterfaceError'>
    # InterfaceError('cannot perform operation: another operation is in progress')
    """
        PostgreSQL database, error:'NoneType' object has no attribute 'send'
        PostgreSQL database,
        sql:SELECT id FROM LIGHTRAG_DOC_STATUS WHERE workspace=$1 AND id IN ('doc-39d40058d376e14613c3229100f4748d'),
        params:{'workspace': 'default'},
        error:cannot perform operation: another operation is in progress

    """




if __name__ == '__main__':
    docx_path = r'C:\Users\houzhimingwx1\Documents\01-code\00-hik-yf\Intelligent_QA\PLM2.0\assets\plm_docx\BOM 审核申请.docx'
    result = CliRunner().invoke(upload_files, ['-p', docx_path, '-o', Path(docx_path).parent])
    assert result.exit_code == 0
    # asyncio.run(upload_files(input_path=docx_path, output_dir=Path(docx_path).parent))
