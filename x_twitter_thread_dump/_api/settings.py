from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    IMAGE_RENDERING_CONCURRENCY: int = 10
    LOGFIRE_TOKEN: str | None = None


settings = Settings()

if settings.LOGFIRE_TOKEN:
    import logfire

    logfire.configure(
        token=settings.LOGFIRE_TOKEN,
        service_name="x-twitter-thread-dump",
        environment="production",
    )

__all__ = [
    "settings",
]
