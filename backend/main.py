from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from firebase_admin import credentials, initialize_app
import os
from contextlib import asynccontextmanager
from database import close_db_connection, init_db
from routers import generation, crud, feedback, integrations, upload, public_api, reporting, admin, knowledge_base, agent, user_settings
# from routers import reporting
# from routers import admin

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    yield
    # Shutdown
    close_db_connection()

# Initialize FastAPI app
app = FastAPI(
    title="AI Test Case Generator",
    description="This API generates test cases from requirements using AI.",
    version="1.0.0",
    lifespan=lifespan
)
    
# CORS Middleware
origins = [
    "http://localhost:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(generation.router)
app.include_router(crud.router)
app.include_router(feedback.router)
app.include_router(integrations.router)
app.include_router(upload.router)
app.include_router(public_api.router)
app.include_router(reporting.router)
app.include_router(admin.router)
app.include_router(knowledge_base.router)
app.include_router(agent.router)
app.include_router(user_settings.router)