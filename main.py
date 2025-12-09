from fastapi import FastAPI

app = FastAPI(
    title="TODO API + WebSocket + Background. Устинов Даниил Николаевич РИ-330948", 
    version="0.1.0",
)


@app.get("/ping")
async def ping():
    return {"message": "pong"}
