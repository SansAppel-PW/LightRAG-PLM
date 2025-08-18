from dotenv import load_dotenv
import os
from pydantic_settings import BaseSettings

dotenv_path = '/mnt/ssd1/italgo_dev14/hzm/code/plm'

class AppSetings(BaseSettings):
    """ Project """
    PROJECT_NAME: str | None = "online_search"
    APP_VERSION: str = "2.0.0"

    class Config:
        env_file = os.path.join(os.path.dirname(__file__),)
        env_file_encoding = 'utf-8'


settings = AppSetings(_env_file='', _env_file_encoding='utf-8')

assert load_dotenv(dotenv_path=dotenv_path, override=False)
