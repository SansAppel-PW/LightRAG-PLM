import asyncio
from typing import Annotated

from fastapi import APIRouter, Request, Body, Depends

from lightrag import QueryParam
from plm.utils.schema import RAGQARequest,RAGQAResponse

from loguru import logger

from lightrag.kg.shared_storage import initialize_pipeline_status
from plm.core.rag import init_rag

router = APIRouter()

@router.post(path="/", response_model=RAGQAResponse)
async def rag_query_and_answer(
        # request: Request,
        args: Annotated[RAGQARequest,
        Body(examples=[{"question": "PLM 怎么修改物料的采购类型？"}])]
        # db_session=Depends()
):
    logger.info(f'RAG QUERY AND ANSWER...')
    logger.info(f'User Question: {args.question}')
    # logger.info(f'User Request Info: {request.headers}')

    text = args.question
    # Initialize RAG
    rag = init_rag()
    # Initialize database connections
    await rag.initialize_storages()
    await initialize_pipeline_status()
    # MAGIC_SPLIT_STR = "\n↔\n"
    # rag_ainsert_reponse = await rag.ainsert(input=text,
    #                                         split_by_character=MAGIC_SPLIT_STR,
    #                                         split_by_character_only=False,
    #                                         ids=None,
    #                                         file_paths=input_path
    #                                         )
    # logger.info(f'RAG ainsert Response: {rag_ainsert_reponse}')
    rag_query_response = await rag.aquery(query=text, param=QueryParam(mode="naive"))

    logger.info(f"RAG QUERY RESPONSE: {rag_query_response}")


    return RAGQAResponse(data={"answer":"您好，正在查询，请稍等..."})

if __name__ == "__main__":
    asyncio.run(rag_query_and_answer(RAGQARequest(question="请问BOM是什么？")))
