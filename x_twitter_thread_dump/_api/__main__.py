from x_twitter_thread_dump._api.app import app

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app)
