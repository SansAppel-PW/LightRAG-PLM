#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
extract_docx_with_context.py
----------------------------
从 .docx 中提取所有图片并关联其前后文字上下文，适用于构建 RAG 知识库。

依赖:
    pip install python-docx lxml pillow tqdm
"""

from pathlib import Path
from typing import List, Dict, Any
import base64
import json

from docx import Document
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from lxml import etree
from tqdm import tqdm
from PIL import Image
import io


# -------------------------------------------------------------
# 辅助函数：把图片二进制保存为文件（仅演示用）
def save_image(bytes_data: bytes, out_dir: Path, name: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    img_path = out_dir / name
    with open(img_path, "wb") as f:
        f.write(bytes_data)
    return img_path


# -------------------------------------------------------------
# 1️⃣ 获取文档中所有块（保持原始顺序）
def iter_document_blocks(doc):
    """
    递归遍历 Document.body 的子元素，返回 (block_type, xml_element) 元组。
    block_type: 'p' (paragraph), 'tbl' (table), 'sect' (section properties)...
    """
    body_elm = doc.element.body
    for child in body_elm.iterchildren():
        if child.tag.endswith('}p'):          # Paragraph
            yield ('p', child)
        elif child.tag.endswith('}tbl'):      # Table
            yield ('tbl', child)
        # 其余如 sectPr、commentRangeStart 等在本例中可以忽略


# -------------------------------------------------------------
# 2️⃣ 判断块中是否包含图片，并提取图片信息
def find_images_in_block(block_xml, doc_part) -> List[Dict[str, Any]]:
    """
    block_xml: lxml element (CT_P or CT_Tbl)
    doc_part : docx.document.Document.part (用于解析关系)
    返回列表，每项为 {'rId':..., 'name':..., 'bytes':...}
    """
    ns = {
        'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
        'pic': 'http://schemas.openxmlformats.org/drawingml/2006/picture',
        'wp': 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
        'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
        'w':'//schemas.openxmlformats.org/wordprocessingml/2006/main'
    }

    images = []

    # ① <w:drawing> 里的 <a:blip r:embed="rIdX"/>
    drawing_blips = block_xml.xpath('.//w:drawing//a:blip', namespaces=ns)
    for blip in drawing_blips:
        rId = blip.get('{%s}embed' % ns['r'])
        if rId and rId in doc_part.related_parts:
            part = doc_part.related_parts[rId]   # type: docx.opc.package.Part
            images.append({
                'rId': rId,
                'name': Path(part.partname).name,
                'bytes': part.blob
            })

    # ② 老版 <w:pict>（有时是 EMF/WMF）
    pict_blips = block_xml.xpath('.//w:pict//v:imagedata', namespaces={'w': ns['w'], 'v': 'urn:schemas-microsoft-com:office:office'})
    for imagedata in pict_blips:
        rId = imagedata.get('{%s}id' % ns['r'])  # 有时候属性是 r:id
        if rId and rId in doc_part.related_parts:
            part = doc_part.related_parts[rId]
            images.append({
                'rId': rId,
                'name': Path(part.partname).name,
                'bytes': part.blob
            })

    return images


# -------------------------------------------------------------
# 3️⃣ 把块转成可读文本（去掉图片占位符）
def block_text(block_type, block_xml) -> str:
    """
    把段落或表格转成纯文本
    """
    if block_type == 'p':
        # 对段落，仅保留 <w:t>（文字）节点
        texts = block_xml.xpath('.//w:t', namespaces={'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'})
        return ''.join([t.text for t in texts if t.text])
    elif block_type == 'tbl':
        # 简单拼接表格每一行的文字
        rows = block_xml.xpath('.//w:tr', namespaces={'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'})
        row_strs = []
        for r in rows:
            cells = r.xpath('.//w:tc', namespaces={'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'})
            cell_texts = []
            for c in cells:
                txts = c.xpath('.//w:t', namespaces={'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'})
                cell_texts.append(''.join([t.text for t in txts if t.text]))
            row_strs.append(' | '.join(cell_texts))
        return '\n'.join(row_strs)
    else:
        return ''


# -------------------------------------------------------------
# 4️⃣ 主函数：遍历文档、抓图、记录上下文
def extract_images_with_context(docx_path: Path, out_image_dir: Path = None) -> List[Dict]:
    """
    参数
    ----
    docx_path: Path
        .docx 文件路径
    out_image_dir: Path | None
        若提供，则把每张图片写入该目录，返回字段 `image_path` 为文件路径；若为 None，只返回二进制。

    返回
    ----
    List[Dict]，每个 dict 结构示例：
    {
        "image_name": "image1.png",
        "image_bytes": b'....',
        "image_path": "/abs/path/to/image1.png",   # only when out_image_dir is given
        "prev_text": "上一块的文字（可能为空）",
        "next_text": "下一块的文字（可能为空）",
        "block_text": "图片所在块本身的文字（如果有）"
    }
    """
    doc = Document(str(docx_path))
    doc_part = doc.part
    results = []

    # 为了能够获取「前后」块，需要先把所有块一次性缓存
    blocks = list(iter_document_blocks(doc))

    for idx, (blk_type, blk_xml) in enumerate(tqdm(blocks, desc="Scanning docx")):
        images = find_images_in_block(blk_xml, doc_part)
        if not images:
            continue   # 该块不含图片，跳过

        # 当前块的文字（不含图片占位符）
        cur_text = block_text(blk_type, blk_xml).strip()

        # 前后块的文字（如果存在）
        prev_text = ''
        if idx > 0:
            p_type, p_xml = blocks[idx - 1]
            prev_text = block_text(p_type, p_xml).strip()
        next_text = ''
        if idx < len(blocks) - 1:
            n_type, n_xml = blocks[idx + 1]
            next_text = block_text(n_type, n_xml).strip()

        for img in images:
            entry = {
                "image_name": img['name'],
                "image_bytes": img['bytes'],
                "prev_text": prev_text,
                "next_text": next_text,
                "block_text": cur_text
            }

            if out_image_dir:
                saved_path = save_image(img['bytes'], out_image_dir, img['name'])
                entry["image_path"] = str(saved_path)

            results.append(entry)

    return results


# -------------------------------------------------------------
# 5️⃣ 示例调用
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Extract images +上下文 from a .docx")
    parser.add_argument("--docx_file",
                        default=Path(r"C:\Users\houzhimingwx1\Documents\01-code\00-hik-yf\Intelligent_QA\PLM2.0\assets\plm_docx\文档审核.docx"),
                        type=str, help="Path to the .docx file")
    parser.add_argument("-o", "--out-dir", required=False, type=str, default=Path(""),
                        help="Directory to store extracted images (optional)")
    parser.add_argument("-j", "--json", required=False, type=Path, default=True,
                        help="If given, write the result list to a JSON file (base64‑encoded image).")
    args = parser.parse_args()


    data = extract_images_with_context(args.docx_file, args.out_dir)

    print(f"\n共提取到 {len(data)} 张图片。")
    # 简单打印前几条
    for i, item in enumerate(data[:5], 1):
        print(f"\n--- Image #{i} ---")
        print(f"File: {item['image_name']}")
        if args.out_dir:
            print(f"Saved to: {item.get('image_path')}")
        print(f"Prev text: {item['prev_text'][:60]!r}")
        print(f"Block text: {item['block_text'][:60]!r}")
        print(f"Next text: {item['next_text'][:60]!r}")

    # 可选：写成 JSON（图片用 base64，方便后续加载到向量库 metadata）
    if args.json:
        for item in data:
            # 把 bytes 转成 base64 以便 JSON 序列化
            item["image_base64"] = base64.b64encode(item["image_bytes"]).decode()
            # 删除原始 bytes，防止 JSON 过大（如果你不需要存二进制）
            del item["image_bytes"]
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n结果已写入 {args.json}")

