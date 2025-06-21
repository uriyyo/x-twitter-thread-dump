import subprocess

import logfire
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    IMAGE_RENDERING_CONCURRENCY: int = 10
    IMAGE_RENDERING_RETRIES: int = 3
    IMAGE_RENDERING_TIMEOUT: float = 60.0

    LOGFIRE_TOKEN: str | None = None


settings = Settings()

if settings.LOGFIRE_TOKEN:

    def _get_current_revision() -> str | None:
        try:
            return subprocess.check_output("git rev-parse HEAD", shell=True, text=True).strip()
        except subprocess.CalledProcessError:
            return None

    logfire.configure(
        token=settings.LOGFIRE_TOKEN,
        service_name="x-twitter-thread-dump",
        environment="production",
        code_source=logfire.CodeSource(
            repository="https://github.com/uriyyo/x-twitter-thread-dump",
            revision=_get_current_revision() or "main",
        ),
    )

__all__ = [
    "settings",
]
