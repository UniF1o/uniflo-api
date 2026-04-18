from pydantic import BaseModel, ConfigDict

class UserResponse(BaseModel):
    id: str
    email: str
    role: str

    model_config = ConfigDict(from_attributes=True)