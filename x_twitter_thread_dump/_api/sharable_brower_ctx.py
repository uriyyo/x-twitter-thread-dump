from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import cached_property
from typing import Any, Self

import logfire
from aiorwlock import RWLock
from playwright._impl._errors import TargetClosedError

from x_twitter_thread_dump._api.metrics import shared_browser_age
from x_twitter_thread_dump.browser import AsyncBrowser, async_browser

logger = logging.getLogger(__name__)


@dataclass
class _CurrentBrowserContext:
    stack: AsyncExitStack
    browser: AsyncBrowser
    lifetime: timedelta
    expired_at: datetime
    rw_lock: RWLock
    close_task: asyncio.Task[Any] | None = None

    @property
    def age(self) -> timedelta:
        return datetime.now() - (self.expired_at - self.lifetime)

    @property
    def is_expired(self) -> bool:
        return datetime.now() >= self.expired_at

    async def aclose(self) -> None:
        await self.stack.aclose()

    async def safe_aclose(
        self,
        *,
        posponed: bool = False,
    ) -> None:
        if posponed:
            initial_delay = (self.expired_at - datetime.now()).total_seconds()
            await asyncio.sleep(initial_delay)

        async with self.rw_lock.writer:
            logger.info("Closing browser context")
            await self.aclose()
            logger.info("Browser context closed")

    def schedule_close(self) -> None:
        if self.close_task is not None:
            self.close_task.cancel()
            self.close_task = None

        self.close_task = asyncio.create_task(
            self.safe_aclose(posponed=True),
            name="browser-context-close-task",
        )


@dataclass(kw_only=True)
class SharableBrowserCtx:
    lifetime: timedelta = timedelta(minutes=30)
    headless: bool = True

    ctx: _CurrentBrowserContext | None = None

    @cached_property
    def _rw_lock(self) -> RWLock:
        return RWLock()

    def _get_expired_at(self) -> datetime:
        return datetime.now() + self.lifetime

    @logfire.instrument("create new browser ctx")
    async def _create_new_ctx(self) -> _CurrentBrowserContext:
        async with self._rw_lock.writer:
            if self.ctx and not self.ctx.is_expired:
                logger.info("New context creation skipped, other task already created it")
                return self.ctx

            logger.info("Creating new browser context")

            stack = AsyncExitStack()
            browser = await stack.enter_async_context(async_browser(headless=self.headless))

            self.ctx = _CurrentBrowserContext(
                stack=stack,
                browser=browser,
                lifetime=self.lifetime,
                expired_at=self._get_expired_at(),
                rw_lock=self._rw_lock,
            )

            logger.info("New browser context created")
            return self.ctx

    @asynccontextmanager
    async def _acquire(self, *, _final: bool = False) -> AsyncIterator[AsyncBrowser]:
        if self.ctx is None or self.ctx.is_expired:
            await self._create_new_ctx()
        else:
            logger.info("Reusing existing browser context")

        cell_empty = False

        async with self._rw_lock.reader:
            if self.ctx is None and not _final:
                cell_empty = True
            elif self.ctx:
                shared_browser_age.record(
                    max(0, int(self.ctx.age.total_seconds())),
                )

                yield self.ctx.browser
                return

        if not cell_empty:
            return

        logger.info("Browser context is empty, try to call resolver again (final call)")

        async with self._acquire(_final=True) as browser:
            yield browser

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[AsyncBrowser]:
        try:
            async with self._acquire() as browser:
                yield browser
        except TargetClosedError:
            if self.ctx:
                logfire.info("Target closed error, closing browser context")
                logger.warning("Target closed error, force closing browser context")

                await self.ctx.safe_aclose()
                self.ctx = None

            raise

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_: object) -> None:
        if self.ctx is None:
            logger.warning("Browser context is not initialized, nothing to close")
            return

        if self.ctx.close_task is not None:
            logger.info("Cancelling browser context close task")
            self.ctx.close_task.cancel()
            self.ctx.close_task = None

        await self.ctx.safe_aclose()
        self.ctx = None


__all__ = [
    "SharableBrowserCtx",
]
