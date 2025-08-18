"""
图像处理和转换工具
"""

import os
import io
import uuid
import signal
import subprocess
import platform
import shutil
import logging
from PIL import Image

logger = logging.getLogger(__name__)

def convert_emf_to_png(emf_data, output_dir, object_id, quick_mode=True):
    """
    自动将EMF格式转换为PNG格式，增强错误处理和健壮性
    quick_mode: 快速模式，跳过耗时的转换尝试，直接保存原格式
    """
    temp_emf_path = None
    try:
        # 验证输入数据
        if not emf_data or len(emf_data) < 16:
            logger.warning(f"EMF数据无效或太小: {len(emf_data) if emf_data else 0} bytes")
            return None
        
        # 创建images目录
        try:
            images_dir = os.path.join(output_dir, "images")
            os.makedirs(images_dir, exist_ok=True)
        except (OSError, IOError) as e:
            logger.error(f"创建images目录失败: {e}")
            return None
        
        # 快速模式：直接保存原格式，跳过转换
        if quick_mode:
            logger.info("快速模式：直接保存EMF文件，跳过转换")
            emf_filename = f"embedded_preview_{object_id}.emf"
            final_emf_path = os.path.join(images_dir, emf_filename)
            
            try:
                with open(final_emf_path, "wb") as f:
                    f.write(emf_data)
                logger.info(f"EMF文件已保存: {emf_filename}")
                return f"images/{emf_filename}"
            except Exception as e:
                logger.error(f"保存EMF文件失败: {e}")
                return None
        
        # 以下是原有的转换逻辑（在非快速模式下执行）
        # 创建临时EMF文件
        try:
            temp_emf_path = os.path.join(output_dir, f"temp_{object_id}.emf")
            with open(temp_emf_path, "wb") as f:
                f.write(emf_data)
            
            # 验证文件写入成功
            if not os.path.exists(temp_emf_path) or os.path.getsize(temp_emf_path) == 0:
                logger.error("临时EMF文件创建失败")
                return None
                
        except (OSError, IOError) as e:
            logger.error(f"写入临时EMF文件失败: {e}")
            return None
        
        # 输出PNG路径
        png_filename = f"embedded_preview_{object_id}.png"
        png_path = os.path.join(images_dir, png_filename)
        
        # 方法1: 使用 PIL 读取基本信息并尝试转换（限时5秒）
        use_timeout = False
        try:
            # 只在Unix系统上使用信号超时
            use_timeout = hasattr(signal, 'SIGALRM')
            
            def timeout_handler(signum, frame):
                raise TimeoutError("PIL转换超时")
            
            # 设置5秒超时（仅在支持的系统上）
            if use_timeout:
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(5)
            
            try:
                with Image.open(temp_emf_path) as img:
                    logger.info(f"PIL检测到图像: 模式={img.mode}, 尺寸={img.size}, 格式={img.format}")
                    
                    # 验证图像
                    img.verify()
                    # 重新打开进行转换
                    with Image.open(temp_emf_path) as img_convert:
                        if img_convert.mode in ('RGBA', 'LA', 'P'):
                            img_convert = img_convert.convert('RGB')
                        img_convert.save(png_path, 'PNG')
                        if os.path.exists(png_path) and os.path.getsize(png_path) > 0:
                            logger.info(f"PIL转换成功: {png_filename}")
                            return f"images/{png_filename}"
            finally:
                if use_timeout:
                    signal.alarm(0)  # 取消超时
                            
        except (TimeoutError, Exception) as e:
            logger.debug(f"PIL 转换失败或超时: {e}")
            if use_timeout:
                signal.alarm(0)  # 确保取消超时
        
        # 方法2: 使用系统工具转换（仅限macOS，限时10秒）
        if platform.system() == "Darwin":
            try:
                # 尝试使用sips命令（限时5秒）
                try:
                    logger.debug(f"尝试sips转换: {temp_emf_path}")
                    result = subprocess.run([
                        'sips', '-s', 'format', 'png', temp_emf_path, '--out', png_path
                    ], capture_output=True, text=True, timeout=5)
                    
                    if result.returncode == 0 and os.path.exists(png_path) and os.path.getsize(png_path) > 0:
                        logger.info(f"sips转换成功: {png_filename}")
                        return f"images/{png_filename}"
                    else:
                        logger.debug(f"sips转换失败: return code {result.returncode}")
                        
                except subprocess.TimeoutExpired:
                    logger.debug("sips命令超时")
                except FileNotFoundError:
                    logger.debug("sips命令不可用")
                except Exception as e:
                    logger.debug(f"sips转换异常: {e}")
            
            except Exception as e:
                logger.debug(f"系统命令转换失败: {e}")
        
        # 方法3: 转换失败，保存原始EMF文件
        try:
            logger.info("转换失败，保存原始EMF文件")
            
            # 保存原始EMF文件
            emf_filename = f"embedded_preview_{object_id}.emf"
            final_emf_path = os.path.join(images_dir, emf_filename)
            
            if temp_emf_path and os.path.exists(temp_emf_path):
                try:
                    os.rename(temp_emf_path, final_emf_path)
                    temp_emf_path = None  # 防止重复删除
                except OSError as e:
                    logger.warning(f"移动EMF文件失败，尝试复制: {e}")
                    try:
                        shutil.copy2(temp_emf_path, final_emf_path)
                    except Exception as copy_e:
                        logger.error(f"复制EMF文件也失败: {copy_e}")
                        return None
            
            logger.info(f"EMF文件已保存: {emf_filename}")
            
            # 返回EMF文件路径
            return f"images/{emf_filename}"
            
        except Exception as e:
            logger.error(f"保存EMF文件失败: {e}")
            return None
            
    except Exception as e:
        logger.error(f"EMF转换过程失败: {e}")
        return None
        
    finally:
        # 清理临时文件
        if temp_emf_path and os.path.exists(temp_emf_path):
            try:
                os.remove(temp_emf_path)
            except Exception as e:
                logger.debug(f"清理临时文件失败: {e}")

def extract_preview_image(image_part, output_dir, object_id, quick_mode=True):
    """
    提取嵌入对象的预览图像并保存为文件
    """
    try:
        # 获取图像数据
        image_data = image_part.blob
        
        # 确定图像格式
        img_format = "png"  # 默认格式
        if hasattr(image_part, 'content_type'):
            content_type = image_part.content_type.lower()
            if 'jpeg' in content_type or 'jpg' in content_type:
                img_format = "jpg"
            elif 'gif' in content_type:
                img_format = "gif"
            elif 'bmp' in content_type:
                img_format = "bmp"
            elif 'png' in content_type:
                img_format = "png"
            elif 'emf' in content_type:
                img_format = "emf"
            elif 'wmf' in content_type:
                img_format = "wmf"
            elif 'tiff' in content_type:
                img_format = "tiff"
        
        # 如果是EMF/WMF格式，尝试转换为PNG
        if img_format in ['emf', 'wmf']:
            try:
                converted_path = convert_emf_to_png(image_data, output_dir, object_id, quick_mode=quick_mode)
                if converted_path:
                    return converted_path
            except Exception as e:
                logger.warning(f"EMF/WMF转换失败，保存原格式: {e}")
        
        # 创建images目录
        images_dir = os.path.join(output_dir, "images")
        os.makedirs(images_dir, exist_ok=True)
        
        # 生成文件名
        img_filename = f"embedded_preview_{object_id}.{img_format}"
        image_path = os.path.join(images_dir, img_filename)
        
        # 保存图像
        with open(image_path, "wb") as img_file:
            img_file.write(image_data)
        
        # 返回相对路径
        return f"images/{img_filename}"
        
    except Exception as e:
        logger.error(f"提取预览图像失败: {e}")
        return None

def get_image_dimensions(image_data):
    """获取图片尺寸"""
    width, height = 0, 0
    try:
        with Image.open(io.BytesIO(image_data)) as img:
            width, height = img.size
    except Exception:
        # 对于SVG等无法直接获取尺寸的图片格式，跳过尺寸获取
        pass
    return width, height
