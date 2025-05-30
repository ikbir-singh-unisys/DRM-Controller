from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.session import get_db
from db.models import Client
from schemas import ClientCreate, ClientUpdate
from api.dependencies import verify_admin_auth

router = APIRouter(prefix="/admin/clients", tags=["Admin Clients"])

@router.post("/", dependencies=[Depends(verify_admin_auth)])
def create_client(client_data: ClientCreate, db: Session = Depends(get_db)):
    if db.query(Client).filter(Client.client_id == client_data.client_id).first():
        raise HTTPException(status_code=400, detail="Client ID already exists")
    client = Client(**client_data.dict())
    db.add(client)
    db.commit()
    db.refresh(client)
    return {"message": "Client created", "client_id": client.client_id}

@router.get("/", dependencies=[Depends(verify_admin_auth)])
def get_clients(db: Session = Depends(get_db)):
    return db.query(Client).all()

@router.get("/{client_id}", dependencies=[Depends(verify_admin_auth)])
def get_client(client_id: str, db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.client_id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client

@router.put("/{client_id}", dependencies=[Depends(verify_admin_auth)])
def update_client(client_id: str, update_data: ClientUpdate, db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.client_id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    for key, value in update_data.dict(exclude_unset=True).items():
        setattr(client, key, value)
    db.commit()
    db.refresh(client)
    return {"message": "Client updated"}

@router.delete("/{client_id}", dependencies=[Depends(verify_admin_auth)])
def delete_client(client_id: str, db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.client_id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    db.delete(client)
    db.commit()
    return {"message": "Client deleted"}
