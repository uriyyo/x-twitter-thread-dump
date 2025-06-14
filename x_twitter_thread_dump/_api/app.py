import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from .router import router
from .sharable_brower_ctx import SharableBrowserCtx

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

parent_package, _ = __name__.rsplit(".", 1)

logger = logging.getLogger(parent_package)
logger.setLevel(logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[Any]:
    async with SharableBrowserCtx() as browser_ctx:
        yield {"browser_ctx": browser_ctx}


app = FastAPI(
    title="X Twitter Thread Dump Debugger",
    description="A simple API to for x-twitter-thread-dump library",
    lifespan=lifespan,
    version="0.1.0",
    redoc_url=None,
    docs_url=None,
    middleware=[
        Middleware(GZipMiddleware),
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Allow all origins for debugging purposes
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        ),
    ],
)
app.include_router(router)
