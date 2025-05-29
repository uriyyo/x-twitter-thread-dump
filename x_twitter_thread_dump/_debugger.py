from typing import Annotated

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse

from x_twitter_thread_dump import x_twitter_thread_dump_async_client
from x_twitter_thread_dump.render import render_thread_html

app = FastAPI()


@app.get("/{tweet_id}")
async def get_tweet(
    tweet_id: str,
    *,
    show_connector_on_last: Annotated[bool, Query()] = False,
) -> HTMLResponse:
    async with x_twitter_thread_dump_async_client() as client:
        thread = await client.get_thread(tweet_id)
        await client._download_previews(thread)  # noqa: SLF001

    html = render_thread_html(
        thread,
        show_connector_on_last=show_connector_on_last,
    )

    return HTMLResponse(content=html)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app)
