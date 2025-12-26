from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from routers import clinical, admin, reports, vision, chat

app = FastAPI(title="Medica AI API", version="1.1")

# Mount Web UI
app.mount("/ui", StaticFiles(directory="static", html=True), name="static")

# Include Routers
app.include_router(clinical.router)
app.include_router(reports.router)
app.include_router(vision.router)
app.include_router(chat.router)
app.include_router(admin.router)

@app.get("/")
async def root():
    # Redirect root to Web UI
    return RedirectResponse(url="/ui/")
