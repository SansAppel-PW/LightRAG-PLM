"""
批量处理器
"""

import os
import json
import logging
import traceback
from datetime import datetime
from plm.deepdoc.parser.document_parser import parse_docx_with_path
from plm.deepdoc.processor.text_processor import process_document_to_text
from plm.deepdoc.utils.text_utils import safe_filename, add_error_to_failed_files

logger = logging.getLogger(__name__)

def process_docx_folder(input_folder, output_base_dir, quick_mode=True):
    """
    批量处理文件夹中的所有DOCX文件，增强错误处理和进度跟踪
    
    Args:
        input_folder: 输入文件夹路径
        output_base_dir: 输出基础目录
        quick_mode: 快速模式，跳过耗时的EMF/WMF转换（默认True）
    """
    try:
        # 确保输出目录存在
        os.makedirs(output_base_dir, exist_ok=True)
    except (OSError, IOError) as e:
        logger.error(f"创建输出目录失败: {e}")
        return 0
    
    # 检查输入目录
    if not os.path.exists(input_folder):
        logger.error(f"输入目录不存在: {input_folder}")
        return 0
        
    if not os.path.isdir(input_folder):
        logger.error(f"输入路径不是目录: {input_folder}")
        return 0
    
    # 准备汇总数据
    all_documents = []
    
    # 查找所有DOCX文件，过滤掉临时文件
    try:
        all_files = os.listdir(input_folder)
        docx_files = [
            f for f in all_files 
            if f.lower().endswith('.docx') and not f.startswith('~$')
        ]
    except (OSError, IOError) as e:
        logger.error(f"读取目录失败: {e}")
        return 0
    
    if not docx_files:
        logger.warning(f"在 {input_folder} 中没有找到有效的DOCX文件")
        return 0
    
    logger.info(f"开始处理 {len(docx_files)} 个DOCX文件...")
    
    processed_count = 0
    failed_files = []
    skipped_files = []
    
    for idx, filename in enumerate(docx_files, 1):
        docx_path = os.path.join(input_folder, filename)
        logger.info(f"处理文件 ({idx}/{len(docx_files)}): {filename}")
        
        try:
            # 为每个文件创建输出目录
            safe_name = safe_filename(filename.replace('.docx', ''))
            output_dir = os.path.join(output_base_dir, safe_name)
            
            try:
                os.makedirs(output_dir, exist_ok=True)
            except (OSError, IOError) as e:
                logger.error(f"创建文件输出目录失败: {e}")
                add_error_to_failed_files(failed_files, filename, f"Directory creation failed: {e}")
                continue
            
            # 检查文件是否可读
            try:
                with open(docx_path, 'rb') as test_file:
                    test_file.read(1)
            except (OSError, IOError) as e:
                logger.error(f"文件不可读: {filename}, 错误: {e}")
                add_error_to_failed_files(failed_files, filename, f"File not readable: {e}")
                continue
            
            # 解析文档
            document_structure = parse_docx_with_path(docx_path, output_dir, quick_mode)
            
            if not document_structure:
                logger.error(f"跳过 {filename}，解析失败")
                add_error_to_failed_files(failed_files, filename, "Document parsing failed")
                continue
            
            # 检查解析结果的质量
            if document_structure.get("processing_info", {}).get("errors"):
                logger.warning(f"文件 {filename} 解析时有错误，但继续处理")
            
            processed_count += 1
            
            # 保存为JSON文件
            json_path = os.path.join(output_dir, "document.json")
            try:
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(document_structure, f, ensure_ascii=False, indent=2)
            except (OSError, IOError) as e:
                logger.error(f"保存JSON文件失败: {e}")
                # 即使JSON保存失败，也算作处理失败
                processed_count -= 1
                add_error_to_failed_files(failed_files, filename, f"JSON save failed: {e}")
                continue
            
            # 处理为标准化文本格式
            try:
                # 从文件名提取文档名称
                doc_name = safe_name
                processed_text = process_document_to_text(document_structure, doc_name)
                
                # 保存处理后的文本
                text_path = os.path.join(output_dir, "processed_text.txt")
                with open(text_path, "w", encoding="utf-8") as f:
                    f.write(processed_text)
                
                logger.info(f"文件 {filename} 的标准化文本已保存")
                
            except Exception as e:
                logger.error(f"文件 {filename} 文本处理失败: {e}")
                # 文本处理失败不影响整体处理状态
            
            # 添加到汇总列表
            all_documents.append({
                "file": filename,
                "path": json_path,
                "status": "success",
                "images_found": len(document_structure.get("images", {})),
                "warnings": len(document_structure.get("processing_info", {}).get("warnings", [])),
                "errors": len(document_structure.get("processing_info", {}).get("errors", []))
            })
            
            # 统计图片数量
            total_images = len(document_structure.get("images", {}))
            hf_images = len(document_structure.get("header_footer_images", []))
            processing_info = document_structure.get("processing_info", {})
            
            logger.info(f"文件 {filename} 处理完成 - 图片: {total_images}, 页眉页脚图片: {hf_images}, 警告: {len(processing_info.get('warnings', []))}")
            
        except Exception as e:
            logger.error(f"处理文件 {filename} 时发生未知错误: {e}")
            logger.error(traceback.format_exc())
            add_error_to_failed_files(failed_files, filename, f"Unexpected error: {e}")
            continue
    
    # 保存汇总信息
    try:
        summary_path = os.path.join(output_base_dir, "summary.json")
        summary_data = {
            "input_folder": input_folder,
            "processing_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_files": len(docx_files),
            "processed": processed_count,
            "failed": len(failed_files),
            "skipped": len(skipped_files),
            "failed_files": failed_files,
            "skipped_files": skipped_files,
            "documents": all_documents,
            "success_rate": f"{processed_count/len(docx_files)*100:.1f}%" if docx_files else "0%"
        }
        
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, ensure_ascii=False, indent=2)
            
        logger.info(f"汇总信息保存在 {summary_path}")
        
    except Exception as e:
        logger.error(f"保存汇总信息失败: {e}")
    
    # 打印处理结果
    logger.info(f"批量处理完成!")
    logger.info(f"成功处理: {processed_count}/{len(docx_files)} 个文件 ({processed_count/len(docx_files)*100:.1f}%)")
    
    if failed_files:
        logger.warning(f"失败文件 ({len(failed_files)}):")
        for failed in failed_files[:5]:  # 只显示前5个失败文件
            logger.warning(f"  - {failed['file']}: {failed['error']}")
        if len(failed_files) > 5:
            logger.warning(f"  ... 还有 {len(failed_files)-5} 个失败文件，详见summary.json")
    
    return processed_count
