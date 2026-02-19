from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from auth_utils import get_current_user, ensure_admin

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
    # valida team
    team = db.query(TeamModel).filter(TeamModel.id == category.team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    category_name_already_registered = db.query(CategoryModel).filter(CategoryModel.name == category.name).first()
    
    if category_name_already_registered:
        raise HTTPException(status_code=400, detail="There is already a category registered with this name")

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
    data: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(ensure_admin)
):
    
    category = db.query(CategoryModel).filter(CategoryModel.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")


    update_data = data.model_dump(exclude_unset=True)
    
    # valida team se estiver no payload
    if "team_id" in update_data:
        team = db.query(TeamModel).filter(TeamModel.id == update_data["team_id"]).first()
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        
    if "name" in update_data:
        
        category_name_already_registered = db.query(CategoryModel).filter(
            CategoryModel.name == update_data["name"],
            CategoryModel.id != category_id
        ).first()
    
        if category_name_already_registered:
            raise HTTPException(status_code=400, detail="There is already a category registered with this name")
        

    for category_attribute, updated_value in update_data.items():
        setattr(category, category_attribute, updated_value)


    db.commit()
    db.refresh(category)

    return category

@router.delete("/{category_id}")
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(ensure_admin)
):
   
    category = db.query(CategoryModel).filter(CategoryModel.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    db.delete(category)
    db.commit()

    return {"message": "Category deleted successfully"}
