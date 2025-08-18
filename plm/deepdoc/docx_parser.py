import io
import json
import os
import re
from datetime import datetime
from pathlib import Path

import click
from click.testing import CliRunner
from loguru import logger

from plm.deepdoc.parser.document_parser import parse_docx_with_path
from plm.deepdoc.processor.text_processor import process_document_to_text
from plm.utils.connect.minio_conn import PLMMinio
from plm.utils.file.file_utils import prepare_env
from plm.utils.file.filebase import FileBasedDataWriter
from plm.version import __version__
from plm.conf.settings import  rep_settings

# 添加src目录到Python路径

# doc_suffixes = [".docx", ".doc", ".pdf"]
doc_suffixes = [".docx"]
image_suffixes = [".png", ".jpeg", ".jpg", ".webp", ".gif"]

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
    help='local filepath or directory. support pdf, png, jpg, jpeg files',
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
    help="""the method for parsing pdf:
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
    '-f',
    '--image',
    'image_enable',
    type=bool,
    help='Enable image parsing. Default is True. Adapted only for the case where the backend is set to "pipeline".',
    default=True,
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
def plm_docx_parse(cxt,
                   input_path, output_dir, method, backend, lang, server_url,
                   start_page_id, end_page_id, image_enable, table_enable,
                   device_mode, virtual_vram, model_source, **kwargs):

    if os.path.isdir(input_path):
        doc_path_list = []
        for doc_path in Path(input_path).glob('*'):
            doc_path = Path(doc_path.as_posix()) # windows path covert '\' to '/'
            # if doc_path.suffix in doc_suffixes + image_suffixes:
            if doc_path.suffix in doc_suffixes:
                doc_path_list.append(doc_path)
        do_parse(Path(output_dir).as_posix(), doc_path_list)
    else:
        docx_path = Path(input_path).as_posix()
        do_parse(Path(output_dir).as_posix(), [Path(docx_path)])


def do_parse(output_dir,
             docx_file_paths: list[Path],
             docx_bytes_list: list[bytes] = None,
             docx_file_names: list[str] = None,
             d_lang_list: list[str] = None,
             backend="pipeline",
             parse_method="python_docx",
             image_enable=True,
             table_enable=True,
             server_url=None,
             start_page_id=0,
             end_page_id=None,
             **kwargs,
             ):
    # 准备汇总数据
    all_documents = []
    failed_files = []
    # skipped_files = []
    processed_count = 0
    for file_path in docx_file_paths:
        # 从文件名提取文档名称
        # doc_name = safe_filename(file_path.stem) # 考虑需要用文件名加载解析结果，所以使用原始文件名
        doc_name = file_path.stem
        local_image_dir, local_md_output_dir = prepare_env(output_dir, doc_name, parse_method)
        image_writer, md_output_writer = FileBasedDataWriter(local_image_dir), FileBasedDataWriter(local_md_output_dir)
        # 解析文档（使用快速模式）
        document_structure = parse_docx_with_path(str(file_path), local_md_output_dir, quick_mode=True)
        processed_count+=1
        if document_structure:
            # save json result
            json_path = local_md_output_dir/ "document.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(document_structure, f, ensure_ascii=False, indent=2)

            # 处理为标准化文本格式
            processed_text = process_document_to_text(document_structure, doc_name)

            # 保存处理后的文本
            text_path = local_md_output_dir / "processed_text.txt"
            with open(text_path, "w", encoding="utf-8") as f:
                f.write(processed_text)

            # 上传图片并将图片信息保存到Minio
            upload_images(doc_name, processed_text)

            # 统计信息
            total_images = len(document_structure.get("images", {}))
            processing_info = document_structure.get("processing_info", {})
            warnings = len(processing_info.get("warnings", []))
            errors = len(processing_info.get("errors", []))

            logger.info(f"文件处理完成!")
            logger.info(f"输出位置: {local_md_output_dir}, 图片数量: {total_images}, 警告数量: {warnings}, 错误数量: {errors}")

            if warnings > 0 or errors > 0:
                logger.info("详细的警告和错误信息请查看 document.json 文件")

            # 添加到汇总列表
            all_documents.append({
                "file": doc_name,
                "path": str(json_path),
                "status": "success",
                "images_found": len(document_structure.get("images", {})),
                "warnings": len(document_structure.get("processing_info", {}).get("warnings", [])),
                "errors": len(document_structure.get("processing_info", {}).get("errors", []))
            })

            # 统计图片数量
            total_images = len(document_structure.get("images", {}))
            hf_images = len(document_structure.get("header_footer_images", []))
            processing_info = document_structure.get("processing_info", {})

            logger.info(f"文件 {doc_name} 处理完成 - 图片: {total_images}, 页眉页脚图片: {hf_images}, 警告: {len(processing_info.get('warnings', []))}")
        else:
            # Failed parsing
            failed_files.append(doc_name)
            logger.error(f"Failed to Parse the File: {doc_name}")
            if errors :=document_structure.get("processing_info", {}).get("errors"):
                logger.error(f"File Parsing Error: {doc_name} - {errors}")

        # 保存汇总信息
        summary_path = local_md_output_dir / "summary.json"
        summary_data = {
            "input_folder": str(file_path.parent),
            "processing_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_files": len(docx_file_paths),
            "processed": processed_count,
            "failed": len(failed_files),
            # "skipped": len(skipped_files),
            "failed_files": failed_files,
            # "skipped_files": skipped_files,
            "documents": all_documents,
            "success_rate": f"{processed_count / len(docx_file_paths) * 100:.1f}%" if docx_file_paths else "0%"
        }

        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, ensure_ascii=False, indent=2)

        logger.info(f"汇总信息保存在 {summary_path}")

        # 打印处理结果
        logger.info(f"批量处理完成!")
        logger.info(f"成功处理: {processed_count}/{len(docx_file_paths)} 个文件 ({processed_count / len(docx_file_paths) * 100:.1f}%)")

def upload_images(doc_name, text):



    images_path_list = re.findall(r"<Image[^>]*>(.*?)</Image>", text, re.DOTALL)
    logger.info(f'images: {images_path_list}')

    minio_object_names = []
    for image_idx, image_path in enumerate(images_path_list):
        # upload minio
        # upload to minio
        image_path = Path(image_path)
        minio_object_name = f"{doc_name}/{image_idx}.{image_path.suffix}"
        # with open(image_path, 'rb') as file:
        #     image_bytes = file.read()
        # f_stream = io.BytesIO(image_bytes)
        # f_stream.seek(0)
        minio_client = PLMMinio()
        minio_client.fput(bucket=rep_settings.MINIO_BUCKET, file_name=minio_object_name,
                                   file_path=str(image_path))
        logger.info(f'MINIO IMAGE UPLOAD: {image_path}')
        minio_object_names.append(minio_object_name)



if __name__ == "__main__":
    input_path = Path(r"C:\Users\houzhimingwx1\Documents\01-code\00-hik-yf\Intelligent_QA\PLM2.0\assets\plm_docx").as_posix()
    output_dir = Path(r"C:\Users\houzhimingwx1\Documents\01-code\00-hik-yf\Intelligent_QA\PLM2.0\examples\pw_parser_test_output_v3").as_posix()
    CliRunner().invoke(plm_docx_parse, ['-p', input_path, '-o', output_dir])
