# controller/api/schemas.py
from pydantic import BaseModel, Field, HttpUrl, EmailStr
from typing import Optional, List
from uuid import UUID
from datetime import datetime

class S3CredentialCreate(BaseModel):
    name: str
    access_key: str
    secret_key: str
    bucket: str
    region: str
    client_id: Optional[str] = None  # Optional: Only admin can set this


class S3CredentialUpdate(BaseModel):
    name: Optional[str]
    access_key: Optional[str]
    secret_key: Optional[str]
    bucket: Optional[str]
    region: Optional[str]


class S3CredentialResponse(S3CredentialCreate):
    id: int
    client_id: str

    class Config:
        from_attributes = True


class JobAudioTrackCreate(BaseModel):
    language: str
    file_path: str

class JobSubtitleTrackCreate(BaseModel):
    language: str
    file_path: str

# class JobCreateRequest(BaseModel):
#     content_id: str
#     client_id: Optional[str] = None
#     s3_input_id: int
#     s3_output_id: Optional[int] = None
#     is_paid: Optional[bool] = False
#     upload_to_s3: bool = False
#     s3_source: str
#     s3_destination: Optional[str] = None
#     already_transcoded: Optional[bool] = False

class JobCreateRequest(BaseModel):
    content_id: str
    client_id: Optional[str] = None
    s3_input_id: int
    s3_output_id: Optional[int] = None
    is_paid: Optional[bool] = False
    upload_to_s3: bool = False
    s3_source: str
    s3_destination: Optional[str] = None
    already_transcoded: Optional[bool] = False
    callback_url: Optional[str] = None

    # Add lists of audio and subtitle tracks (optional)
    audio_tracks: Optional[List[JobAudioTrackCreate]] = []
    subtitle_tracks: Optional[List[JobSubtitleTrackCreate]] = []

class JobAudioTrackResponse(JobAudioTrackCreate):
    id: int

    class Config:
        from_attributes = True

class JobSubtitleTrackResponse(JobSubtitleTrackCreate):
    id: int

    class Config:
        from_attributes = True

class JobCreateResponse(BaseModel):
    job_id: str
    status: str
    message: str

class JobCompleteSchema(BaseModel):
    job_id: UUID
    status: str = Field(..., example="completed")  # e.g., "completed", "failed"
    progress: Optional[int] = 100
    error: Optional[str] = None


# class JobDetailResponse(BaseModel):
#     job_id: str
#     content_id: str
#     client_id: Optional[str]
#     s3_input_id: int  # <- Change from str to int
#     s3_output_id: Optional[int]  # <- Change from str to int
#     is_paid: bool
#     upload_to_s3: bool
#     s3_source: str
#     s3_destination: Optional[str]
#     already_transcoded: Optional[bool]
#     status: str
#     progress: int
#     created_at: datetime
#     updated_at: datetime

#     class Config:
#         from_attributes = True


class JobDetailResponse(BaseModel):
    job_id: str
    content_id: str
    client_id: Optional[str]
    s3_input_id: int
    s3_output_id: Optional[int]
    is_paid: bool
    upload_to_s3: bool
    s3_source: str
    s3_destination: Optional[str]
    already_transcoded: Optional[bool]
    callback_url: Optional[str]
    status: str
    progress: int
    created_at: datetime
    updated_at: datetime

    audio_tracks: List[JobAudioTrackResponse] = []
    subtitle_tracks: List[JobSubtitleTrackResponse] = []

    class Config:
        from_attributes = True

class JobLog(BaseModel):
    id: int
    job_id: str
    event_type: str
    event_value: str
    created_at: datetime

    class Config:
        from_attributes = True


class WorkerInstance(BaseModel):
    id: int
    name: str
    instance_id: str
    public_ip: str
    current_jobs: int
    max_jobs: int
    is_active: bool
    last_used: Optional[datetime]
    last_active: Optional[datetime]

    class Config:
        from_attributes = True


class ClientBase(BaseModel):
    client_id: str
    name: str
    email: EmailStr
    organization: Optional[str] = None
    is_active: Optional[bool] = True


class ClientCreate(ClientBase):
    client_id: str
    license_key: str
    is_active: bool = True
    name: Optional[str]
    email: Optional[str]
    organization: Optional[str]

class ClientUpdate(BaseModel):
    name: Optional[str]
    email: Optional[EmailStr]
    organization: Optional[str]
    license_key: Optional[str]
    is_active: Optional[bool]


class ClientUpdateSchema(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    organization: Optional[str] = None


class ClientOut(ClientBase):
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TokenRequest(BaseModel):
    client_id: str
    license_key: str