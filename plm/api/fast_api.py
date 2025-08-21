'''
Author: Jerry Hu
Date: 2025-08-21 10:00:05
LastEditors: Jerry Hu
LastEditTime: 2025-08-21 10:17:07
FilePath: \Intelligent_QA\PLM2.0\plm\api\fast_api.py
Description: 个人联系方式：1548814695@qq.com

Copyright (c) 2025 by ${git_name_email}, All Rights Reserved. 
'''
from contextlib import asynccontextmanager
from pathlib import Path

import click
import uvicorn
from fastapi import FastAPI

from transformers import AutoTokenizer

from lightrag.llm.openai import openai_complete_if_cache, openai_embed
from lightrag.rerank import custom_rerank
from lightrag.types import GPTKeywordExtractionFormat
from lightrag.utils import EmbeddingFunc

from plm.utils.cli_parser import arg_parse
from loguru import logger
from plm.conf.settings import (app_settings, rep_settings, llm_settings, rag_settings, ui_settings)
from lightrag import LightRAG

from plm.api.router import router
from click.testing import CliRunner

from plm.utils.handler.exception_handler import BizException, DocxParserException
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette import status
from fastapi.exceptions import RequestValidationError
from fastapi import HTTPException, Request
from plm.utils.handler.exception_handler import (
    biz_exception_handler,
    http_exception_handler,
    starlette_http_exception_handler,
    validation_exception_handler,
    unhandled_exception_handler,
    docx_parser_exception_handler
)

from plm.core.rag import init_rag
from lightrag.kg.shared_storage import (
    get_namespace_data,
    get_pipeline_status_lock,
    initialize_pipeline_status,
    cleanup_keyed_lock,
)


# app = FastAPI()
def create_app():
    # Setup logging
    logger.level(app_settings.LOG_LEVEL)
    logger.info('---create-app---')

    rag = init_rag()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Lifespan context manager for startup and shutdown events"""
        # Store background tasks
        app.state.background_tasks = set()
        # app.state.rag=rag

        try:
            # Initialize database connections
            await rag.initialize_storages()

            logger.info('RAG INIT SUCCESSFULLY.')

            await initialize_pipeline_status()
            pipeline_status = await get_namespace_data("pipeline_status")

            # should_start_autoscan = False
            # async with get_pipeline_status_lock():
            #     # Auto scan documents if enabled
            #     if args.auto_scan_at_startup:
            #         if not pipeline_status.get("autoscanned", False):
            #             pipeline_status["autoscanned"] = True
            #             should_start_autoscan = True

            ## Only run auto scan when no other process started it first
            # if should_start_autoscan:
            #     # Create background task
            #     task = asyncio.create_task(run_scanning_process(rag, doc_manager))
            #     app.state.background_tasks.add(task)
            #     task.add_done_callback(app.state.background_tasks.discard)
            #     logger.info(f"Process {os.getpid()} auto scan task started at startup.")

            logger.info("\nServer is ready to accept connections! 🚀\n")

            yield

        finally:
            # Clean up database connections
            await rag.finalize_storages()

    logger.info('---settinngs fastapi---')
    # Initialize FastAPI
    app_kwargs = {
        "title": "PLM2.0 Server API",
        "description": "Providing API for PLM2.0 core, Web UI and LLM Model Emulation (With authentication)" if llm_settings.HIK_MAAS_KEY else "",
        "version": app_settings.APP_VERSION,
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "lifespan": lifespan,
        # Configure Swagger UI parameters
        # Enable persistAuthorization and tryItOutEnabled for better user experience
        "swagger_ui_parameters": {
            "persistAuthorization": True,
            "tryItOutEnabled": True,
        }
    }

    app = FastAPI(**app_kwargs)

    app.include_router(router)

    # Webui mount webui/index.html
    # static_dir = Path(__file__).parent / "webui"
    static_dir = Path(ui_settings.RAG_WEB_UI_PATH)
    static_dir.mkdir(exist_ok=True)
    app.mount(
        "/webui",
        SmartStaticFiles(
            directory=static_dir, html=True, check_dir=True
        ),  # Use SmartStaticFiles
        name="webui",
    )

    return app
from fastapi.staticfiles import StaticFiles
# Custom StaticFiles class for smart caching
class SmartStaticFiles(StaticFiles):  # Renamed from NoCacheStaticFiles
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)

        if path.endswith(".html"):
            response.headers["Cache-Control"] = (
                "no-cache, no-store, must-revalidate"
            )
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        elif (
            "/assets/" in path
        ):  # Assets (JS, CSS, images, fonts) generated by Vite with hash in filename
            response.headers["Cache-Control"] = (
                "public, max-age=31536000, immutable"
            )
        # Add other rules here if needed for non-HTML, non-asset files

        # Ensure correct Content-Type
        if path.endswith(".js"):
            response.headers["Content-Type"] = "application/javascript"
        elif path.endswith(".css"):
            response.headers["Content-Type"] = "text/css"

        return response

# Create application instance directly instead of using factory function
app: FastAPI = create_app()

app.add_exception_handler(Exception, unhandled_exception_handler)
app.add_exception_handler(BizException, biz_exception_handler)  # type: ignore
app.add_exception_handler(DocxParserException, docx_parser_exception_handler)  # type: ignore
app.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore
app.add_exception_handler(StarletteHTTPException, starlette_http_exception_handler)  # type: ignore
app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore



@click.command(context_settings=dict(ignore_unknown_options=True, allow_extra_args=True))
@click.pass_context
@click.option('--host', default='127.0.0.1', help='Server host (default: 127.0.0.1)')
@click.option('--port', default=8000, type=int, help='Server port (default: 8000)')
# @click.option('--host', default='localhost', help='Server host (default: 127.0.0.1)')
# @click.option('--port', default=8001, type=int, help='Server port (default: 8000)')
@click.option('--reload', is_flag=True, help='Enable auto-reload (development mode)')
@click.option('--env', default='development', help='Environment (default: development)')
def main(ctx, host, port, reload, **kwargs):
    kwargs.update(arg_parse(ctx))

    # 将配置参数存储到应用状态中
    app.state.config = kwargs

    logger.info(f"config:{app.state.config}")

    logger.info(r"""
          _____  _      __  __   ___    ___
         |  __ \| |    |  \/  | |__ \  / _ \
         | |__) | |    | \  / |    ) || | | |
         |  ___/| |    | |\/| |   / / | | | |
         | |    | |____| |  | |  / /_ | |_| |
         |_|    |______|_|  |_| |____(_\___/

       """)
    # """
    #         ____  __    __  ___   ___    ____
    #        / __ \/ /   /  |/  /  |__ \  / __ \
    #       / /_/ / /   / /|_/ /   __/ / / / / /
    #      / ____/ /___/ /  / /   / __/_/ /_/ /
    #     /_/   /_____/_/  /_/   /____(_\____/
    # """

    """启动 PLM2.0 FastAPI 服务器的命令行入口"""  # MinerU
    logger.info(f"Start PLM2.0 FastAPI Service: http://{app_settings.SERVER_HOST}:{app_settings.SERVER_PORT}")
    logger.info("The API documentation can be accessed at the following address:")
    logger.info(f"- Swagger UI: http://{app_settings.SERVER_HOST}:{app_settings.SERVER_PORT}/docs")
    logger.info(f"- ReDoc: http://{app_settings.SERVER_HOST}:{app_settings.SERVER_PORT}/redoc")

    uvicorn.run(
        "plm.api.fast_api:app",
        host=app_settings.SERVER_HOST,
        port=app_settings.SERVER_PORT,
        reload=reload,
    )


if __name__ == "__main__":
    runner = CliRunner()
    runner.invoke(main, [])
