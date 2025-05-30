from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.models import Client
from db.session import get_db
from api.schemas import ClientCreate, ClientOut, ClientUpdate, ClientUpdateSchema
from api.dependencies import verify_admin_auth, verify_client_auth

router = APIRouter(prefix="/clients", tags=["Clients"])

# Admin only: Create a new client
@router.post("/", response_model=ClientOut)
def create_client(
    client_data: ClientCreate,
    db: Session = Depends(get_db),
    admin=Depends(verify_admin_auth)
):
    """
    Create a new client with a unique `client_id`. Requires admin authentication.
    """
    existing_client_id = db.query(Client).filter_by(client_id=client_data.client_id).first()
    existing_email = db.query(Client).filter_by(email=client_data.email).first()
    if existing_client_id:
        raise HTTPException(status_code=400, detail="Client ID already exists")
    if existing_email:
        raise HTTPException(status_code=400, detail="Email ID already exists")

    try:
        client = Client(**client_data.dict())
        db.add(client)
        db.commit()
        db.refresh(client)
        return client
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create client: {str(e)}")

# Admin only: Get all clients
@router.get("/", response_model=list[ClientOut])
def get_all_clients(db: Session = Depends(get_db), admin=Depends(verify_admin_auth)):
    return db.query(Client).all()

# Client or Admin: Get a specific client
@router.get("/{client_id}", response_model=ClientOut)
def get_client(client_id: str, db: Session = Depends(get_db), current=Depends(verify_client_auth)):
    if current.client_id != client_id and current.client_id != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    client = db.query(Client).filter_by(client_id=client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.put("/me", response_model=ClientUpdateSchema)
def update_my_client_details(
    updates: ClientUpdateSchema,
    db: Session = Depends(get_db),
    client=Depends(verify_client_auth)
):
    db_client = db.query(Client).filter_by(client_id=client.client_id).first()
    if not db_client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Apply updates only for provided fields
    for field, value in updates.dict(exclude_unset=True).items():
        setattr(db_client, field, value)

    db.commit()
    db.refresh(db_client)
    return db_client
