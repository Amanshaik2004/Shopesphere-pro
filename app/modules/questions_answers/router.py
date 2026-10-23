from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.engagement import ProductQuestion, ProductAnswer
from app.models.catalog import Product
from app.models.users import User
from app.common.responses import ResponseSchema
from app.common.dependencies import get_current_active_user, require_roles
from app.common.enums import UserRole
from app.core.exceptions import NotFoundError
from app.modules.questions_answers.schemas import QuestionCreate, AnswerCreate, QuestionOut, AnswerOut

router = APIRouter(prefix="/qa", tags=["Module 39: Product Questions & Answers"])

@router.post("/questions", response_model=ResponseSchema[QuestionOut])
def ask_question(
    data: QuestionCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if not db.query(Product).filter(Product.id == data.product_id).first():
        raise NotFoundError("Product not found")

    q = ProductQuestion(
        product_id=data.product_id,
        user_id=current_user.id,
        question_text=data.question_text,
        is_approved=True
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    return ResponseSchema(message="Question submitted", data=QuestionOut.model_validate(q))

@router.post("/questions/{question_id}/answers", response_model=ResponseSchema[AnswerOut])
def answer_question(
    question_id: int,
    data: AnswerCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    q = db.query(ProductQuestion).filter(ProductQuestion.id == question_id).first()
    if not q:
        raise NotFoundError("Question not found")

    is_staff = current_user.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.SUPPORT_AGENT, UserRole.PRODUCT_MANAGER]

    ans = ProductAnswer(
        question_id=q.id,
        user_id=current_user.id,
        answer_text=data.answer_text,
        is_official=is_staff
    )
    db.add(ans)
    db.commit()
    db.refresh(ans)
    return ResponseSchema(message="Answer posted", data=AnswerOut.model_validate(ans))

@router.get("/product/{product_id}", response_model=ResponseSchema[List[QuestionOut]])
def get_questions_for_product(product_id: int, db: Session = Depends(get_db)):
    questions = db.query(ProductQuestion).filter(
        ProductQuestion.product_id == product_id,
        ProductQuestion.is_approved == True
    ).order_by(ProductQuestion.created_at.desc()).all()
    return ResponseSchema(data=[QuestionOut.model_validate(q) for q in questions])
