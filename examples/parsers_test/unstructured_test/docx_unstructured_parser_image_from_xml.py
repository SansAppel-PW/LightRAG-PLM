"""Test suite for `unstructured.partition.docx` module."""

from __future__ import annotations
from lxml import etree
import hashlib
import io
import os
import pathlib
import re
import tempfile
from typing import Any, Iterator
from loguru import logger
import docx
# import pytest
from docx.document import Document
from docx.text.paragraph import Paragraph
# from pytest_mock import MockFixture

# from test_unstructured.unit_utils import (
#     FixtureRequest,
#     Mock,
#     assert_round_trips_through_JSON,
#     example_doc_path,
#     function_mock,
#     instance_mock,
#     property_mock,
# )
from unstructured.chunking.title import chunk_by_title
from unstructured.documents.elements import (
    Address,
    CompositeElement,
    Element,
    Footer,
    Header,
    Image,
    ListItem,
    NarrativeText,
    PageBreak,
    Table,
    TableChunk,
    Text,
    Title,
)
from unstructured.partition.docx import (
    DocxPartitionerOptions,
    _DocxPartitioner,
    partition_docx,
    register_picture_partitioner,
)
from unstructured.partition.utils.constants import (
    UNSTRUCTURED_INCLUDE_DEBUG_METADATA,
    PartitionStrategy,
)
from unstructured.staging.base import convert_to_dict

docx_path = pathlib.Path(r"C:\Users\houzhimingwx1\Documents\01-code\00-hik-yf\Intelligent_QA\PLM2.0\assets\plm_docx\BOM 审核申请.docx").as_posix()
# docx_path = pathlib.Path(r"C:\Users\houzhimingwx1\Documents\01-code\00-hik-yf\Intelligent_QA\PLM2.0\assets\plm_docx\文档审核.docx").as_posix()

image_id = 0
import uuid

def extract_images_from_xml(xml_str, doc_part, images_dir, image_references, context=""):
    """
    从XML字符串中提取图片并保存
    返回: 图片节点列表
    """
    image_nodes = []
    try:
        if not xml_str or ('<pic:pic' not in xml_str and '<w:drawing>' not in xml_str):
            return image_nodes

        namespaces = {
            'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
            'pic': 'http://schemas.openxmlformats.org/drawingml/2006/picture',
            'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
            'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
        }

        root = etree.fromstring(xml_str)

        # 查找所有图片元素
        for blip in root.findall('.//a:blip', namespaces):
            embed_id = blip.get(f'{{{namespaces["r"]}}}embed')
            if not embed_id:
                continue

            # 获取图片部件
            if embed_id not in doc_part.related_parts:
                logger.warning(f"图片关系 {embed_id} 在 {context} 中未找到")
                continue

            image_part = doc_part.related_parts[embed_id]
            image_data = image_part.blob

            # 确定图片格式
            img_format = "png"  # 默认格式
            if hasattr(image_part, 'content_type'):
                if 'jpeg' in image_part.content_type:
                    img_format = "jpg"
                elif 'gif' in image_part.content_type:
                    img_format = "gif"
                elif 'bmp' in image_part.content_type:
                    img_format = "bmp"
                elif 'png' in image_part.content_type:
                    img_format = "png"
                elif 'svg' in image_part.content_type:
                    img_format = "svg"
                elif 'tiff' in image_part.content_type:
                    img_format = "tiff"

            # 生成唯一图片ID
            image_id = f"img_{uuid.uuid4().hex[:8]}"
            img_filename = f"{image_id}.{img_format}"
            image_path = os.path.join(images_dir, img_filename)

            # 保存图片
            with open(image_path, "wb") as img_file:
                img_file.write(image_data)

            # 获取图片尺寸
            width, height = 0, 0
            try:
                with Image.open(io.BytesIO(image_data)) as img:
                    width, height = img.size
            except Exception as e:
                # 对于SVG等无法直接获取尺寸的图片格式，跳过尺寸获取
                pass

            # 创建图片节点
            image_node = {
                "type": "image",
                "url": f"images/{img_filename}",
                "format": img_format,
                "width": width,
                "height": height,
                "size": f"{len(image_data) / 1024:.2f} KB",
                "context": context
            }

            # 记录图片信息
            image_references[image_id] = image_node
            image_nodes.append(image_node)

    except Exception as e:
        logger.error(f"从XML提取图片失败: {e}")

    return image_nodes


def extract_paragraph_images(para, images_dir, image_references):
    """提取段落中的图片并返回图片节点列表"""
    image_nodes = []
    # context = f"段落: {clean_text(para.text[:20])}..." if para.text else "段落"
    context = f"段落: {para.text[:20]}..." if para.text else "段落"

    for run_idx, run in enumerate(para.runs):
        if run._element and run._element.xml:
            try:
                # 提取该运行中的图片
                images = extract_images_from_xml(
                    run._element.xml,
                    para.part,
                    images_dir,
                    image_references,
                    f"{context} (运行 {run_idx})"
                )
                if images:
                    image_nodes.extend(images)
            except Exception as e:
                logger.error(f"提取段落图片失败: {e}")

    return image_nodes


def test_partition_docx_uses_registered_picture_partitioner():
    class FakeParagraphPicturePartitioner:
        @classmethod
        def iter_elements(
            cls, paragraph: Paragraph, opts: DocxPartitionerOptions) -> Iterator[Image]:
            call_hash = hashlib.sha1(f"{paragraph.text}{opts.strategy}".encode()).hexdigest()
            # print(f'PicturePartitioner Paragraph Text: {paragraph.text}')
            output_folder = "images_pw_bom_v1"
            os.makedirs(output_folder, exist_ok=True)
            images_info = []
            image_references = {}
            image_nodes = extract_paragraph_images(paragraph, output_folder, image_references)
            print('--------------------')
            print(len(image_nodes))
            if len(image_nodes)>0:
                yield Image(f"Images: {len(image_nodes)}")

            # return images_info

            # yield Image(f"Image with hash {call_hash}, strategy: {opts.strategy}")
        # @classmethod  #<docx.text.paragraph.Paragraph object at 0x000001DCF0E60E90>
        # def iter_elements(cls, picture: Picture, opts: PptxPartitionerOptions) -> Iterator[Element]:
        #     image_hash = hashlib.sha1(picture.image.blob).hexdigest()
        #     yield Image(f"Image with hash {image_hash}, strategy: {opts.strategy}")

    register_picture_partitioner(FakeParagraphPicturePartitioner)

    # elements = partition_docx(example_doc_path("contains-pictures.docx"))
    elements = partition_docx(docx_path, strategy=PartitionStrategy.HI_RES)

    # -- picture-partitioner registration has module-lifetime, so need to de-register this fake
    # -- so other tests in same test-run don't use it
    DocxPartitionerOptions._PicturePartitionerCls = None

    # assert len(elements) == 11
    # image_elements = [e for e in elements if isinstance(e, Image)]
    # assert len(image_elements) == 6
    # assert [e.text for e in image_elements] == [
    #     "Image with hash 429de54e71f1f0fb395b6f6191961a3ea1b64dc0, strategy: hi_res",
    #     "Image with hash 5e0cd2c62809377d8ce7422d8ca6b0cf5f4453bc, strategy: hi_res",
    #     "Image with hash 429de54e71f1f0fb395b6f6191961a3ea1b64dc0, strategy: hi_res",
    #     "Image with hash ccbd34be6096544babc391890cb0849c24cc046c, strategy: hi_res",
    #     "Image with hash a41b819c7b4a9750ec0f9198c59c2057d39c653c, strategy: hi_res",
    #     "Image with hash ba0dc2a1205af8f6d9e06c8d415df096b0a9c428, strategy: hi_res",
    # ]
    from loguru import logger
    import json
    dict_data = convert_to_dict(elements)
    # logger.info(dict_data)
    with open(pathlib.Path(docx_path).stem + '.json', "w", encoding="utf-8") as f:
        json.dump(dict_data, f, ensure_ascii=False, indent=2)
    image_elements = [e for e in elements if isinstance(e, Image)]
    logger.info(f"Image Element:{len(image_elements)}")

if __name__=="__main__":
    test_partition_docx_uses_registered_picture_partitioner()