from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from auth_utils import get_current_user

from services.authorization import ensure_admin
from services.category_service import create_category_service, delete_category_service, update_category_service

from models import Category as CategoryModel, Team as TeamModel
from models import User as UserModel
from models import RoleEnum
from schemas import CategoryCreate, CategoryUpdate, Category, CategoryWithSubcategories

router = APIRouter(
    prefix="/categories",
    tags=["categories"]
)

@router.post("/", response_model=Category)
def create_category(
    category: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(ensure_admin)
):   
    new_category = create_category_service(category, db)

    return new_category

@router.get("/", response_model=List[Category])
def list_categories(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    return db.query(CategoryModel).all()

@router.get("/{category_id}", response_model=CategoryWithSubcategories)
def get_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    category = db.query(CategoryModel).filter(CategoryModel.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category

@router.put("/{category_id}", response_model=Category)
def update_category(
    category_id: int,
    category_update: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(ensure_admin)
):
    updated_category = update_category_service(category_id, category_update, db)

    return updated_category

@router.delete("/{category_id}")
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(ensure_admin)
):
   
    delete_category_service(category_id, db)

    return {"message": "Category deleted successfully"}
