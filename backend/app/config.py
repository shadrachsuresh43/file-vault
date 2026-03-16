from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg2://filevault:filevaultpw@localhost:5432/filevault"
    JWT_SECRET: str = "CHANGE_ME_IN_PROD"
    JWT_ALG: str = "HS256"
    ACCESS_TOKEN_MINUTES: int = 30
    CORS_ORIGINS: str = "http://localhost:5173"

    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str = ""
    USE_S3: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()