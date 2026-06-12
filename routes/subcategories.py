from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List

from database import get_db
from auth_utils import get_current_user

from services.authorization import ensure_admin

from models import SubCategory as SubCategoryModel, Category as CategoryModel, SLAPolicy as SLAPolicyModel, Ticket as TicketModel
from schemas import SubCategoryCreate, SubCategoryUpdate, SubCategory, SubCategoryWithSLA

router = APIRouter(
    prefix="/subcategories",
    tags=["subcategories"]
)


@router.post("/", response_model=SubCategory)
def create_subcategory(
    sub: SubCategoryCreate,
    db: Session = Depends(get_db),
    current_user = Depends(ensure_admin)
):
    category = db.query(CategoryModel).filter(CategoryModel.id == sub.category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    db_sub = SubCategoryModel(
        name=sub.name,
        category_id=sub.category_id
    )

    db.add(db_sub)
    db.commit()
    db.refresh(db_sub)

    return db_sub


@router.get("/", response_model=List[SubCategoryWithSLA])
def list_subcategories(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    category_id: int | None = None
):
    query = db.query(SubCategoryModel).options(joinedload(SubCategoryModel.sla_policy))

    if category_id:
        query = query.filter(SubCategoryModel.category_id == category_id)

    return query.all()


@router.get("/{subcategory_id}", response_model=SubCategory)
def get_subcategory(
    subcategory_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    sub = db.query(SubCategoryModel).filter(SubCategoryModel.id == subcategory_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="SubCategory not found")
    return sub


@router.put("/{subcategory_id}", response_model=SubCategoryWithSLA)
def update_subcategory(
    subcategory_id: int,
    data: SubCategoryUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(ensure_admin)
):
    sub = db.query(SubCategoryModel).filter(SubCategoryModel.id == subcategory_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="SubCategory not found")

    if data.name is not None:
        sub.name = data.name

    if data.category_id is not None:
        category = db.query(CategoryModel).filter(CategoryModel.id == data.category_id).first()
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        sub.category_id = data.category_id

    if "sla_policy_id" in data.model_fields_set:
        if data.sla_policy_id is not None:
            policy = db.query(SLAPolicyModel).filter(SLAPolicyModel.id == data.sla_policy_id).first()
            if not policy:
                raise HTTPException(status_code=404, detail="Política SLA não encontrada")
        sub.sla_policy_id = data.sla_policy_id

    db.commit()

    sub = (
        db.query(SubCategoryModel)
        .options(joinedload(SubCategoryModel.sla_policy))
        .filter(SubCategoryModel.id == subcategory_id)
        .first()
    )

    return sub


@router.delete("/{subcategory_id}")
def delete_subcategory(
    subcategory_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(ensure_admin)
):
    sub = db.query(SubCategoryModel).filter(SubCategoryModel.id == subcategory_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="SubCategory not found")

    db.query(TicketModel).filter(TicketModel.subcategory_id == subcategory_id).update(
        {"subcategory_id": None}, synchronize_session=False
    )

    db.delete(sub)
    db.commit()

    return {"message": "SubCategory deleted successfully"}
