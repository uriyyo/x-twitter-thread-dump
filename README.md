# X Twitter Thread Dump

<p align="center">
  <img src="docs/favicon.svg" alt="X Twitter Thread Dump Favicon" width="100"/>
</p>

X Twitter Thread Dump is a Python tool designed to capture and save Twitter threads as images. It offers both a command-line interface for quick captures and a web API for programmatic access.

## Key Features

*   **Thread Capturing:** Saves entire Twitter threads into image format.
*   **Dual Interface:** Usable as a CLI tool or a web API.
*   **Asynchronous Operations:** Built with async support for efficient handling of requests.

## Overview

The project allows users to easily convert Twitter threads into shareable images. The CLI is suitable for manual, on-demand captures, while the API allows integration into other services or automated workflows.

For detailed installation and usage instructions, please refer to the project's documentation or use the help options provided by the CLI and API.

```shell
uv run to-image --tweet-url <tweet_url>
```

## Project Structure

The codebase is organized into modules for handling browser interactions, image generation, API routing, and command-line parsing. Key components include:

*   `x_twitter_thread_dump/`: Main package containing core logic.
*   `x_twitter_thread_dump/_api/`: FastAPI application for the web API.

## Contributing

Contributions to the project are welcome. Please refer to standard open-source contribution practices.

## License

This project is licensed under the MIT License. See the `LICENSE` file for more details.
