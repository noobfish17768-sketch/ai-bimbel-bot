from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"msg": "VERSI BARU RAILWAY 999"}