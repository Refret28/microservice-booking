import re

from pydantic import BaseModel, Field, constr, field_validator, ConfigDict
from typing import Optional


class Token(BaseModel):
    access_token: str
    token_type: str
    
class TokenData(BaseModel):
    email: str | None = None

class SLoginForm(BaseModel):
    email: str
    password: str = Field(...)

    @field_validator('password')
    def validate_password(cls, password):
        if not re.match(r'^[a-zA-Z0-9]+$', password):
            raise ValueError('Password must contain only letters and digits.')
        return password


class SRegisterForm(SLoginForm):
    username: str = Field(..., min_length=3, max_length=50)
    phone: str = Field(..., pattern=r"^\+?\d{10,15}$") 

    @field_validator("username")
    def validate_username(cls, value):
        if not value.isalnum():
            raise ValueError("Username must be alphanumeric")
        return value


class SUser(SRegisterForm):
    id: int  

    model_config = ConfigDict(from_attributes=True)

class UserInDB(SUser):
    hashed_password: str

class SBookingData(BaseModel):
    user_id: int
    address: str
    floor: Optional[str] = None
    spot_number: str
    start_datetime: str
    end_datetime: str

class SCarInfoForm(BaseModel):
    user_id: int
    car_number: str = Field(..., min_length=6, max_length=10, description="Номер автомобиля должен содержать от 6 до 10 символов.")
    car_brand: str = Field(..., description="Марка автомобиля")
    booking_id: Optional[int] = None

    @field_validator('car_number')
    def validate_car_number(cls, car_number):
        if not re.match(r'^[0-9а-яА-Я]{6,10}$', car_number):
            raise ValueError("Номер автомобиля должен состоять из 6-10 символов (буквы, цифры и кириллица).")
        return car_number

    @field_validator('car_brand')
    def validate_car_brand(cls, car_brand):
        popular_brands = [
            "Toyota", "BMW", "Audi", "Mercedes-Benz", "Volkswagen", "Honda", "Ford",
            "Nissan", "Hyundai", "Chevrolet", "Kia", "Mazda", "Renault", "Peugeot"
        ]
        if car_brand not in popular_brands:
            raise ValueError(f"Марка автомобиля должна быть одной из следующих: {', '.join(popular_brands)}.")
        return car_brand