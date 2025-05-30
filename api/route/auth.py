from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
from jose import jwt

from db.session import get_db
from db.models import Client
from api.schemas import TokenRequest
from starlette import status

SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

router = APIRouter()

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


@router.post("/auth/token")
def login_for_access_token(form_data: TokenRequest, db: Session = Depends(get_db)):
    client = db.query(Client).filter(
        Client.client_id == form_data.client_id,
        Client.license_key == form_data.license_key,
        Client.is_active == True
    ).first()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid client credentials",
        )

    access_token = create_access_token(
        data={"sub": client.client_id, "role": "admin" if client.client_id == "admin" else "user"}
    )
    return {"access_token": access_token, "token_type": "bearer"}
