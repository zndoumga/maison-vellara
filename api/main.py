from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import ecom, wholesale

app = FastAPI(
    title="Maison Vellara Data API",
    description="Internal data API serving online store and wholesale partner data.",
    version="1.0.0",
    docs_url="/docs",
)

# The Vercel dashboard calls this API directly from the browser, so the
# response needs CORS headers. Read-only data behind an API key — open to all
# origins is fine here.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(ecom.router)
app.include_router(wholesale.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "maison-vellara-api"}
