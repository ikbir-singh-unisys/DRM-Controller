# controller/api/main.py
from fastapi import APIRouter, HTTPException, Depends, Request, FastAPI
from api import endpoints

from fastapi.middleware.cors import CORSMiddleware

from services.worker_dispatcher import WorkerDispatcher
import threading, time

from sqlalchemy.orm import Session
from db.session import get_db
from api.schemas import JobCompleteSchema
from db import crud
import socket
import platform

from api.route import client, credentials, job, dashboard, auth

app = FastAPI()

# Allow requests from your frontend
origins = ["*"]
# origins = [
#     "http://localhost:5173",  # Vite dev server
#     "http://127.0.0.1:5173",
# ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Or use ["*"] for all origins (not recommended in prod)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(endpoints.router)

# app.include_router(api_router)

app.include_router(client.router)
app.include_router(credentials.router)
app.include_router(job.router)
app.include_router(dashboard.router)
app.include_router(auth.router)

dispatcher = WorkerDispatcher()

def start_dispatch_loop():
    while True:
        dispatcher.dispatch_pending_jobs()
        time.sleep(5)  # Adjust polling interval as needed

@app.on_event("startup")
def start_background_tasks():
    threading.Thread(target=start_dispatch_loop, daemon=True).start()


@app.get("/")
def health():
    return {"status": "Controller is Running!"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/test-info")
def get_machine_info(request: Request):
    client_ip = request.headers.get("x-forwarded-for") or request.client.host
    hostname = socket.gethostname()
    machine_ip = socket.gethostbyname(hostname)
    os_info = platform.system()
    arch = platform.machine()

    return {
        "client_ip": client_ip,        
        "hostname": hostname,         
        "machine_ip": machine_ip,      
        "os": os_info,                 
        "arch": arch                
    }


@app.post("/api/job-complete")
def job_complete(payload: JobCompleteSchema, db: Session = Depends(get_db)):
    job = crud.get_job_by_id(db, payload.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    crud.update_job_status(
        db,
        job_id=payload.job_id,
        status=payload.status,
        progress=payload.progress or 100,
        error=payload.error
    )

    return {"success": True, "message": f"Job {payload.job_id} marked as {payload.status}"}