from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    groq_api_key: str = Field(default="placeholder", env="GROQ_API_KEY")
    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/syllabusai",
        env="DATABASE_URL",
    )
    allowed_origins: str = Field(default="http://localhost:5173", env="ALLOWED_ORIGINS")
    embedding_model: str = Field(default="all-MiniLM-L6-v2", env="EMBEDDING_MODEL")
    jwt_secret: str = Field(default="syllabusai-super-secret-key-2024", env="JWT_SECRET")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
