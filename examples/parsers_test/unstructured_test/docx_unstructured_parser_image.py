"""Test suite for `unstructured.partition.docx` module."""

from __future__ import annotations

import hashlib
import io
import os
import pathlib
import re
import tempfile
from typing import Any, Iterator

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

docx_path = pathlib.Path(r"C:\Users\houzhimingwx1\Documents\01-code\00-hik-yf\Intelligent_QA\PLM2.0\assets\plm_docx\文档审核.docx").as_posix()

def test_partition_docx_uses_registered_picture_partitioner():
    class FakeParagraphPicturePartitioner:
        @classmethod
        def iter_elements(
            cls, paragraph: Paragraph, opts: DocxPartitionerOptions
        , count=0) -> Iterator[Image]:
            call_hash = hashlib.sha1(f"{paragraph.text}{opts.strategy}".encode()).hexdigest()
            # print(f'PicturePartitioner Paragraph Text: {paragraph.text}')
            output_folder = "images_small_v1"
            os.makedirs(output_folder, exist_ok=True)
            images_info = []
            for rel in paragraph.part.rels.values():
                if "image" in rel.reltype:
                    blob = rel.target_part.blob
                    image_ext = rel.target_ref.split('.')[-1].lower()
                    if image_ext not in ['png', 'jpg', 'jpeg', 'gif', 'bmp']:
                        image_ext = 'png'

                    # 使用 BytesIO 加载图片以获取信息
                    img_data = io.BytesIO(blob)
                    try:
                        from PIL import Image as PILImage
                        pil_img = PILImage.open(img_data)
                        width, height = pil_img.size
                        mode = pil_img.mode  # RGB, RGBA, etc.
                        img_data.seek(0)  # 重置指针
                    except Exception as e:
                        width, height, mode = None, None, None
                        print(f"⚠️ 无法读取图片信息: {e}")

                    # 保存图片
                    # filename = f"image_{len(images_info) + 1}.{image_ext}"
                    filename = pathlib.Path(rel.target_ref).name
                    path = os.path.join(output_folder, filename)
                    with open(path, 'wb') as f:
                        f.write(blob)

                    images_info.append({
                        "filename": filename,
                        "path": path,
                        "size_bytes": len(blob),
                        "width": width,
                        "height": height,
                        "mode": mode,
                        "format": image_ext.upper()
                    })
                    print(f"Image name: {filename}, Image path: {path}, Image byte size: {len(blob)}")
                    # yield Image(f"Image path: {path}, Image name: {filename}, Image byte size: {len(blob)}")
            count+=1
            print('------------------------')
            print(count)
            yield Image(f"Images: {len(images_info)}")

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
    with open("文档审核_v1.json", "w", encoding="utf-8") as f:
        json.dump(dict_data, f, ensure_ascii=False, indent=2)
    image_elements = [e for e in elements if isinstance(e, Image)]
    logger.info(f"Image Element:{len(image_elements)}")

if __name__=="__main__":
    test_partition_docx_uses_registered_picture_partitioner()