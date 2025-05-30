from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from db.session import get_db
from db import crud
from api.schemas import S3CredentialCreate, S3CredentialUpdate, S3CredentialResponse
from api.dependencies import get_current_client_data

from typing import Optional

router = APIRouter()


@router.post("/credentials", response_model=S3CredentialResponse)
def create_credential(
    payload: S3CredentialCreate,
    db: Session = Depends(get_db),
    client_data=Depends(get_current_client_data)
):
    target_client_id = payload.client_id or client_data["client_id"]

    # Block non-admins from setting other client IDs
    if not client_data["is_admin"] and target_client_id != client_data["client_id"]:
        raise HTTPException(status_code=403, detail="Not allowed to create credentials for other clients")

    return crud.create_s3_credential(db, payload, target_client_id)


@router.get("/credentials", response_model=list[S3CredentialResponse], summary="List S3 Credentials")
def list_credentials(
    db: Session = Depends(get_db),
    client_data=Depends(get_current_client_data),
    client_id: Optional[str] = Query(None, description="Filter by client ID"),
    s3_id: Optional[int] = Query(None, description="Filter by S3 Credential ID")
):
    return crud.get_s3_credentials_filtered(
        db=db,
        client_id=client_id,
        s3_id=s3_id,
        requester_id=client_data["client_id"],
        is_admin=client_data["is_admin"]
    )


@router.put("/credentials/{credential_id}", response_model=S3CredentialResponse)
def update_credential(
    credential_id: int,
    payload: S3CredentialUpdate,
    db: Session = Depends(get_db),
    client_data=Depends(get_current_client_data)
):
    updated = crud.update_s3_credential(
        db, credential_id, payload, client_data["client_id"], client_data["is_admin"]
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Credential not found or access denied")
    return updated
