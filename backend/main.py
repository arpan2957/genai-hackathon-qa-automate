from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import time
from audit import log_audit_event
from security import get_current_user, get_user_from_request
from fastapi import Depends

from database import lifespan
from routers import admin, crud, feedback, generation, integrations, knowledge_base, upload, reporting, public_api

# --- FastAPI App Initialization ---
app = FastAPI(
    title="AI Test Case Generator API",
    description="API for generating, managing, and exporting test cases using AI.",
    version="1.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
)

@app.middleware("http")
async def audit_log_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time

    user = await get_user_from_request(request)

    log_audit_event({
        "timestamp": time.time(),
        "user_id": user['uid'] if user else None,
        "email": user['email'] if user else None,
        "endpoint": request.url.path,
        "method": request.method,
        "status_code": response.status_code,
        "process_time": process_time
    })

    return response


app.include_router(generation.router)
app.include_router(crud.router)
app.include_router(knowledge_base.router)
app.include_router(admin.router)
app.include_router(integrations.router)
app.include_router(feedback.router)
app.include_router(upload.router)
app.include_router(reporting.router)
app.include_router(public_api.router)