from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, DateTime, ForeignKey, Numeric, Boolean
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "Users"

    UserID: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    Username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    Password: Mapped[str] = mapped_column(String(255), nullable=False)
    Email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    PhoneNumber: Mapped[str] = mapped_column(String(20))
    Created: Mapped[DateTime] = mapped_column(DateTime, default=func.now())
    Status: Mapped[str] = mapped_column(String(10), nullable=False, default="White")

    bookings: Mapped[list["Booking"]] = relationship("Booking", back_populates="user")
    user_role_mappings: Mapped[list["UserRoleMapping"]] = relationship("UserRoleMapping", back_populates="user")
    cancelled_bookings: Mapped[list["CancelledBooking"]] = relationship("CancelledBooking", back_populates="user")
    cars: Mapped[list["Car"]] = relationship("Car", back_populates="user")  

class Car(Base):
    __tablename__ = "Cars"

    CarID: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    UserID: Mapped[int] = mapped_column(ForeignKey("Users.UserID"), nullable=False)
    CarNumber: Mapped[str] = mapped_column(String(50), nullable=False)
    CarBrand: Mapped[str] = mapped_column(String(100), nullable=False)
    Created: Mapped[DateTime] = mapped_column(DateTime, default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="cars")
    bookings: Mapped[list["Booking"]] = relationship("Booking", back_populates="car")

class ParkingLocation(Base):
    __tablename__ = "ParkingLocations"

    LocationID: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    Address: Mapped[str] = mapped_column(String(255), nullable=False)
    Created: Mapped[DateTime] = mapped_column(DateTime, default=func.now())

    parking_spots: Mapped[list["ParkingSpot"]] = relationship("ParkingSpot", back_populates="location")

class ParkingSpot(Base):
    __tablename__ = "ParkingSpots"

    SpotID: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    LocationID: Mapped[int] = mapped_column(ForeignKey("ParkingLocations.LocationID"), nullable=False)
    SpotNumber: Mapped[str] = mapped_column(String(50), nullable=False)
    Floor: Mapped[str] = mapped_column(String(1), nullable=True)
    IsAvailable: Mapped[bool] = mapped_column(Boolean, default=True)
    Price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    Created: Mapped[DateTime] = mapped_column(DateTime, default=func.now())

    location: Mapped["ParkingLocation"] = relationship("ParkingLocation", back_populates="parking_spots")
    bookings: Mapped[list["Booking"]] = relationship("Booking", back_populates="parking_spot")

class Booking(Base):
    __tablename__ = "Bookings"

    BookingID: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    UserID: Mapped[int] = mapped_column(ForeignKey("Users.UserID"), nullable=False)
    CarID: Mapped[int] = mapped_column(ForeignKey("Cars.CarID"), nullable=False)
    SpotID: Mapped[int] = mapped_column(ForeignKey("ParkingSpots.SpotID"), nullable=True)
    StartTime: Mapped[str] = mapped_column(String(50), nullable=False)
    EndTime: Mapped[str] = mapped_column(String(50), nullable=False)
    Created: Mapped[DateTime] = mapped_column(DateTime, default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="bookings")
    parking_spot: Mapped["ParkingSpot"] = relationship("ParkingSpot", back_populates="bookings")
    car: Mapped["Car"] = relationship("Car", back_populates="bookings")

class UserRole(Base):
    __tablename__ = "UserRoles"

    RoleID: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    RoleName: Mapped[str] = mapped_column(String(50), nullable=False)

    user_role_mappings: Mapped[list["UserRoleMapping"]] = relationship("UserRoleMapping", back_populates="role")

class UserRoleMapping(Base):
    __tablename__ = "UserRoleMapping"

    UserRoleMappingID: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    UserID: Mapped[int] = mapped_column(ForeignKey("Users.UserID"), nullable=False)
    RoleID: Mapped[int] = mapped_column(ForeignKey("UserRoles.RoleID"), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="user_role_mappings")
    role: Mapped["UserRole"] = relationship("UserRole", back_populates="user_role_mappings")

class CancelledBooking(Base):
    __tablename__ = "CancelledBookings"

    CancellationID: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    BookingID: Mapped[int] = mapped_column(Integer, nullable=False)
    UserID: Mapped[int] = mapped_column(ForeignKey("Users.UserID"), nullable=False)
    CancellationReason: Mapped[str] = mapped_column(String(255), nullable=False)
    CancellationTime: Mapped[DateTime] = mapped_column(DateTime, default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="cancelled_bookings")