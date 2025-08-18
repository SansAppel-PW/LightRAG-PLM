"""
SmartArt和嵌入对象提取器
"""

import os
import json
import uuid
import logging
import traceback
from plm.deepdoc.utils.image_utils import extract_preview_image

# 兼容性导入
try:
    from lxml import etree
except ImportError:
    try:
        import xml.etree.ElementTree as etree
    except ImportError:
        from xml.etree import ElementTree as etree

logger = logging.getLogger(__name__)

def extract_smartart_from_xml(xml_str, doc_part, output_dir, context=""):
    """
    从XML字符串中提取SmartArt图表信息
    返回: SmartArt节点列表
    """
    smartart_nodes = []
    try:
        if not xml_str or ('<a:graphic' not in xml_str and '<w:drawing>' not in xml_str):
            return smartart_nodes
        
        namespaces = {
            'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
            'pic': 'http://schemas.openxmlformats.org/drawingml/2006/picture',
            'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
            'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
            'dgm': 'http://schemas.openxmlformats.org/drawingml/2006/diagram',
            'wp': 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
            'mc': 'http://schemas.openxmlformats.org/markup-compatibility/2006'
        }
        
        root = etree.fromstring(xml_str)
        
        # 查找所有graphic元素
        graphics = root.findall('.//a:graphic', namespaces)
        
        for graphic in graphics:
            graphic_data = graphic.find('.//a:graphicData', namespaces)
            if graphic_data is not None:
                uri = graphic_data.get('uri')
                if uri and 'diagram' in uri:
                    logger.info(f"发现SmartArt图表在 {context}")
                    smartart_data = extract_smartart_details(graphic_data, doc_part, output_dir, namespaces)
                    if smartart_data:
                        smartart_nodes.append(smartart_data)
    
    except Exception as e:
        logger.error(f"从XML提取SmartArt失败: {e}")
    
    return smartart_nodes

def extract_smartart_details(graphic_data, doc_part, output_dir, namespaces):
    """
    提取SmartArt的详细信息和文本内容
    """
    try:
        # 查找关系ID
        rel_ids_elem = graphic_data.find('.//dgm:relIds', namespaces)
        if rel_ids_elem is None:
            return None
        
        # 获取各种关系ID（使用完整的命名空间属性名）
        dm_rel_id = rel_ids_elem.get(f'{{{namespaces["r"]}}}dm')  # data model
        lo_rel_id = rel_ids_elem.get(f'{{{namespaces["r"]}}}lo')  # layout
        qs_rel_id = rel_ids_elem.get(f'{{{namespaces["r"]}}}qs')  # quick style
        cs_rel_id = rel_ids_elem.get(f'{{{namespaces["r"]}}}cs')  # color scheme
        
        logger.info(f"SmartArt关系ID - dm: {dm_rel_id}, lo: {lo_rel_id}, qs: {qs_rel_id}, cs: {cs_rel_id}")
        logger.info(f"可用的关系部件数量: {len(doc_part.related_parts)}")
        
        smartart_data = {
            "type": "smartart",
            "text_content": [],
            "diagram_type": "unknown",
            "nodes": []
        }
        
        # 提取数据模型中的文本内容
        if dm_rel_id and dm_rel_id in doc_part.related_parts:
            logger.info(f"找到数据模型关系: {dm_rel_id}")
            data_part = doc_part.related_parts[dm_rel_id]
            data_xml = data_part.blob.decode('utf-8')
            text_nodes = extract_smartart_text(data_xml)
            smartart_data["text_content"] = text_nodes
            smartart_data["nodes"] = len(text_nodes)
        else:
            logger.warning(f"未找到数据模型关系 {dm_rel_id} 或关系不存在")
        
        # 尝试确定图表类型
        if lo_rel_id and lo_rel_id in doc_part.related_parts:
            layout_part = doc_part.related_parts[lo_rel_id]
            layout_xml = layout_part.blob.decode('utf-8')
            diagram_type = extract_diagram_type(layout_xml)
            if diagram_type:
                smartart_data["diagram_type"] = diagram_type
        
        # 生成唯一ID
        smartart_id = f"smartart_{uuid.uuid4().hex[:8]}"
        smartart_data["id"] = smartart_id
        
        # 保存原始数据到文件（可选）
        smartart_dir = os.path.join(output_dir, "smartart")
        os.makedirs(smartart_dir, exist_ok=True)
        
        smartart_file = os.path.join(smartart_dir, f"{smartart_id}.json")
        with open(smartart_file, 'w', encoding='utf-8') as f:
            json.dump(smartart_data, f, ensure_ascii=False, indent=2)
        
        smartart_data["file_path"] = f"smartart/{smartart_id}.json"
        
        logger.info(f"提取SmartArt成功，包含 {len(smartart_data['text_content'])} 个文本节点")
        return smartart_data
        
    except Exception as e:
        logger.error(f"提取SmartArt详细信息失败: {e}")
        logger.error(traceback.format_exc())
        return None

def extract_smartart_text(data_xml):
    """
    从SmartArt数据模型XML中提取文本内容，保持层次结构
    """
    text_nodes = []
    try:
        # 定义命名空间
        namespaces = {
            'dgm': 'http://schemas.openxmlformats.org/drawingml/2006/diagram',
            'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'
        }
        
        root = etree.fromstring(data_xml.encode('utf-8'))
        
        # 1. 解析所有数据点
        points = {}
        pt_elements = root.findall('.//dgm:pt', namespaces)
        
        for pt in pt_elements:
            model_id = pt.get('modelId')
            point_type = pt.get('type', 'unknown')
            
            # 提取文本内容
            text_parts = []
            text_elems = pt.findall('.//a:t', namespaces)
            for text_elem in text_elems:
                if text_elem.text:
                    text_parts.append(text_elem.text.strip())
            
            combined_text = ' '.join(text_parts) if text_parts else ''
            points[model_id] = {
                'text': combined_text,
                'type': point_type,
                'children': []
            }
        
        # 2. 解析连接关系构建层次结构
        connections = root.findall('.//dgm:cxn', namespaces)
        parent_child_map = {}
        
        for cxn in connections:
            src_id = cxn.get('srcId')
            dest_id = cxn.get('destId')
            cxn_type = cxn.get('type', 'unknown')
            src_ord = int(cxn.get('srcOrd', 0))
            
            # 只处理非presentation的连接（即真正的数据结构关系）
            if cxn_type in ['presOf', 'presParOf']:
                continue
                
            if src_id not in parent_child_map:
                parent_child_map[src_id] = []
            parent_child_map[src_id].append((dest_id, src_ord))
        
        # 3. 找到根节点（type="doc"的节点）
        root_id = None
        for point_id, point in points.items():
            if point['type'] == 'doc':
                root_id = point_id
                break
        
        # 4. 构建层次结构并提取文本
        def extract_hierarchy_text(node_id, level=0):
            if node_id not in points:
                return
            
            point = points[node_id]
            
            # 添加当前节点的文本（如果有的话）
            if point['text']:
                text_nodes.append(f"{'  ' * level}{point['text']}")
            
            # 处理子节点，按srcOrd排序
            if node_id in parent_child_map:
                children = sorted(parent_child_map[node_id], key=lambda x: x[1])
                for child_id, _ in children:
                    extract_hierarchy_text(child_id, level + 1)
        
        if root_id:
            extract_hierarchy_text(root_id)
        
        # 如果层次结构提取失败，回退到简单文本提取
        if not text_nodes:
            seen_texts = set()
            for point in points.values():
                if point['text'] and point['text'] not in seen_texts:
                    text_nodes.append(point['text'])
                    seen_texts.add(point['text'])
    
    except Exception as e:
        logger.error(f"提取SmartArt文本失败: {e}")
        # 回退到原始方法
        try:
            root = etree.fromstring(data_xml.encode('utf-8'))
            texts = []
            # 使用兼容的方法查找文本元素
            text_elements = []
            try:
                # lxml方法
                text_elements = root.xpath('.//a:t', namespaces={'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'})
            except (AttributeError, ImportError):
                # ElementTree方法
                text_elements = root.findall('.//{http://schemas.openxmlformats.org/drawingml/2006/main}t')
            
            seen_texts = set()
            for elem in text_elements:
                if elem.text and elem.text.strip() and elem.text.strip() not in seen_texts:
                    texts.append(elem.text.strip())
                    seen_texts.add(elem.text.strip())
            text_nodes = texts
        except:
            pass
    
    return text_nodes

def extract_diagram_type(layout_xml):
    """
    从布局XML中确定图表类型
    """
    try:
        # 常见的SmartArt布局类型
        layout_patterns = {
            'list': ['list', 'bullet', 'sequence'],
            'process': ['process', 'flow', 'step'],
            'cycle': ['cycle', 'circular'],
            'hierarchy': ['hierarchy', 'org', 'tree'],
            'relationship': ['relationship', 'venn', 'matrix'],
            'pyramid': ['pyramid', 'funnel']
        }
        
        layout_xml_lower = layout_xml.lower()
        
        for diagram_type, patterns in layout_patterns.items():
            for pattern in patterns:
                if pattern in layout_xml_lower:
                    return diagram_type
        
        return "unknown"
    
    except Exception as e:
        logger.error(f"确定图表类型失败: {e}")
        return "unknown"

def extract_embedded_objects_from_xml(xml_str, doc_part, output_dir, context="", quick_mode=True):
    """
    从XML字符串中提取嵌入对象（如Visio图表、Excel表格等）
    返回: 嵌入对象节点列表
    """
    embedded_objects = []
    try:
        if not xml_str or '<w:object' not in xml_str:
            return embedded_objects
        
        namespaces = {
            'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
            'o': 'urn:schemas-microsoft-com:office:office',
            'v': 'urn:schemas-microsoft-com:vml',
            'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
        }
        
        root = etree.fromstring(xml_str)
        
        # 查找所有object元素
        objects = root.findall('.//w:object', namespaces)
        
        for obj_idx, obj in enumerate(objects):
            logger.info(f"发现嵌入对象在 {context}")
            
            # 分析OLE对象
            ole_objects = obj.findall('.//o:OLEObject', namespaces)
            
            for ole in ole_objects:
                ole_type = ole.get('Type', 'Unknown')
                prog_id = ole.get('ProgID', 'Unknown')
                r_id = ole.get(f'{{{namespaces["r"]}}}id')
                
                # 获取尺寸信息
                shapes = obj.findall('.//v:shape', namespaces)
                width, height = "unknown", "unknown"
                preview_image_r_id = None
                
                if shapes:
                    shape = shapes[0]
                    style = shape.get('style', '')
                    # 解析style中的尺寸信息
                    if 'width:' in style and 'height:' in style:
                        import re
                        width_match = re.search(r'width:([^;]+)', style)
                        height_match = re.search(r'height:([^;]+)', style)
                        if width_match:
                            width = width_match.group(1).strip()
                        if height_match:
                            height = height_match.group(1).strip()
                    
                    # 查找预览图像关系ID
                    image_data = shape.find('.//v:imagedata', namespaces)
                    if image_data is not None:
                        preview_image_r_id = image_data.get(f'{{{namespaces["r"]}}}id')
                
                # 确定对象类型
                object_type = "unknown"
                object_description = prog_id
                
                if "Visio" in prog_id:
                    object_type = "visio"
                    object_description = "Visio绘图/流程图"
                elif "Excel" in prog_id:
                    object_type = "excel"
                    object_description = "Excel工作表"
                elif "PowerPoint" in prog_id:
                    object_type = "powerpoint"
                    object_description = "PowerPoint演示文稿"
                elif "Word" in prog_id:
                    object_type = "word"
                    object_description = "Word文档"
                
                # 尝试获取嵌入文件信息
                embedded_file_info = None
                if r_id and r_id in doc_part.related_parts:
                    embedded_part = doc_part.related_parts[r_id]
                    embedded_file_info = {
                        "size": len(embedded_part.blob),
                        "content_type": getattr(embedded_part, 'content_type', 'unknown')
                    }
                
                # 生成唯一ID
                object_id = f"embedded_obj_{uuid.uuid4().hex[:8]}"
                
                # 创建嵌入对象节点
                embedded_obj = {
                    "type": "embedded_object",
                    "object_type": object_type,
                    "description": object_description,
                    "prog_id": prog_id,
                    "ole_type": ole_type,
                    "width": width,
                    "height": height,
                    "context": context,
                    "id": object_id
                }
                
                if embedded_file_info:
                    embedded_obj["file_info"] = embedded_file_info
                
                # 提取并保存预览图像
                preview_image_path = None
                if preview_image_r_id and preview_image_r_id in doc_part.related_parts:
                    image_part = doc_part.related_parts[preview_image_r_id]
                    preview_image_path = extract_preview_image(image_part, output_dir, object_id, quick_mode)
                    if preview_image_path:
                        logger.info(f"成功提取预览图像: {preview_image_path}")
                        embedded_obj["preview_image"] = preview_image_path
                
                # 保存对象信息到文件
                objects_dir = os.path.join(output_dir, "embedded_objects")
                os.makedirs(objects_dir, exist_ok=True)
                
                object_file = os.path.join(objects_dir, f"{object_id}.json")
                with open(object_file, 'w', encoding='utf-8') as f:
                    json.dump(embedded_obj, f, ensure_ascii=False, indent=2)
                
                embedded_obj["file_path"] = f"embedded_objects/{object_id}.json"
                
                embedded_objects.append(embedded_obj)
                logger.info(f"提取嵌入对象成功: {object_description} ({width} x {height})")
    
    except Exception as e:
        logger.error(f"从XML提取嵌入对象失败: {e}")
    
    return embedded_objects
