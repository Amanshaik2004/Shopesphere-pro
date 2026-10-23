from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel

class QuestionCreate(BaseModel):
    product_id: int
    question_text: str

class AnswerCreate(BaseModel):
    answer_text: str

class AnswerOut(BaseModel):
    id: int
    question_id: int
    user_id: int
    answer_text: str
    is_official: bool
    created_at: datetime

    class Config:
        from_attributes = True

class QuestionOut(BaseModel):
    id: int
    product_id: int
    user_id: int
    question_text: str
    is_approved: bool
    answers: List[AnswerOut] = []
    created_at: datetime

    class Config:
        from_attributes = True
