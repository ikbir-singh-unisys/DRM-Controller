# controller/api/endpoints.py
from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from db.session import get_db
from db import models
from api.schemas import S3CredentialCreate, S3CredentialResponse, JobCreateRequest, JobCreateResponse
from datetime import datetime, timezone
from pydantic import BaseModel
import uuid

import socket
import platform

from typing import Optional

from db.crud import create_job_with_tracks

router = APIRouter()

class StatusUpdateRequest(BaseModel):
    status: str

class ProgressUpdateRequest(BaseModel):
    progress: int
    duration: Optional[float] = None  # Accepts int, float, or null


@router.post("/credentials-old", response_model=S3CredentialResponse)
def create_s3_credential(cred: S3CredentialCreate, db: Session = Depends(get_db)):
    credential = models.S3Credential(**cred.dict())
    db.add(credential)
    db.commit()
    db.refresh(credential)
    return credential


@router.post("/api/process", response_model=JobCreateResponse)
def create_job(request: JobCreateRequest, db: Session = Depends(get_db)):
    existing_job = db.query(models.Job).filter_by(content_id=request.content_id).first()
    if existing_job:
        raise HTTPException(
            status_code=400,
            detail="A job with this content_id already exists."
        )

    job_id = f"{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}"
    # try:
    #     job_data = models.Job(
    #         job_id=job_id,
    #         content_id=request.content_id,
    #         client_id=request.client_id,
    #         s3_input_id=request.s3_input_id,
    #         s3_output_id=request.s3_output_id,
    #         is_paid=request.is_paid,
    #         upload_to_s3=request.upload_to_s3,
    #         s3_source=request.s3_source,
    #         s3_destination=request.s3_destination,
    #         already_transcoded=request.already_transcoded or False,
    #         status="queued",
    #         progress=0,
    #         created_at=datetime.now(timezone.utc),
    #         updated_at=datetime.now(timezone.utc),  # if using updated_at
    #     )
    #     db.add(job_data)
    #     db.commit()
    #     return JobCreateResponse(
    #         job_id=job_id,
    #         status="queued",
    #         message="Job queued successfully"
    #     )
    # except Exception as e:
    #     db.rollback()
    #     raise HTTPException(status_code=500, detail=f"Failed to queue job: {str(e)}")

    try:
        job_data = request.model_dump(exclude={"audio_tracks", "subtitle_tracks"})

        client_id = request.client_id or None
        if request.client_id:
            job_data["client_id"] = client_id

        db_job = create_job_with_tracks(
            db=db,
            job_id=job_id,
            job_data=job_data,
            audio_tracks=request.audio_tracks or [],
            subtitle_tracks=request.subtitle_tracks or []
        )

        return JobCreateResponse(
            job_id=db_job.job_id,
            status=db_job.status,
            message="Job queued successfully"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to queue job: {str(e)}")
    
@router.get("/api/queue/next", response_model=JobCreateRequest)
def get_next_job(db: Session = Depends(get_db)):
    job = db.query(models.Job).filter(models.Job.status == "queued").order_by(models.Job.created_at.asc()).first()
    if not job:
        raise HTTPException(status_code=404, detail="No jobs available")
    job.status = "processing"
    job.progress = 0
    db.commit()
    return job


@router.post("/queue/{job_id}/status")
def update_job_status(
    job_id: str,
    data: StatusUpdateRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    job = db.query(models.Job).filter(models.Job.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job.status = data.status
    job.updated_at = datetime.now(timezone.utc)

    # Extract machine/request info
    requester_ip = request.headers.get("x-forwarded-for", request.client.host)
    hostname = socket.gethostname()
    system = platform.system()
    arch = platform.machine()

    # Save info in job table
    job.requester_ip = requester_ip
    job.machine = hostname
    job.os = system
    job.arch = arch

    # Also insert into job_logs
    log_entry = models.JobLog(
        job_id=job_id,
        event_type="status_update",
        event_value=data.status,
        ip_address=requester_ip,
        machine=hostname,
        os=system,
        arch=arch
    )
    db.add(log_entry)

    print(f"job requester_ip : {job.requester_ip}")

    if job.progress == 100 or job.status == "completed" or job.status == "failed":
        # Decrement current_jobs for the worker
        worker = db.query(models.WorkerInstance).filter(
            models.WorkerInstance.public_ip == job.requester_ip  
        ).first()
        if worker and worker.current_jobs > 0:
            worker.current_jobs -= 1
            worker.last_active = datetime.now(timezone.utc)
            db.commit()

    db.commit()
    return {"job_id": job_id, "status": job.status}


@router.post("/queue/{job_id}/progress")
def update_job_progress(
    job_id: str,
    data: ProgressUpdateRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    job = db.query(models.Job).filter(models.Job.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if not (0 <= data.progress <= 100):
        raise HTTPException(status_code=400, detail="Progress must be between 0 and 100")

    job.progress = data.progress
    job.updated_at = datetime.now(timezone.utc)

    if data.duration is not None:
        job.content_duration = int(data.duration)

    # Extract requester machine details
    requester_ip = request.headers.get("x-forwarded-for", request.client.host)
    hostname = socket.gethostname()
    system = platform.system()
    arch = platform.machine()

    # Save in Job table
    job.requester_ip = requester_ip
    job.machine = hostname
    job.os = system
    job.arch = arch

    # Log to job_logs
    log_entry = models.JobLog(
        job_id=job_id,
        event_type="progress_update",
        event_value=str(data.progress),
        ip_address=requester_ip,
        machine=hostname,
        os=system,
        arch=arch
    )
    db.add(log_entry)

    db.commit()
    return {"job_id": job_id, "progress": job.progress}


@router.get("/queue/{job_id}/logs")
def get_job_logs(job_id: str, db: Session = Depends(get_db)):
    logs = db.query(models.JobLog).filter(models.JobLog.job_id == job_id).order_by(models.JobLog.created_at.asc()).all()
    return [
        {
            "event": log.event_type,
            "value": log.event_value,
            "ip": log.ip_address,
            "machine": log.machine,
            "os": log.os,
            "arch": log.arch,
            "timestamp": log.created_at
        }
        for log in logs
    ]