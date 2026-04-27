from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="Lumina Insight AI Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/process_query")
async def process_query():
    return {"status": "stub"}


@app.post("/upload")
async def upload():
    return {"status": "stub"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
