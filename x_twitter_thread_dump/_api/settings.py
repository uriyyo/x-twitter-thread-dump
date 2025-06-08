from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }

    IMAGE_RENDERING_CONCURRENCY: int = 10


settings = Settings()

__all__ = [
    "settings",
]
