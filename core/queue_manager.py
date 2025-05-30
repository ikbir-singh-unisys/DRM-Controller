# controller/core/queue_manager.py
from db.session import SessionLocal
from db import crud

def fetch_job():
    db = SessionLocal()
    try:
        job = crud.get_next_job(db)
        if not job:
            return None

        # Lock job
        job = crud.update_job_status(db, job.job_id, "processing", 5)
        return job
    finally:
        db.close()
