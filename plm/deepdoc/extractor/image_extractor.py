"""
图像提取器
"""

import os
import uuid
import logging
from plm.deepdoc.utils.image_utils import get_image_dimensions

# 兼容性导入
try:
    from lxml import etree
except ImportError:
    try:
        import xml.etree.ElementTree as etree
    except ImportError:
        from xml.etree import ElementTree as etree

logger = logging.getLogger(__name__)

def extract_images_from_xml(xml_str, doc_part, images_dir, image_references, context="", quick_mode=True):
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
        # image_idx = 1
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
                content_type = image_part.content_type.lower()
                if 'jpeg' in content_type:
                    img_format = "jpg"
                elif 'gif' in content_type:
                    img_format = "gif"
                elif 'bmp' in content_type:
                    img_format = "bmp"
                elif 'png' in content_type:
                    img_format = "png"
                elif 'svg' in content_type:
                    img_format = "svg"
                elif 'tiff' in content_type:
                    img_format = "tiff"
            
            # 生成唯一图片ID
            image_id = f"img_{uuid.uuid4().hex[:8]}"
            img_filename = f"{image_id}.{img_format}"
            # img_filename = f"image_{image_idx:02d}.{img_format}"
            # image_idx += 1
            image_path = os.path.join(images_dir, img_filename)
            
            # 保存图片
            with open(image_path, "wb") as img_file:
                img_file.write(image_data)
            
            # 获取图片尺寸
            width, height = get_image_dimensions(image_data)
            
            # 创建图片节点
            image_node = {
                "type": "image",
                "url": f"images/{img_filename}",
                "path": image_path,
                "format": img_format,
                "width": width,
                "height": height,
                "size": f"{len(image_data)/1024:.2f} KB",
                "context": context
            }
            
            # 记录图片信息
            image_references[image_id] = image_node
            image_nodes.append(image_node)
    
    except Exception as e:
        logger.error(f"从XML提取图片失败: {e}")
    
    return image_nodes

def extract_table_images(cell, table_idx, row_idx, cell_idx, image_references, images_dir):
    """提取表格单元格中的图片"""
    image_nodes = []
    context = f"表格{table_idx}单元格[{row_idx},{cell_idx}]"
    
    try:
        if not hasattr(cell, '_tc') or cell._tc is None:
            return image_nodes
            
        cell_xml = etree.tostring(cell._tc, encoding='unicode')
        image_nodes = extract_images_from_xml(
            cell_xml, 
            cell.part, 
            images_dir, 
            image_references,
            context,
            quick_mode=True
        )
    except Exception as e:
        logger.error(f"提取表格图片失败: {e}")
    
    return image_nodes

def extract_header_footer_images(doc, images_dir, image_references, quick_mode=True):
    """提取页眉页脚中的图片"""
    try:
        for section in doc.sections:
            # 页眉
            if hasattr(section, 'header') and section.header:
                for paragraph in section.header.paragraphs:
                    # 为了向后兼容，将 images_dir 转换为 output_dir 格式
                    output_dir = os.path.dirname(images_dir) if images_dir.endswith('images') else images_dir
                    from plm.deepdoc.extractor.content_extractor import extract_paragraph_content
                    content_nodes = extract_paragraph_content(paragraph, output_dir, image_references, quick_mode)
                    images = [node for node in content_nodes if node.get("type") == "image"]
                    if images:
                        logger.info(f"在页眉中找到 {len(images)} 张图片")
            
            # 页脚
            if hasattr(section, 'footer') and section.footer:
                for paragraph in section.footer.paragraphs:
                    # 为了向后兼容，将 images_dir 转换为 output_dir 格式
                    output_dir = os.path.dirname(images_dir) if images_dir.endswith('images') else images_dir
                    from plm.deepdoc.extractor.content_extractor import extract_paragraph_content
                    content_nodes = extract_paragraph_content(paragraph, output_dir, image_references, quick_mode)
                    images = [node for node in content_nodes if node.get("type") == "image"]
                    if images:
                        logger.info(f"在页脚中找到 {len(images)} 张图片")
    except Exception as e:
        logger.error(f"提取页眉页脚图片失败: {e}")
