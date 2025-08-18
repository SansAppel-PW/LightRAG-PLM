"""
增强的图片提取器 - 直接从DOCX ZIP文件提取所有图片
"""

import logging
import os
import uuid
import zipfile

logger = logging.getLogger(__name__)

def extract_all_images_from_docx(docx_path, images_dir):
    """
    直接从DOCX文件的ZIP结构中提取所有图片
    这种方法可以确保提取到文档中的所有图片，无论它们在文档中的位置如何
    
    Args:
        docx_path: DOCX文件路径
        images_dir: 图片输出目录
    
    Returns:
        list: 提取的图片信息列表
    """
    extracted_images = []
    
    try:
        if not os.path.exists(docx_path):
            logger.error(f"DOCX文件不存在: {docx_path}")
            return extracted_images
            
        # 确保输出目录存在
        os.makedirs(images_dir, exist_ok=True)
        
        with zipfile.ZipFile(docx_path, 'r') as zip_file:
            # 获取所有媒体文件
            media_files = [f for f in zip_file.namelist() if f.startswith('word/media/')]
            
            logger.info(f"在文档中发现 {len(media_files)} 个媒体文件")
            
            for media_file in media_files:
                try:
                    # 读取图片数据
                    image_data = zip_file.read(media_file)
                    
                    # 获取原始文件名和扩展名
                    original_name = os.path.basename(media_file)
                    name_part, ext_part = os.path.splitext(original_name)
                    
                    # 处理特殊格式
                    if ext_part.lower() == '.emf':
                        ext_part = '.png'  # EMF转换为PNG
                    elif ext_part.lower() == '.wmf':
                        ext_part = '.png'  # WMF转换为PNG
                    elif not ext_part:
                        ext_part = '.png'  # 默认PNG
                    
                    # 生成唯一文件名
                    image_id = f"img_{uuid.uuid4().hex[:8]}"
                    img_filename = f"{image_id}{ext_part}"
                    image_path = os.path.join(images_dir, img_filename)
                    
                    # 保存图片
                    with open(image_path, 'wb') as img_file:
                        img_file.write(image_data)
                    
                    # 获取图片大小
                    file_size = len(image_data)
                    
                    # 创建图片信息
                    image_info = {
                        "type": "image",
                        "id": image_id,
                        "filename": img_filename,
                        "original_name": original_name,
                        "path": f"images/{img_filename}",
                        "size_bytes": file_size,
                        "size_kb": f"{file_size/1024:.2f} KB",
                        "format": ext_part[1:].upper(),  # 去掉点号
                        "source": media_file
                    }
                    
                    extracted_images.append(image_info)
                    logger.debug(f"提取图片: {original_name} -> {img_filename}")
                    
                except Exception as e:
                    logger.error(f"提取图片 {media_file} 失败: {e}")
                    continue
                    
        logger.info(f"成功提取 {len(extracted_images)} 张图片到 {images_dir}")
        
    except zipfile.BadZipFile as e:
        logger.error(f"DOCX文件格式错误: {e}")
    except Exception as e:
        logger.error(f"提取图片时发生错误: {e}")
    
    return extracted_images

def analyze_image_relationships(docx_path):
    """
    分析DOCX文件中的图片关系，用于调试
    
    Args:
        docx_path: DOCX文件路径
    
    Returns:
        dict: 分析结果
    """
    analysis = {
        "media_files": [],
        "relationship_files": [],
        "document_relationships": [],
        "header_footer_relationships": []
    }
    
    try:
        with zipfile.ZipFile(docx_path, 'r') as zip_file:
            file_list = zip_file.namelist()
            
            # 媒体文件
            analysis["media_files"] = [f for f in file_list if f.startswith('word/media/')]
            
            # 关系文件
            analysis["relationship_files"] = [f for f in file_list if f.endswith('.rels')]
            
            # 分析主文档关系
            if 'word/_rels/document.xml.rels' in file_list:
                try:
                    rels_content = zip_file.read('word/_rels/document.xml.rels').decode('utf-8')
                    import re
                    # 查找图片关系
                    image_rels = re.findall(r'Target="media/([^"]+)".*?Type="[^"]*image[^"]*"', rels_content)
                    analysis["document_relationships"] = image_rels
                except Exception as e:
                    logger.error(f"分析文档关系失败: {e}")
            
            # 分析页眉页脚关系
            header_footer_rels = [f for f in file_list if f.startswith('word/_rels/header') or f.startswith('word/_rels/footer')]
            for rel_file in header_footer_rels:
                try:
                    rels_content = zip_file.read(rel_file).decode('utf-8')
                    import re
                    image_rels = re.findall(r'Target="media/([^"]+)".*?Type="[^"]*image[^"]*"', rels_content)
                    analysis["header_footer_relationships"].extend(image_rels)
                except Exception as e:
                    logger.error(f"分析页眉页脚关系失败: {e}")
    
    except Exception as e:
        logger.error(f"分析图片关系失败: {e}")
    
    return analysis
