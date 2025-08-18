from typing import Optional

from starlette import status

from pydantic import BaseModel, Field


class RAGQARequest(BaseModel):
    question: str = Field(default=None, max_length=1000, title="question", description="user question")


class ApiResponse(BaseModel):
    code: int
    message: str
    data: Optional[dict] = None

class RAGQAResponse(BaseModel):
    code: int = status.HTTP_200_OK
    message: str = "SUCCESS"
    data: Optional[dict] = None


class UploadResponse(BaseModel):
    code: int = status.HTTP_200_OK
    message: str = "SUCCESS"
