# controller/api/route/job.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from db.models import Job, Client
from db.session import get_db
from api.schemas import JobCreateRequest, JobCreateResponse, JobDetailResponse
from api.dependencies import get_current_client_data
from datetime import datetime, timezone
import uuid
from typing import List, Optional

from db.crud import create_job_with_tracks

router = APIRouter()

# Create Job
@router.post("/api/jobcreate", response_model=JobCreateResponse)
def create_job(
    request: JobCreateRequest,
    db: Session = Depends(get_db),
    auth=Depends(get_current_client_data)
):
    client_id = auth["client_id"]

    if auth["is_admin"]:
        if not request.client_id:
            raise HTTPException(status_code=400, detail="Admin must provide client_id")

        # Validate client_id exists and is active
        client = db.query(Client).filter_by(client_id=request.client_id, is_active=True).first()
        if not client:
            raise HTTPException(status_code=404, detail="Provided client_id does not exist or is inactive.")

        client_id = request.client_id  # Override client_id from request

    # Check for duplicates
    existing = db.query(Job).filter_by(content_id=request.content_id, client_id=client_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Job with this content_id already exists")

    job_id = f"{datetime.utcnow().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}"

    try:
        job_data = request.model_dump(exclude={"audio_tracks", "subtitle_tracks"})
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

# Get Job by Job ID
@router.get("/api/job/{job_id}", response_model=JobDetailResponse)
def get_job_by_id(
    job_id: str,
    db: Session = Depends(get_db),
    auth=Depends(get_current_client_data)
):
    job = db.query(Job).filter(Job.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if not auth["is_admin"] and job.client_id != auth["client_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    return job

# List Jobs (Optional filters via query params)
@router.get("/api/jobs", response_model=List[JobDetailResponse])
def list_jobs(
    db: Session = Depends(get_db),
    auth=Depends(get_current_client_data),
    job_id: Optional[str] = None,
    status: Optional[str] = None,
    progress: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    order: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
):
    query = db.query(Job)

    if not auth["is_admin"]:
        query = query.filter(Job.client_id == auth["client_id"])

    if job_id:
        query = query.filter(Job.job_id == job_id)

    if status:
        query = query.filter(Job.status == status)

    if progress is not None:
        query = query.filter(Job.progress >= progress)

    if date_from:
        query = query.filter(Job.created_at >= date_from)

    if date_to:
        query = query.filter(Job.created_at <= date_to)

    # Order by creation date
    if order == "asc":
        query = query.order_by(Job.created_at.asc())
    else:
        query = query.order_by(Job.created_at.desc())  # default to descending

    jobs = query.offset(offset).limit(limit).all()
    return jobs