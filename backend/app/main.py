from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, engine

from app.routes import auth, complaints, cases, tasks, capa, reports, webhook

app = FastAPI(
    title="QualiTrace AI",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(complaints.router)
app.include_router(cases.router)
app.include_router(tasks.router)
app.include_router(capa.router)
app.include_router(reports.router)
app.include_router(webhook.router)

@app.on_event("startup")
async def startup_event():
    Base.metadata.create_all(bind=engine)


@app.get("/")
async def health_check():
    return {"status": "ok", "project": "QualiTrace AI"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
