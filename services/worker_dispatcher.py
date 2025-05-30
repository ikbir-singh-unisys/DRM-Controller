# controller/services/worker_dispatcher.py
from db.session import SessionLocal
from db import crud, models
from config.settings import settings
from services.ec2_manager import start_instance, stop_instance, is_instance_running
from datetime import datetime, timezone, timedelta
import logging
import time
import requests

from types import SimpleNamespace

logger = logging.getLogger(__name__)

MAX_JOBS_PER_WORKER = settings.MAX_JOBS_PER_WORKER
MAX_CONCURRENT_JOBS = settings.MAX_CONCURRENT_JOBS
IDLE_TIMEOUT = timedelta(minutes=settings.POLL_INTERVAL)
IS_PRODUCTION = settings.IS_PRODUCTION
WORKERPORT = settings.WORKERPORT


class WorkerDispatcher:
    def __init__(self):
        pass

    def get_available_worker(self, db):
        if IS_PRODUCTION:
            workers = db.query(models.WorkerInstance).all()
            for worker in workers:
                if worker.current_jobs < worker.max_jobs:

                    if not worker.is_active:
                        print(f"Starting instance {worker.name}...")
                        start_instance(worker.instance_id, worker.ec2_credential_id)

                        # Step 1: Wait for instance to enter 'running' state
                        while not is_instance_running(worker.instance_id, worker.ec2_credential_id):
                            print(f"Waiting for {worker.name} to boot EC2...")
                            time.sleep(5)

                        print(f"EC2 instance for {worker.name} is running.")

                        # Step 2: Wait for FastAPI service to respond on /api/ping
                        worker_url = f"http://{worker.public_ip}:9000/health"
                        for _ in range(20):  # Try for ~20 x 3s = 60s
                            try:
                                response = requests.get(worker_url, timeout=2)
                                if response.status_code == 200:
                                    print(f"FastAPI on {worker.name} is ready.")
                                    break
                            except requests.exceptions.RequestException:
                                pass
                            print(f"Waiting for {worker.name} API to become ready...")
                            time.sleep(3)
                        else:
                            logger.error(f"FastAPI on {worker.name} not responding. Skipping.")
                            continue

                        # Step 3: Mark instance as active
                        worker.is_active = True
                        db.commit()

                    return worker
                
            return None
        else:
            # Local development mode: use a dummy/local worker
            print("Running in local mode - using localhost worker")
            worker = SimpleNamespace()
            worker.public_ip = "localhost"
            worker.name = "localhost"
            return worker
    

    def dispatch_pending_jobs(self):
        db = SessionLocal()
        try:
            running = crud.count_running_jobs(db)
            slots_available = MAX_CONCURRENT_JOBS - running
            if slots_available <= 0:
                print("Max concurrent jobs running. Waiting...")
                return

            pending_jobs = crud.get_pending_jobs(db, limit=slots_available)
            for job in pending_jobs:
                worker = self.get_available_worker(db)
                if not worker:
                    logger.warning("No available worker found.")
                    break

                worker_url = f"http://{worker.public_ip}:{WORKERPORT}"

                print(f"Dispatching {job.job_id} to {worker.name}")

                crud.update_job_status(db, job.job_id, "dispatched", progress=5)

                if IS_PRODUCTION:
                    worker.current_jobs += 1
                    worker.last_used = datetime.utcnow()
                    db.commit()

                job_data = {
                    "job_id": job.job_id,
                    "content_id": job.content_id,
                    "client_id": job.client_id,
                    "s3_input_id": str(job.s3_input_id),
                    "s3_output_id": str(job.s3_output_id),
                    "is_paid": job.is_paid,
                    "upload_to_s3": job.upload_to_s3,
                    "s3_source": job.s3_source,
                    "s3_destination": job.s3_destination,
                    "already_transcoded": job.already_transcoded,
                }

                try:
                    response = requests.post(f"{worker_url}/api/run-job", json=job_data, timeout=10)
                    if response.status_code == 200:
                        crud.update_job_status(db, job.job_id, "processing", progress=10)
                        print(f"Job {job.job_id} dispatched to {worker.name}")
                    else:
                        crud.update_job_status(db, job.job_id, "failed", error=response.text)
                        logger.error(f"Job {job.job_id} dispatch failed")
                        if IS_PRODUCTION:
                            worker.current_jobs -= 1
                            db.commit()
                except Exception as e:
                    crud.update_job_status(db, job.job_id, "failed", error=str(e))
                    logger.error(f"Error dispatching job: {e}")
                    if IS_PRODUCTION:
                        worker.current_jobs -= 1
                        db.commit()

            if IS_PRODUCTION:
                self.shutdown_idle_workers(db)

        finally:
            db.close()

    def shutdown_idle_workers(self, db):
        if not IS_PRODUCTION:
            return  # Do nothing in development

        workers = db.query(models.WorkerInstance).filter(
            models.WorkerInstance.current_jobs == 0,
            models.WorkerInstance.is_active == True
        ).all()
        for worker in workers:
            print(f"Shutting down idle worker {worker.name}")
            stop_instance(worker.instance_id, worker.ec2_credential_id)
            worker.is_active = False
            db.commit()


    def monitor_workers(self):
        if not IS_PRODUCTION:
            return  # Skip monitoring in dev

        db = SessionLocal()
        try:
            workers = db.query(models.WorkerInstance).filter(
                models.WorkerInstance.is_active == True
            ).all()
            for worker in workers:
                if worker.current_jobs == 0 and datetime.now(timezone.utc) - worker.last_active > IDLE_TIMEOUT:
                    stop_instance(worker.instance_id, worker.ec2_credential_id)
                    worker.is_active = False
                    db.commit()
                    print(f"Stopped idle worker {worker.name}")
        finally:
            db.close()
