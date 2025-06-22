from pydantic import BaseModel, ConfigDict
from typing import Optional

class ParkingLocationSchema(BaseModel):
    LocationID: int
    Address: str

    model_config = ConfigDict(from_attributes=True)

class ParkingSpotSchema(BaseModel):
    SpotID: int
    LocationID: int
    SpotNumber: str
    Floor: Optional[str]
    IsAvailable: bool
    Price: float

    model_config = ConfigDict(from_attributes=True)

class AdminUserSchema(BaseModel):
    UserID: int
    Username: str
    Email: str
    RoleName: str
    Status: str

    model_config = ConfigDict(from_attributes=True)

class UpdatePriceSchema(BaseModel):
    price: float

class BookingSchema(BaseModel):
    bookingId: int
    address: str
    floor: Optional[str]
    startTime: str
    endTime: str
    carBrand: Optional[str]
    carNumber: Optional[str]

    model_config = ConfigDict(from_attributes=True)