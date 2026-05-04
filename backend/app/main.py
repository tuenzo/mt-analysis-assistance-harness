from fastapi import FastAPI

app = FastAPI(title="Business Analysis Companion Workspace")


@app.get("/health")
def health_check():
    return {"status": "ok"}
