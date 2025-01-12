from pydantic import BaseModel, EmailStr
from typing import Optional
from typing_extensions import Literal
from bson import ObjectId

class UserRegistrationModel(BaseModel):
    username: str
    email: EmailStr
    password: str
    profilephoto: Optional[str] = None  
    gender: Literal['male', 'female', 'other']  
    age: int
    currentrole: Literal['student', 'employee', 'author', 'other']  

 

class BookReviewModel(BaseModel):
    bookname: str
    bookauthor: str
    bookphoto: Optional[str] = None  
    experience: str  
    readingstatus: Literal['start', 'continue', 'finished']  
    rating: float  
    buyplace: Literal['online', 'offline']  
    satisfied: bool  
    user_id: str  

    
