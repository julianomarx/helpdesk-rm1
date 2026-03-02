from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session

from schemas import CategoryCreate, CategoryUpdate

from models import User as UserModel, Category as CategoryModel, Team as TeamModel


def create_category_service(
    category: CategoryCreate,
    db: Session
):
    
    team = db.query(TeamModel).filter(TeamModel.id == category.team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    category_name_already_registered = db.query(CategoryModel).filter(CategoryModel.name == category.name).first()
    
    if category_name_already_registered:
        raise HTTPException(status_code=400, detail="There is already a category registered with this name")

    new_category = CategoryModel(
        name=category.name,
        team_id=category.team_id
    )
    
    db.add(new_category)
    db.commit()
    
    db.refresh(new_category)
    
    return new_category

def delete_category_service(
    category_id: int,
    db: Session
):
    
    category = db.query(CategoryModel).filter(CategoryModel.id == category_id).first()
    
    if not category:
        raise HTTPException(status_code=404, detail="Category doesn't exist")
    
    db.delete(category)
    
    db.commit()
    
def update_category_service(
    category_id: int,
    category_update: CategoryUpdate,
    current_user: UserModel,
    db: Session
):
    
    category = db.query(CategoryModel).filter(CategoryModel.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")


    update_data = category_update.model_dump(exclude_unset=True)
    
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
    
