from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from auth_utils import get_current_user

from models import SubCategory as SubCategoryModel, Category as CategoryModel
from schemas import SubCategoryCreate, SubCategoryUpdate, SubCategory

router = APIRouter(
    prefix="/subcategories",
    tags=["subcategories"]
)


@router.post("/", response_model=SubCategory)
def create_subcategory(
    sub: SubCategoryCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
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


@router.get("/", response_model=List[SubCategory])
def list_subcategories(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    return db.query(SubCategoryModel).all()


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


@router.put("/{subcategory_id}", response_model=SubCategory)
def update_subcategory(
    subcategory_id: int,
    data: SubCategoryUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
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

    db.commit()
    db.refresh(sub)

    return sub


@router.delete("/{subcategory_id}")
def delete_subcategory(
    subcategory_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    sub = db.query(SubCategoryModel).filter(SubCategoryModel.id == subcategory_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="SubCategory not found")

    db.delete(sub)
    db.commit()

    return {"message": "SubCategory deleted successfully"}
