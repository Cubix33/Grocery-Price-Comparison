"""
Utility for running Playwright coroutines on Windows under Uvicorn.

Problem: Uvicorn may create a SelectorEventLoop before our app module is
imported, making asyncio.set_event_loop_policy() ineffective.  SelectorEventLoop
does NOT support asyncio.create_subprocess_exec, which Playwright needs to
launch the browser process -- producing NotImplementedError at runtime.

Fix: Offload every Playwright call to a ThreadPoolExecutor thread that creates
its own ProactorEventLoop (or a fresh event loop on non-Windows platforms).
The calling FastAPI async handler simply awaits the result via run_in_executor.
"""

import asyncio
import sys
from collections.abc import Callable, Coroutine
from concurrent.futures import ThreadPoolExecutor
from typing import Any, TypeVar

T = TypeVar("T")

# Shared thread pool - two workers allows Blinkit + Instamart to run in parallel.
_playwright_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="playwright")


def _run_in_fresh_loop(coro_factory):
    """
    Synchronously run coro_factory() inside a brand-new event loop.
    On Windows the loop is explicitly a ProactorEventLoop so that
    asyncio.create_subprocess_exec works (required by Playwright).
    """
    if sys.platform == "win32":
        loop = asyncio.ProactorEventLoop()
    else:
        loop = asyncio.new_event_loop()

    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro_factory())
    finally:
        loop.close()
        asyncio.set_event_loop(None)


async def run_playwright(coro_factory):
    """
    Await a Playwright coroutine from any async context (e.g. a FastAPI endpoint).

    Usage:
        result = await run_playwright(lambda: my_playwright_async_fn(arg1, arg2))
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_playwright_pool, _run_in_fresh_loop, coro_factory)
