import asyncio
import functools
import logging
import time
import warnings
from typing import Union, Tuple, Type, Optional, Callable, Any

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger
from starlette import status
from starlette.exceptions import HTTPException as StarletteHTTPException

from plm.utils.schema import ApiResponse


class BizException(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message


class DocxParserException(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message


async def biz_exception_handler(request: Request, exc: BizException):
    return JSONResponse(
        status_code=status.HTTP_200_OK,  # 业务异常通常返回 200，错误在 body 中体现
        content=ApiResponse(code=exc.code, message='Business Exception', data={'errors': exc.message}).model_dump()
    )


async def docx_parser_exception_handler(request: Request, exc: DocxParserException):
    return JSONResponse(
        status_code=status.HTTP_200_OK,  # 业务异常通常返回 200，错误在 body 中体现
        content=ApiResponse(code=exc.code, message='Docx Parser Exception', data={'errors': exc.message}).model_dump()
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=ApiResponse(code=exc.status_code, message=exc.detail).model_dump()
    )


async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ApiResponse(code=exc.status_code, message=exc.detail).model_dump()
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ApiResponse(
            code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            # message=f"请求参数错误: {exc.errors()[0]['msg']}",
            message=f"Validation Error: {exc.errors()[0]['msg']}",
            data={"errors": exc.errors()}
        ).model_dump()
    )


async def unhandled_exception_handler(request: Request, exc: Exception):
    # 可以在这里记录日志
    # print(f"Unhandled exception: {exc}")  # 建议使用 logging
    logger.error(f"Unhandled exception at {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ApiResponse(
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            # message="服务器内部错误，请联系管理员",
            message="Internal Server Error",
            data={'errors': exc}).model_dump()
    )


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
