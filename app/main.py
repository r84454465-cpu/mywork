# app/main.py
from fastapi import FastAPI
from .routes import router

app = FastAPI(title="FastAPI Replicate Gemini Demo")
app.include_router(router)


@app.get("/")
def root():
    return {"status": "ok", "message": "FastAPI Replicate Gemini Demo"}
