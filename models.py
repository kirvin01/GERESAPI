# models.py

from pydantic import BaseModel
from typing import Optional

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # segundos

class UserInDB(BaseModel):
    username: str
    hashed_password: str
    role: str = "user"
    disabled: bool = False