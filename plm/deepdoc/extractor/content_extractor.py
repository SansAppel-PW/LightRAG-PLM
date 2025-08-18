"""
内容提取器 - 提取段落中的各种内容（图片、SmartArt、嵌入对象）
"""

import logging
from plm.deepdoc.extractor.image_extractor import extract_images_from_xml
from plm.deepdoc.extractor.smartart_extractor import extract_smartart_from_xml, extract_embedded_objects_from_xml

logger = logging.getLogger(__name__)

def extract_paragraph_content(para, output_dir, image_references, quick_mode=True):
    """提取段落中的SmartArt和嵌入对象内容，不再提取图片（避免重复）"""
    content_nodes = []
    context = f"段落: {para.text[:20] if para.text else ''}..." if para.text else "段落"
    
    # 确保目录存在
    import os
    images_dir = os.path.join(output_dir, "images")
    os.makedirs(images_dir, exist_ok=True)
    
    for run_idx, run in enumerate(para.runs):
        if run._element is not None and run._element.xml:
            try:
                # 提取图片（为了在内容结构中创建节点）
                images = extract_images_from_xml(
                    run._element.xml,
                    para.part,
                    images_dir,
                    image_references,
                    f"{context} (运行 {run_idx})"
                )
                if images:
                    content_nodes.extend(images)
                
                # 提取SmartArt
                smartarts = extract_smartart_from_xml(
                    run._element.xml,
                    para.part,
                    output_dir,
                    f"{context} (运行 {run_idx})"
                )
                if smartarts:
                    content_nodes.extend(smartarts)
                
                # 提取嵌入对象 (OLE Objects)
                embedded_objects = extract_embedded_objects_from_xml(
                    run._element.xml,
                    para.part,
                    output_dir,
                    f"{context} (运行 {run_idx})",
                    quick_mode
                )
                if embedded_objects:
                    content_nodes.extend(embedded_objects)
                    
            except Exception as e:
                logger.error(f"提取段落内容失败: {e}")
    
    return content_nodes
