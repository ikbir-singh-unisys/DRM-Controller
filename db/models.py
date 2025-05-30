# controller/db/models.py
from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from db.session import Base
from datetime import datetime, timezone


class S3Credential(Base):
    __tablename__ = "s3_credentials"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50))
    access_key = Column(String(100))
    secret_key = Column(String(100))
    bucket = Column(String(100))
    region = Column(String(100))

    client_id = Column(String(50), ForeignKey("clients.client_id"))
    client = relationship("Client", back_populates="s3_credentials")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(50), unique=True, nullable=False)
    content_id = Column(String(255), nullable=False)
    client_id = Column(String(50), ForeignKey("clients.client_id"), nullable=False)
    s3_input_id = Column(Integer, nullable=False)
    s3_output_id = Column(Integer, nullable=True)
    content_duration = Column(Integer, nullable=True)
    is_paid = Column(Boolean, default=False)
    upload_to_s3 = Column(Boolean, default=True)
    s3_source = Column(Text, nullable=True)
    s3_destination = Column(Text, nullable=True)
    already_transcoded = Column(Boolean, default=False)
    callback_url = Column(Text, default=False, nullable=True)
    status = Column(String(20), default="queued")
    progress = Column(Integer, default=0)
    error = Column(Text, nullable=True)
    requester_ip = Column(String(100), nullable=True)
    machine = Column(String(100), nullable=True)
    os = Column(String(100), nullable=True)
    arch = Column(String(100), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime, server_default=func.now())

    logs = relationship("JobLog", back_populates="parent_job", cascade="all, delete-orphan")
    client = relationship("Client", back_populates="jobs")
    audio_tracks = relationship("JobAudioTrack", back_populates="job", cascade="all, delete-orphan")
    subtitle_tracks = relationship("JobSubtitleTrack", back_populates="job", cascade="all, delete-orphan")


class JobLog(Base):
    __tablename__ = "job_logs"

    id = Column(Integer, primary_key=True, index=True)
    # job_id = Column(String(36), ForeignKey("jobs.job_id"), nullable=False)
    job_id = Column(String(36), ForeignKey("jobs.job_id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(50))
    event_value = Column(String(255))
    ip_address = Column(String(100))
    machine = Column(String(100))
    os = Column(String(100))
    arch = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    parent_job = relationship("Job", back_populates="logs")



class WorkerInstance(Base):
    __tablename__ = "worker_instances"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    instance_id = Column(String(50), nullable=False)
    public_ip = Column(String(50), nullable=False)
    current_jobs = Column(Integer, default=0)
    max_jobs = Column(Integer, default=3)
    is_active = Column(Boolean, default=False)
    last_used = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)

    ec2_credential_id = Column(Integer, ForeignKey("s3_credentials.id"), nullable=True)
    ec2_credentials = relationship("S3Credential", foreign_keys=[ec2_credential_id])


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=True)
    organization = Column(String(100), nullable=True)
    license_key = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    jobs = relationship("Job", back_populates="client", cascade="all, delete-orphan")
    s3_credentials = relationship("S3Credential", back_populates="client")



class JobAudioTrack(Base):
    __tablename__ = "job_audio_tracks"

    id = Column(Integer, primary_key=True)
    job_id = Column(String(50), ForeignKey("jobs.job_id", ondelete="CASCADE"))
    language = Column(String(10), nullable=False)
    file_path = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    job = relationship("Job", back_populates="audio_tracks")


class JobSubtitleTrack(Base):
    __tablename__ = "job_subtitle_tracks"

    id = Column(Integer, primary_key=True)
    job_id = Column(String(50), ForeignKey("jobs.job_id", ondelete="CASCADE"))
    language = Column(String(10), nullable=False)
    file_path = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    

    job = relationship("Job", back_populates="subtitle_tracks")
