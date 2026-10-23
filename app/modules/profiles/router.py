from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.users import User, UserProfile
from app.common.responses import ResponseSchema, MessageResponse
from app.common.dependencies import get_current_active_user
from app.modules.profiles.schemas import ProfileOut, ProfileUpdate

router = APIRouter(prefix="/profile", tags=["Module 04: Customer Profile Management"])

@router.get("", response_model=ResponseSchema[ProfileOut])
def get_my_profile(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)

    data = ProfileOut(
        id=profile.id,
        user_id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        phone_number=current_user.phone_number,
        bio=profile.bio,
        avatar_url=profile.avatar_url,
        date_of_birth=profile.date_of_birth,
        gender=profile.gender,
        preferences=profile.preferences,
        deactivation_requested=current_user.deactivation_requested
    )
    return ResponseSchema(data=data)

@router.put("", response_model=ResponseSchema[ProfileOut])
def update_my_profile(
    data_in: ProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)
        db.flush()

    if data_in.full_name is not None:
        current_user.full_name = data_in.full_name
    if data_in.phone_number is not None:
        current_user.phone_number = data_in.phone_number
    if data_in.bio is not None:
        profile.bio = data_in.bio
    if data_in.avatar_url is not None:
        profile.avatar_url = data_in.avatar_url
    if data_in.date_of_birth is not None:
        profile.date_of_birth = data_in.date_of_birth
    if data_in.gender is not None:
        profile.gender = data_in.gender
    if data_in.preferences is not None:
        profile.preferences = data_in.preferences

    db.commit()
    db.refresh(profile)
    db.refresh(current_user)

    data = ProfileOut(
        id=profile.id,
        user_id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        phone_number=current_user.phone_number,
        bio=profile.bio,
        avatar_url=profile.avatar_url,
        date_of_birth=profile.date_of_birth,
        gender=profile.gender,
        preferences=profile.preferences,
        deactivation_requested=current_user.deactivation_requested
    )
    return ResponseSchema(message="Profile updated successfully", data=data)

@router.post("/deactivate-request", response_model=ResponseSchema[MessageResponse])
def request_account_deactivation(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    current_user.deactivation_requested = True
    db.commit()
    return ResponseSchema(
        message="Account deactivation requested successfully",
        data=MessageResponse(message="Your request to deactivate account has been recorded and will be reviewed by administration.")
    )
