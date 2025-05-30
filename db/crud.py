# controller/db/crud.py
from sqlalchemy.orm import Session
from db import models
from sqlalchemy import func
from datetime import datetime
from collections import defaultdict
from api.schemas import S3CredentialCreate, S3CredentialUpdate

from typing import Optional

def create_s3_credential(db: Session, cred: S3CredentialCreate, client_id: str):
    # Ensure we use provided client_id (admin) or current user's ID (client)
    db_cred = models.S3Credential(**cred.dict(exclude={"client_id"}), client_id=client_id)
    db.add(db_cred)
    db.commit()
    db.refresh(db_cred)
    return db_cred


def get_s3_credentials_filtered(
    db: Session,
    client_id: Optional[str] = None,
    s3_id: Optional[int] = None,
    requester_id: Optional[str] = None,
    is_admin: bool = False
):
    query = db.query(models.S3Credential)

    if s3_id:
        query = query.filter(models.S3Credential.id == s3_id)

    if client_id:
        query = query.filter(models.S3Credential.client_id == client_id)

    # Only non-admins should be restricted to their own credentials
    if not is_admin and requester_id:
        query = query.filter(models.S3Credential.client_id == requester_id)

    return query.all()


def get_s3_credentials_for_client(db: Session, client_id: str):
    return db.query(models.S3Credential).filter(models.S3Credential.client_id == client_id).all()


def update_s3_credential(
    db: Session,
    credential_id: int,
    updates: S3CredentialUpdate,
    client_id: str,
    is_admin: bool = False
):
    cred = db.query(models.S3Credential).filter(models.S3Credential.id == credential_id).first()
    if not cred:
        return None
    if not is_admin and cred.client_id != client_id:
        return None

    for key, value in updates.dict(exclude_unset=True).items():
        setattr(cred, key, value)
    db.commit()
    db.refresh(cred)
    return cred


def create_job(db: Session, job_id: str, job_data):
    db_job = models.Job(job_id=job_id, **job_data.dict())
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job


def create_job_with_tracks(db: Session, job_id: str, job_data: dict, audio_tracks: list, subtitle_tracks: list):
    # Create main job instance with all fields
    db_job = models.Job(
        job_id=job_id,
        content_id=job_data['content_id'],
        client_id=job_data.get('client_id'),
        s3_input_id=job_data['s3_input_id'],
        s3_output_id=job_data.get('s3_output_id'),
        is_paid=job_data.get('is_paid', False),
        upload_to_s3=job_data.get('upload_to_s3', False),
        s3_source=job_data['s3_source'],
        s3_destination=job_data.get('s3_destination'),
        already_transcoded=job_data.get('already_transcoded', False),
        callback_url=job_data.get('callback_url'),
        status="queued",
        progress=0,
    )

    # Append audio tracks
    for audio in audio_tracks:
        db_audio = models.JobAudioTrack(
            language=audio.language,
            file_path=audio.file_path
        )
        db_job.audio_tracks.append(db_audio)

    # Append subtitle tracks
    for subtitle in subtitle_tracks:
        db_subtitle = models.JobSubtitleTrack(
            language=subtitle.language,
            file_path=subtitle.file_path
        )
        db_job.subtitle_tracks.append(db_subtitle)

    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job

def get_next_job(db: Session):
    return db.query(models.Job).filter(models.Job.status == "queued").order_by(models.Job.created_at.asc()).first()

def update_job_status(db: Session, job_id: str, status: str, progress: int = 0, error: str = None):
    job = db.query(models.Job).filter(models.Job.job_id == job_id).first()
    if job:
        job.status = status
        job.progress = progress
        if error:
            job.error = error
        db.commit()
    return job

def get_pending_jobs(db: Session, limit: int = 2):
    return db.query(models.Job)\
        .filter(models.Job.status.in_(["queued"]))\
        .order_by(models.Job.created_at.asc())\
        .limit(limit)\
        .all()

def count_running_jobs(db: Session):
    return db.query(models.Job).filter(models.Job.status.in_(["processing", "dispatched"])).count()

def get_job_by_id(db: Session, job_id: str):
    return db.query(models.Job).filter(models.Job.job_id == job_id).first()


def get_dashboard_summary_data(
    db: Session,
    auth: dict,  # should contain 'is_admin' and 'client_id'
    date_from: datetime = None,
    date_to: datetime = None,
):
    """
    Returns job and worker summary data based on user role.
    Admins get overall data.
    Clients get data limited to their own jobs.
    Supports optional date filtering.
    """
    query = db.query(models.Job)

    if not auth["is_admin"]:
        query = query.filter(models.Job.client_id == auth["client_id"])

    if date_from:
        query = query.filter(models.Job.created_at >= date_from)
    if date_to:
        query = query.filter(models.Job.created_at <= date_to)

    jobs = query.all()

    total_jobs = len(jobs)
    total_duration = 0
    jobs_by_status = defaultdict(int)
    duration_by_status = defaultdict(int)

    for job in jobs:
        jobs_by_status[job.status] += 1
        if job.content_duration:
            total_duration += job.content_duration
            duration_by_status[job.status] += job.content_duration

    summary = {
        "total_jobs": total_jobs,
        "total_duration_seconds": total_duration,
        "jobs_by_status": dict(jobs_by_status),
        "duration_by_status_seconds": dict(duration_by_status),
    }

    if auth["is_admin"]:
        # Jobs grouped by client
        client_summary = (
            db.query(
                models.Job.client_id,
                func.count(models.Job.id),
                func.coalesce(func.sum(models.Job.content_duration), 0)
            )
            .group_by(models.Job.client_id)
            .all()
        )

        # Jobs grouped by worker (machine)
        worker_summary = (
            db.query(
                models.Job.machine,
                func.count(models.Job.id),
                func.coalesce(func.sum(models.Job.content_duration), 0)
            )
            .filter(models.Job.machine.isnot(None))
            .group_by(models.Job.machine)
            .all()
        )

        # All EC2 worker instances
        all_workers = db.query(models.WorkerInstance).all()

        summary.update({
            "client_summary": [
                {
                    "client_id": cid,
                    "job_count": job_count,
                    "total_duration": duration
                }
                for cid, job_count, duration in client_summary
            ],
            "worker_summary": [
                {
                    "worker": machine,
                    "job_count": job_count,
                    "total_duration": duration
                }
                for machine, job_count, duration in worker_summary
            ],
            "all_workers": [
                {
                    "id": w.id,
                    "name": w.name,
                    "instance_id": w.instance_id,
                    "public_ip": w.public_ip,
                    "current_jobs": w.current_jobs,
                    "max_jobs": w.max_jobs,
                    "is_active": w.is_active,
                    "last_used": w.last_used,
                    "last_active": w.last_active
                }
                for w in all_workers
            ]
        })

    return summary