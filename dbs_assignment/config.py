from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    class Config:
        case_sensitive = True

    NAME: str

settings = Settings()
