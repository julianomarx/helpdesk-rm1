from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from auth_utils import get_current_user

from models import Category as CategoryModel, Team as TeamModel
from schemas import CategoryCreate, CategoryUpdate, Category, CategoryWithSubcategories

router = APIRouter(
    prefix="/categories",
    tags=["categories"]
)


@router.post("/", response_model=Category)
def create_category(
    category: CategoryCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # valida team
    team = db.query(TeamModel).filter(TeamModel.id == category.team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    db_category = CategoryModel(
        name=category.name,
        team_id=category.team_id
    )

    db.add(db_category)
    db.commit()
    db.refresh(db_category)

    return db_category


@router.get("/", response_model=List[Category])
def list_categories(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    return db.query(CategoryModel).all()


@router.get("/{category_id}", response_model=CategoryWithSubcategories)
def get_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    category = db.query(CategoryModel).filter(CategoryModel.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.put("/{category_id}", response_model=Category)
def update_category(
    category_id: int,
    data: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    category = db.query(CategoryModel).filter(CategoryModel.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Atualiza somente campos enviados
    if data.name is not None:
        category.name = data.name
    if data.team_id is not None:
        # validar team novo
        team = db.query(TeamModel).filter(TeamModel.id == data.team_id).first()
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        category.team_id = data.team_id

    db.commit()
    db.refresh(category)

    return category


@router.delete("/{category_id}")
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    category = db.query(CategoryModel).filter(CategoryModel.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    db.delete(category)
    db.commit()

    return {"message": "Category deleted successfully"}
