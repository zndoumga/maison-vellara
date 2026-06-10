from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from routers import ecom, wholesale

app = FastAPI(
    title="Maison Vellara Data API",
    description="Internal data API serving online store and wholesale partner data.",
    version="1.0.0",
    docs_url="/docs",
)

app.include_router(ecom.router)
app.include_router(wholesale.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "maison-vellara-api"}
