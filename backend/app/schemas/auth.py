from typing import List, Optional
from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Alphanumeric username")
    email: str = Field(..., description="Valid email address")
    password: str = Field(..., min_length=6, description="Password with minimum 6 characters")
    full_name: Optional[str] = Field(None, description="User full display name")
    role: Optional[str] = Field("Site Reliability Engineer", description="User role in cluster")


class UserLogin(BaseModel):
    username_or_email: str = Field(..., description="Username or registered email")
    password: str = Field(..., description="Account password")


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    full_name: str
    role: str
    permissions: List[str]
    created_at: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse
