import warnings

import functools
import logging
import time
import asyncio

from typing import Union, Tuple, Type, Optional, Callable, Any

from fastapi import Request
from fastapi.responses import JSONResponse

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from plm.utils.schema import ApiResponse

from loguru import logger


def deprecated(message: str = "This function is deprecated.", category=DeprecationWarning):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 发出弃用警告
            warnings.warn(message, category=category, stacklevel=2)
            # 继续执行原函数
            return func(*args, **kwargs)

        return wrapper

    return decorator


class BizException(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message

class DocxParserException(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message

def exception_handler(
        retries: int = 1,
        delay: float = 1,
        exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception,
        default: Optional[Any] = None,
        log_traceback: bool = True
) -> Callable:
    """
    通用异常处理装饰器（支持同步/异步函数）

    Args:
        retries (int): 异常时重试次数，0表示不重试
        delay (float): 重试间的间隔秒数
        exceptions (Exception|tuple): 要捕获的异常类型
        default (any): 异常后的默认返回值
        log_traceback (bool): 是否记录堆栈信息
    """

    def decorator(func: Callable) -> Callable:
        # 同步函数处理器
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            attempt = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    attempt += 1
                    error_msg = (
                        f"调用 {func.__name__} 失败 (第{attempt}次重试)"
                        if retries > 0 and attempt <= retries
                        else f"调用 {func.__name__} 失败，不再重试"
                    )
                    if log_traceback:
                        logging.error(error_msg, exc_info=True)
                    else:
                        logging.error(f"{error_msg} - 错误消息: {str(e)}")

                    if attempt > retries:
                        return default
                    time.sleep(delay)

        # 异步函数处理器
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            attempt = 0
            while True:
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    attempt += 1
                    error_msg = (
                        f"调用 {func.__name__} 失败 (第{attempt}次重试)"
                        if retries > 0 and attempt <= retries
                        else f"调用 {func.__name__} 失败，不再重试"
                    )
                    if log_traceback:
                        logging.error(error_msg, exc_info=True)
                    else:
                        logging.error(f"{error_msg} - 错误消息: {str(e)}")

                    if attempt > retries:
                        return default
                    await asyncio.sleep(delay)

        # 自动选择同步/异步包装器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator

# # 示例使用
# @exception_handler(
#     retries=2,
#     delay=0.5,
#     exceptions=(ValueError, ZeroDivisionError),
#     default=-1,
#     log_traceback=False
# )
# def risky_operation(x: int, y: int) -> float:
#     """这是一个可能抛出异常的操作"""
#     if x < 0:
#         raise ValueError("x不能为负数")
#     return x / y
#
#
# # 测试用例
# print(risky_operation(5, 2))  # 正常调用 → 2.5
# print(risky_operation(-1, 5))  # 触发ValueError → 记录日志后返回-1
# print(risky_operation(5, 0))  # 触发ZeroDivisionError → 重试两次后返回-1
