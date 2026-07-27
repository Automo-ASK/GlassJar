from pydantic import BaseModel, Field


class AskIn(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class AskOut(BaseModel):
    answer: str
