from functools import lru_cache

from pydantic import Field, PostgresDsn, RedisDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
import os
from dotenv import load_dotenv


class AppSettings(BaseSettings):
    # 项目基础配置
    PROJECT_NAME: str | None = "PLM2.0"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field(default='development', pattern='^(development|staging|production)$')
    # DEBUG: bool = True
    LOG_LEVEL: str = Field(default='DEBUG', pattern='^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$')

    # 服务器配置
    SERVER_HOST: str = '127.0.0.1'
    SERVER_PORT: int = 8000
    API_PREFIX: str = '/api'

    # model_config = SettingsConfigDict(  # SettingsConfigDict 替代了旧版本 Config 内部类
    #     env_file='.env.development',
    #     env_prefix='',
    #     env_file_encoding='utf-8'
    # )


class RepSettings(BaseSettings):
    # 数据库配置（使用 SecretStr 隐藏敏感信息）
    POSTGRE_DATABASE_URL: PostgresDsn | None = None
    ASYNC_POSTGRE_DATABASE_URL: PostgresDsn | None = None

    POSTGRES_USER: SecretStr | None = None
    POSTGRES_PASSWORD: SecretStr | None = None
    POSTGRES_DATABASE: SecretStr | None = None

    POSTGRES_HOST: SecretStr | None = None
    POSTGRES_PORT: SecretStr | None = None
    POSTGRES_URL: SecretStr | None = None
    POSTGRES_SYNC_URL: SecretStr | None = None
    POSTGRES_ASYNC_URL: SecretStr | None = None

    POSTGRES_POOL_SIZE: int = Field(default=64, description="postgre pool size")
    POSTGRES_MAX_OVERFLOW: int = Field(default=64, description="postgre max overflow")
    POSTGRES_POOL_PRE_PIN: bool = Field(default=True, description="postgre pool pre pin")
    POSTGRES_AUTO_COMMIT: bool = Field(default=False, description="postgre auto commit")
    POSTGRES_AUTO_FLUSH: bool = Field(default=False, description="postgre auto flush")

    # Minio配置
    MINIO_ENDPOINT: SecretStr | None = None
    MINIO_ACCESSKEY: SecretStr | None = None
    MINIO_SECRETKEY: SecretStr | None = None
    MINIO_BUCKET: str | None = None

    MILVUS_URI: SecretStr | None = None
    MILVUS_TOKEN: SecretStr | None = None
    MILVUS_HOST: SecretStr | None = None

    # Redis配置
    REDIS_URL: RedisDsn | None = None

    model_config = SettingsConfigDict(  # SettingsConfigDict 替代了旧版本 Config 内部类
        # env_file='.env.development', # 使用load_dotenv加载
        env_prefix='',
        env_file_encoding='utf-8',
        extra='ignore'
    )

    def sync_repo_sets_to_env(self):
        os.environ['POSTGRES_USER'] = self.POSTGRES_USER.get_secret_value() if self.POSTGRES_USER else ""
        os.environ['POSTGRES_PASSWORD'] = self.POSTGRES_PASSWORD.get_secret_value() if self.POSTGRES_PASSWORD else ""
        os.environ['POSTGRES_DATABASE'] = self.POSTGRES_DATABASE.get_secret_value() if self.POSTGRES_DATABASE else ""


class LLMSettings(BaseSettings):
    # 外部服务密钥
    HIK_MAAS_URL: SecretStr | None = None
    HIK_MAAS_LLM: SecretStr | None = None
    HIK_MAAS_EMB: SecretStr | None = None
    HIK_MAAS_KEY: SecretStr | None = None
    HIK_MAAS_RERANKER: SecretStr | None = None
    HIK_MAAS_RERANKER_URL: SecretStr | None = None
    HIK_MAAS_TIMEOUT: int = 100
    HIK_MAAS_TOKENIZER: SecretStr | None = None
    ENABLE_LLM_CACHE: bool = True
    ENABLE_LLM_CACHE_FOR_EXTRACT: bool = True
    MAX_ASYNC: int = 100
    MAX_TOKENS_SIZE: int = 8192
    TEMPERATURE: float = 0.5

    model_config = SettingsConfigDict(  # SettingsConfigDict 替代了旧版本 Config 内部类
        # env_file='.env.development', # 使用load_dotenv加载
        env_prefix='',
        env_file_encoding='utf-8',
        extra='ignore',

    )


class RAGSettings(BaseSettings):
    # 策略配置
    CHUNK_SIZE: int = 1000
    EMBEDDING_DIM: int = 1024
    MAX_EMBED_TOKENS: int = 8192
    CHUNK_OVERLAP_SIZE: int = 20
    COSINE_THRESHOLD: float = 0.2

    KV_STORAGE: str = 'PGKVStorage'
    GRAPH_STORAGE: str = 'PGGraphStorage'
    DOC_STATUS_STORAGE: str = "PGDocStatusStorage"
    VECTOR_STORAGE: str = "PGVectorStorage"

    MAX_GRAPH_NODES: int = 100000
    SUMMARY_LANGUAGE: str = Field(default='Chinese', pattern='^(Chinese|English)$')

    MAX_PARALLEL_INSERT: int = 100


class FileSettings(BaseSettings):
    FILE_SAVE_PATH: str | None = None
    FILE_PARSE_OUTPUT_PATH: str | None = None

    model_config = SettingsConfigDict(  # SettingsConfigDict 替代了旧版本 Config 内部类
        # env_file='.env.development', # 使用load_dotenv加载
        env_prefix='',
        env_file_encoding='utf-8',
        extra='ignore',

    )


class UISettings(BaseSettings):
    RAG_WEB_UI_PATH: str | None = None
    model_config = SettingsConfigDict(  # SettingsConfigDict 替代了旧版本 Config 内部类
        # env_file='.env.development', # 使用load_dotenv加载
        env_prefix='',
        env_file_encoding='utf-8',
        extra='ignore',

    )


@lru_cache
def get_app_settings():
    return AppSettings()


@lru_cache
def get_rep_settings():
    return RepSettings()


@lru_cache
def get_llm_settings():
    return LLMSettings()


@lru_cache
def get_rag_settings():
    return RAGSettings()


@lru_cache
def get_file_settings():
    return FileSettings()


@lru_cache
def get_ui_settings():
    return UISettings()


# 默认从运行目录加载.env
# 部署服务器时，将BASE_DIR去掉，从根路径执行 python plm/api/fast_api.py 会从项目路径下加载所有.env.*文件
# BASE_DIR 只是为了在windows测试使用
BASE_DIR = r"C:/Users/hupeiwen6/Desktop/PLM2.0/"
load_dotenv(f'{BASE_DIR}.env', override=True, interpolate=True)  # 加载基础配置，包含ENVIRONMENT
load_dotenv(f'{BASE_DIR}/.env.{os.getenv('ENVIRONMENT', 'development')}', override=True,
            interpolate=True)  # interpoldate 解决.env文件中使用${}引用上下文变量

# 必须放在load_dotenv下面，否则加载不到配置信息
app_settings = get_app_settings()
rep_settings = get_rep_settings()
rep_settings.sync_repo_sets_to_env()
llm_settings = get_llm_settings()
rag_settings = get_rag_settings()
file_settings = get_file_settings()
ui_settings = get_ui_settings()

if __name__ == '__main__':
    print(get_app_settings())
    print(get_rep_settings().POSTGRES_URL.get_secret_value())
    print(get_rep_settings().POSTGRES_SYNC_URL.get_secret_value())
