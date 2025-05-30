from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from api.dependencies import get_current_client_data
from db.session import get_db
from db.crud import get_dashboard_summary_data

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"]
)

@router.get("")
def get_dashboard_data(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_client_data),
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None
):
    return get_dashboard_summary_data(
        db=db,
        auth={"is_admin": current_user["is_admin"], "client_id": current_user["client_id"]},
        date_from=date_from,
        date_to=date_to
    )
