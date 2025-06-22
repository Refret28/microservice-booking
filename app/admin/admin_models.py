from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Numeric, Boolean, ForeignKey
from sqlalchemy.sql import func
from users.user_models import Base, User, ParkingLocation, ParkingSpot, UserRole, UserRoleMapping, Booking, ParkingLocation, ParkingSpot
from users.user_models import Car