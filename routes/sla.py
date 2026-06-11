from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from auth_utils import get_current_user
from models import User as UserModel, SLAPolicy as SLAPolicyModel, SubCategory as SubCategoryModel, RoleEnum
from schemas import SLAPolicyCreate, SLAPolicyUpdate, SLAPolicyOut

router = APIRouter(prefix="/sla-policies", tags=["sla"])


def _require_admin(current_user: UserModel) -> None:
    if current_user.role != RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Apenas administradores podem gerenciar políticas de SLA")


@router.get("", response_model=List[SLAPolicyOut])
def list_policies(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    return db.query(SLAPolicyModel).order_by(SLAPolicyModel.first_response_hours).all()


@router.post("", response_model=SLAPolicyOut, status_code=201)
def create_policy(
    payload: SLAPolicyCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    _require_admin(current_user)

    if db.query(SLAPolicyModel).filter(SLAPolicyModel.name == payload.name).first():
        raise HTTPException(status_code=400, detail="Já existe uma política com esse nome")

    policy = SLAPolicyModel(**payload.model_dump())
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


@router.put("/{policy_id}", response_model=SLAPolicyOut)
def update_policy(
    policy_id: int,
    payload: SLAPolicyUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    _require_admin(current_user)

    policy = db.query(SLAPolicyModel).filter(SLAPolicyModel.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Política não encontrada")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(policy, field, value)

    db.commit()
    db.refresh(policy)
    return policy


@router.delete("/{policy_id}", status_code=204)
def delete_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    _require_admin(current_user)

    policy = db.query(SLAPolicyModel).filter(SLAPolicyModel.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Política não encontrada")

    # Desvincula subcategorias antes de deletar
    db.query(SubCategoryModel).filter(SubCategoryModel.sla_policy_id == policy_id).update(
        {"sla_policy_id": None}
    )

    db.delete(policy)
    db.commit()


@router.put("/subcategories/{subcategory_id}/sla-policy", response_model=dict)
def assign_policy_to_subcategory(
    subcategory_id: int,
    policy_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """Associa (ou remove) uma política SLA de uma subcategoria."""
    _require_admin(current_user)

    subcategory = db.query(SubCategoryModel).filter(SubCategoryModel.id == subcategory_id).first()
    if not subcategory:
        raise HTTPException(status_code=404, detail="Subcategoria não encontrada")

    if policy_id is not None:
        policy = db.query(SLAPolicyModel).filter(SLAPolicyModel.id == policy_id).first()
        if not policy:
            raise HTTPException(status_code=404, detail="Política não encontrada")

    subcategory.sla_policy_id = policy_id
    db.commit()
    return {"subcategory_id": subcategory_id, "sla_policy_id": policy_id}
