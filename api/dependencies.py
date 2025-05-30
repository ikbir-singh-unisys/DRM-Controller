# controller/api/dependencies.py
from fastapi import Depends, HTTPException, status, Header, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from db.session import get_db
from db.models import Client
from typing import Optional


# Secret config (move these to config/settings)
SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        client_id = payload.get("sub")
        role = payload.get("role")
        if not client_id or not role:
            raise JWTError("Missing claims")
        return {
            "client_id": client_id,
            "role": role
        }
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    decoded = decode_token(token)
    if decoded["role"] != "user":
        raise HTTPException(status_code=403, detail="User role required")
    client = db.query(Client).filter(Client.client_id == decoded["client_id"], Client.is_active == True).first()
    if not client:
        raise HTTPException(status_code=404, detail="User not found or inactive")
    return client

def get_current_admin(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    decoded = decode_token(token)
    if decoded["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    client = db.query(Client).filter(Client.client_id == decoded["client_id"], Client.is_active == True).first()
    if not client or client.client_id != "admin":
        raise HTTPException(status_code=403, detail="Admin not found or inactive")
    return client


def verify_client_auth(
    request: Request,
    x_client_id: Optional[str] = Header(None, convert_underscores=False),
    x_license_key: Optional[str] = Header(None, convert_underscores=False),
    db: Session = Depends(get_db)
):
    # Check for Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            client_id = payload.get("sub")
            role = payload.get("role")
            if not client_id or not role:
                raise HTTPException(status_code=401, detail="Invalid token")
            if role != "user":
                raise HTTPException(status_code=403, detail="User role required")

            client = db.query(Client).filter(Client.client_id == client_id, Client.is_active == True).first()
            if not client:
                raise HTTPException(status_code=401, detail="Invalid or inactive client")
            return client
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Fallback to old x-client-id/x-license-key auth
    if not x_client_id or not x_license_key:
        raise HTTPException(status_code=401, detail="Missing credentials")

    client = db.query(Client).filter(
        Client.client_id == x_client_id,
        Client.license_key == x_license_key,
        Client.is_active == True
    ).first()
    if not client:
        raise HTTPException(status_code=401, detail="Invalid or inactive client credentials")
    return client


def verify_admin_auth(
    request: Request,
    x_client_id: Optional[str] = Header(None, convert_underscores=False),
    x_license_key: Optional[str] = Header(None, convert_underscores=False),
    db: Session = Depends(get_db)
):
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            client_id = payload.get("sub")
            role = payload.get("role")
            if not client_id or role != "admin":
                raise HTTPException(status_code=403, detail="Admin role required")
            client = db.query(Client).filter(Client.client_id == client_id, Client.is_active == True).first()
            if not client or client.client_id != "admin":
                raise HTTPException(status_code=403, detail="Admin not found or inactive")
            return client
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Fallback to header-based admin auth
    if not x_client_id or not x_license_key:
        raise HTTPException(status_code=401, detail="Missing credentials")

    client = db.query(Client).filter(
        Client.client_id == x_client_id,
        Client.license_key == x_license_key,
        Client.is_active == True
    ).first()
    if not client or client.client_id != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")
    return client


def get_current_client_data(
    request: Request,
    x_client_id: Optional[str] = Header(None, convert_underscores=False),
    x_license_key: Optional[str] = Header(None, convert_underscores=False),
    db: Session = Depends(get_db)
):
    # First, try Bearer token auth
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            client_id = payload.get("sub")
            role = payload.get("role")
            if not client_id or not role:
                raise HTTPException(status_code=401, detail="Invalid token")

            client = db.query(Client).filter(Client.client_id == client_id, Client.is_active == True).first()
            if not client:
                raise HTTPException(status_code=401, detail="Invalid or inactive client")

            return {
                "client_id": client.client_id,
                "is_admin": client.client_id == "admin"
            }

        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Fallback to x-client-id and x-license-key
    if not x_client_id or not x_license_key:
        raise HTTPException(status_code=401, detail="Missing credentials")

    client = db.query(Client).filter(
        Client.client_id == x_client_id,
        Client.license_key == x_license_key,
        Client.is_active == True
    ).first()
    if not client:
        raise HTTPException(status_code=401, detail="Invalid or inactive client")

    return {
        "client_id": client.client_id,
        "is_admin": client.client_id == "admin"
    }