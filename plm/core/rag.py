from loguru import logger
from transformers import AutoTokenizer

from lightrag import LightRAG
from lightrag.chunk import custom_chunking
from lightrag.llm.openai import openai_complete_if_cache, openai_embed
from lightrag.rerank import custom_rerank
from lightrag.types import GPTKeywordExtractionFormat
from lightrag.utils import EmbeddingFunc
from plm.conf.settings import (
    app_settings,
    rep_settings,
    llm_settings,
    rag_settings,
)


async def hik_openai_model_complete(prompt,
                                    system_prompt=None,
                                    history_messages=None,
                                    keyword_extraction=False,
                                    **kwargs,
                                    ) -> str:
    keyword_extraction = kwargs.pop("keyword_extraction", None)
    if keyword_extraction:
        kwargs["response_format"] = GPTKeywordExtractionFormat
    if history_messages is None:
        history_messages = []
    kwargs["temperature"] = llm_settings.TEMPERATURE
    return await openai_complete_if_cache(
        llm_settings.HIK_MAAS_LLM.get_secret_value(),
        prompt,
        system_prompt=system_prompt,
        history_messages=history_messages,
        base_url=llm_settings.HIK_MAAS_URL.get_secret_value(),
        api_key=llm_settings.HIK_MAAS_KEY.get_secret_value(),
        **kwargs,
    )


def embedding_func():
    return EmbeddingFunc(
        embedding_dim=rag_settings.EMBEDDING_DIM,
        max_token_size=rag_settings.MAX_EMBED_TOKENS,
        func=lambda texts: openai_embed(
            texts,
            model=llm_settings.HIK_MAAS_EMB.get_secret_value(),
            api_key=llm_settings.HIK_MAAS_KEY.get_secret_value(),
            base_url=llm_settings.HIK_MAAS_URL.get_secret_value()
        ),
    )


def tokenizer():
    return AutoTokenizer.from_pretrained(llm_settings.HIK_MAAS_TOKENIZER.get_secret_value())  # local tokenizer


async def rerank_model_func(
        query: str, documents: list, top_n: int = None, **kwargs
):
    """Server rerank function with configuration from environment variables"""
    return await custom_rerank(
        query=query,
        documents=documents,
        model=llm_settings.HIK_MAAS_RERANKER.get_secret_value(),
        base_url=llm_settings.HIK_MAAS_URL.get_secret_value(),
        api_key=llm_settings.HIK_MAAS_KEY.get_secret_value(),
        top_n=top_n,
        **kwargs,
    )

def init_rag():
   return LightRAG(
        # working_dir=args.working_dir,
        # workspace=args.workspace,
        llm_model_func=hik_openai_model_complete,  # azure_openai_model_complete
        chunking_func=custom_chunking,
        chunk_token_size=int(rag_settings.CHUNK_SIZE),
        chunk_overlap_token_size=int(rag_settings.CHUNK_OVERLAP_SIZE),
        llm_model_kwargs={
            "timeout": llm_settings.HIK_MAAS_TIMEOUT,
        },
        llm_model_name=llm_settings.HIK_MAAS_LLM.get_secret_value(),
        llm_model_max_async=llm_settings.MAX_ASYNC,
        llm_model_max_token_size=llm_settings.MAX_TOKENS_SIZE,
        embedding_func=embedding_func(),
        tokenizer=tokenizer(),
        kv_storage=rag_settings.KV_STORAGE,
        graph_storage=rag_settings.GRAPH_STORAGE,
        vector_storage=rag_settings.VECTOR_STORAGE,
        doc_status_storage=rag_settings.DOC_STATUS_STORAGE,
        vector_db_storage_cls_kwargs={
            "cosine_better_than_threshold": rag_settings.COSINE_THRESHOLD  # TODO:20
        },
        enable_llm_cache_for_entity_extract=llm_settings.ENABLE_LLM_CACHE_FOR_EXTRACT,
        enable_llm_cache=llm_settings.ENABLE_LLM_CACHE,
        rerank_model_func=rerank_model_func,
        auto_manage_storages_states=False,
        max_parallel_insert=rag_settings.MAX_PARALLEL_INSERT,
        max_graph_nodes=rag_settings.MAX_GRAPH_NODES,
        addon_params={"language": rag_settings.SUMMARY_LANGUAGE},
    )

