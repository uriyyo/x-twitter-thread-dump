from pathlib import Path

import click

from x_twitter_thread_dump import x_twitter_thread_dump_async_client
from x_twitter_thread_dump.utils import async_to_sync, get_tweet_id_from_url


@click.group()
def cli() -> None:
    pass


@cli.command(name="to-image")
@click.option(
    "--tweet-url",
    type=str,
    required=True,
    help="The URL of the tweet to dump as an image.",
)
@click.option(
    "--limit",
    type=int,
    default=None,
    help="Limit the number of tweets to include in the dump. If not specified, all tweets will be included.",
)
@click.option(
    "-o",
    "--output",
    type=click.Path(exists=False, writable=True, dir_okay=False),
    default="dump.png",
    help="The output file path for the image dump.",
)
@click.option(
    "--tweets-per-image",
    type=int,
    default=None,
    help="Number of tweets to include in each image. If not specified, all tweets will be included in a single image.",
)
@click.option(
    "--max-tweet-height",
    type=int,
    default=None,
    help="Maximum height of each tweet in pixels. If not specified, no limit will be applied.",
)
@click.option(
    "--timeout",
    type=int,
    default=None,
    help="Timeout for the request in seconds. If not specified, the default timeout will be used.",
)
@async_to_sync
async def dump_to_image(  # noqa: PLR0913
    *,
    tweet_url: str,
    limit: int | None = None,
    output: Path,
    tweets_per_image: int | None = None,
    max_tweet_height: int | None = None,
    timeout: int | None = None,
) -> None:
    tweet_id = get_tweet_id_from_url(tweet_url)

    async with x_twitter_thread_dump_async_client(timeout=timeout) as client:
        thread = await client.get_thread(tweet_id, limit=limit)
        result = await client.thread_to_image(
            thread,
            tweets_per_image=tweets_per_image,
            max_tweet_height=max_tweet_height,
        )

        match result:
            case []:
                raise RuntimeError(f"No tweets found for {tweet_id}")
            case [image]:
                image.save(output)
            case [*images] if len(images) > 1:
                for i, img in enumerate(images, 1):
                    img.save(output.with_name(f"{output.stem}_{i}.png"))


if __name__ == "__main__":
    cli()


__all__ = [
    "cli",
]
