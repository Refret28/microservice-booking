from datetime import datetime, timedelta, timezone
import logging
import configparser

from typing import Annotated
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext
from sqlalchemy import case, delete, func, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from db_conn import DB_connection
from users.user_models import User, ParkingLocation, ParkingSpot, Booking, UserRole, UserRoleMapping, CancelledBooking, Car
from users.user_schemes import SCarInfoForm, SRegisterForm, SLoginForm, SBookingData, Token, TokenData
from logging_manager import logger

logging.basicConfig()
logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
logging.getLogger("sqlalchemy.dialects").setLevel(logging.DEBUG)

config = configparser.ConfigParser()
config.read('config.ini')
SECRET_KEY = config['SECRET KEY']['SECRET_KEY']
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class UserRepository:
    def __init__(self, db_connection: DB_connection):
        self.db_connection = db_connection

    async def cancel_booking(self, booking_id: int):
        async for session in self.db_connection.get_session():
            async with session.begin():
                booking = await session.get(Booking, booking_id)
                if not booking:
                    logger.error(f"Booking with ID {booking_id} not found.")
                    raise HTTPException(status_code=404)

                start_time = datetime.strptime(booking.StartTime.replace("T", " "), "%Y-%m-%d %H:%M")
                if datetime.now() > start_time - timedelta(days=1):
                    raise HTTPException(status_code=400, detail="Бронирование можно отменить только за сутки до начала")

                await session.execute(
                    delete(Car).where(Car.BookingID == booking_id)
                )

                await session.execute(
                    update(ParkingSpot)
                    .where(ParkingSpot.SpotID == booking.SpotID)
                    .values(IsAvailable=True)
                )

                await session.delete(booking)

                await session.commit()

    def verify_password(self, plain_password, hashed_password):
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception as e:
            logger.error(f"Ошибка верификации пароля: {e}")
            return False

    def get_password_hash(self, password):
        try:
            return pwd_context.hash(password)
        except Exception as e:
            logger.error(f"Ошибка хеширования пароля: {e}")
            raise HTTPException(status_code=500, detail="Ошибка хеширования пароля")

    async def get_user(self, email: str):
        async for session in self.db_connection.get_session():
            query = (
                select(User, UserRole.RoleName)
                .join(UserRoleMapping, User.UserID == UserRoleMapping.UserID)
                .join(UserRole, UserRoleMapping.RoleID == UserRole.RoleID)
                .where(User.Email == email)
            )
            result = await session.execute(query)
            row = result.first()
            if not row:
                logger.error(f"Пользователь с email {email} не найден")
                return None
            user, role_name = row
            user.RoleName = role_name  
            return user

    async def authenticate_user(self, email: str, password: str):
        user = await self.get_user(email)
        
        if not user:
            logger.error("Пользователь не найден")
            raise HTTPException(status_code=401, detail="Неверный email или пароль") 
        
        logger.info(f"Stored hashed password: {user.Password}")
        logger.info(f"Entered password: {password}")

        if not self.verify_password(password, user.Password):
            logger.error("Ошибка верификации пароля")
            raise HTTPException(status_code=401, detail="Неверный email или пароль")
        
        if user.Status == "Black":
            logger.error(f"Пользователь {email} в черном списке")
            raise HTTPException(status_code=403, detail="Вас добавили в черный список")
        
        logger.info("Пароль успешно верифицирован")
        return user

    async def create_access_token(self, data: dict, expires_delta: timedelta | None = None):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    async def get_current_user(self, token: str = Depends(oauth2_scheme)):
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            email: str = payload.get("sub")
            if email is None:
                raise credentials_exception
            token_data = TokenData(email=email)
        except InvalidTokenError:
            raise credentials_exception

        user = await self.get_user(token_data.email)
        if user is None:
            raise credentials_exception
        return user

    async def get_current_active_user(self, current_user: Annotated[User, Depends(get_current_user)]):
        if current_user.disabled:
            raise HTTPException(status_code=400, detail="Inactive user")
        return current_user
    
    async def register_user(self, data: SRegisterForm) -> int:
        async for session in self.db_connection.get_session():
            try:
                logger.info(f"Начало регистрации пользователя: {data.username}, {data.email}, {data.phone}")

                username_query = select(User.UserID).where(User.Username == data.username)
                username_result = await session.execute(username_query)
                if username_result.scalar_one_or_none():
                    logger.error(f"Имя пользователя {data.username} уже занято")
                    raise ValueError("Имя пользователя уже занято")

                email_query = select(User.UserID).where(User.Email == data.email)
                email_result = await session.execute(email_query)
                if email_result.scalar_one_or_none():
                    logger.error(f"Email {data.email} уже зарегистрирован")
                    raise ValueError("Email уже зарегистрирован")

                phone_query = select(User.UserID).where(User.PhoneNumber == data.phone)
                phone_result = await session.execute(phone_query)
                if phone_result.scalar_one_or_none():
                    logger.error(f"Номер телефона {data.phone} уже зарегистрирован")
                    raise ValueError("Номер телефона уже зарегистрирован")

                role_query = select(UserRole.RoleID).where(UserRole.RoleName == "User")
                role_result = await session.execute(role_query)
                role_id = role_result.scalar_one_or_none()
                
                if not role_id:
                    logger.error("Роль User не найдена в базе данных")
                    raise ValueError("Роль User не найдена")

                hashed_password = self.get_password_hash(data.password)
                user = User(
                    Username=data.username,
                    Email=data.email,
                    PhoneNumber=data.phone,
                    Password=hashed_password,
                    Status='White'
                )
                session.add(user)
                await session.flush()
                logger.info(f"Создан пользователь: {data.username}, UserID: {user.UserID}")

                user_role_mapping = UserRoleMapping(
                    UserID=user.UserID,
                    RoleID=role_id
                )
                session.add(user_role_mapping)
                logger.info(f"Добавлена роль User для UserID: {user.UserID}")

                await session.commit()
                logger.info(f"Пользователь {data.username} зарегистрирован с ID: {user.UserID} и ролью User")
                return user.UserID
            except IntegrityError:
                await session.rollback()
                logger.error(f"Ошибка IntegrityError при регистрации: возможное дублирование данных")
                raise ValueError("Ошибка при регистрации: данные уже существуют")
            except Exception as e:
                await session.rollback()
                logger.error(f"Неизвестная ошибка при регистрации: {str(e)}")
                raise ValueError(str(e))

    async def login_user(self, data: SLoginForm) -> Token:
        user = await self.authenticate_user(data.email, data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверные данные для входа.",
                headers={"X-Error-Email": "Invalid email or password."},
            )

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = await self.create_access_token(
            data={"sub": user.Email}, expires_delta=access_token_expires
        )
        return {"token": Token(access_token=access_token, token_type="bearer"), "user_id": user.UserID}

    async def get_username(self, user_id: int) -> str:
        async for session in self.db_connection.get_session():
            query_user = select(User.Username).where(User.UserID == user_id)
            result_user = await session.execute(query_user)
            username = result_user.scalar_one_or_none()
            if not username:
                raise ValueError("User not found")
            return username

    async def check_available_parking_spots(self) -> list[dict[str, str | int | list[int]]]:
        async for session in self.db_connection.get_session():
            try:
                query = (
                    select(ParkingLocation.Address, ParkingSpot.Floor)
                    .join(ParkingSpot, ParkingLocation.LocationID == ParkingSpot.LocationID, isouter=True)
                    .group_by(ParkingLocation.Address, ParkingSpot.Floor)
                    .having(
                        func.sum(
                            case(
                                (ParkingSpot.IsAvailable == 1, 1),
                                else_=0
                            )
                        ) == 0
                    )
                )
                logger.debug(f"Выполняется SQL-запрос: {str(query)}")
                result = await session.execute(query)
                occupied_data = result.fetchall()

                parking_dict = {}

                for row in occupied_data:
                    address = row.Address
                    floor = row.Floor

                    if address not in parking_dict:
                        parking_dict[address] = {
                            "address": address,
                            "floors": set() if floor is not None else None 
                        }

                    if floor is not None:
                        parking_dict[address]["floors"].add(floor)

                return list(parking_dict.values())
            except SQLAlchemyError as e:
                logger.error(f"Ошибка базы данных в check_available_parking_spots: {e}")
                raise HTTPException(status_code=500, detail=f"Ошибка базы данных: {str(e)}")

    async def get_parking_spots(self, location: str) -> list[dict]:
        coords, address = location.split("|")
        async for session in self.db_connection.get_session():
            query = (
                select(ParkingSpot.SpotNumber, ParkingSpot.Floor, ParkingSpot.IsAvailable, ParkingSpot.Price)
                .join(ParkingLocation, ParkingLocation.LocationID == ParkingSpot.LocationID)
                .where(ParkingLocation.Address == address)
            )
            logger.debug(f"Выполняется SQL-запрос: {str(query)}")
            result = await session.execute(query)
            spots = [
                {
                    "spot_number": row.SpotNumber,
                    "floor": row.Floor,
                    "is_available": row.IsAvailable,
                    "price": float(row.Price) if row.Price is not None else 0.0
                }
                for row in result.fetchall()
            ]
            logger.info(f"Найдены места для {address}: {spots}")
            return spots

    async def get_parking_prices(self) -> list[dict]:
        async for session in self.db_connection.get_session():
            query = (
                select(ParkingLocation.Address, func.avg(ParkingSpot.Price).label("avg_price"))
                .join(ParkingSpot, ParkingLocation.LocationID == ParkingSpot.LocationID)
                .group_by(ParkingLocation.Address)
            )
            logger.debug(f"Выполняется SQL-запрос: {str(query)}")
            result = await session.execute(query)
            prices = [
                {
                    "address": row.Address,
                    "price_per_hour": float(row.avg_price) if row.avg_price is not None else 0.0,
                    "price_per_minute": float(row.avg_price) / 60 if row.avg_price is not None else 0.0
                }
                for row in result.fetchall()
            ]
            return prices

    async def get_user_info(self, user_id: int) -> dict:
        async for session in self.db_connection.get_session():
            query_user = select(User).where(User.UserID == user_id)
            result_user = await session.execute(query_user)
            user = result_user.scalar_one_or_none()

            if not user:
                raise ValueError("User not found")

            query_bookings = (
                select(
                    Booking.BookingID,
                    ParkingLocation.Address,
                    ParkingSpot.SpotNumber,
                    ParkingSpot.Floor,
                    Booking.StartTime,
                    Booking.EndTime
                )
                .join(ParkingSpot, ParkingSpot.SpotID == Booking.SpotID)
                .join(ParkingLocation, ParkingLocation.LocationID == ParkingSpot.LocationID)
                .where(Booking.UserID == user_id)
            )
            logger.debug(f"Выполняется SQL-запрос: {str(query_bookings)}")
            result_bookings = await session.execute(query_bookings)
            bookings_raw = result_bookings.all()

            bookings = []
            for row in bookings_raw:
                cars_query = select(Car.CarNumber, Car.CarBrand).where(Car.BookingID == row.BookingID)
                result_cars = await session.execute(cars_query)
                cars_list = [{"car_number": c.CarNumber, "car_brand": c.CarBrand} for c in result_cars.fetchall()]

                bookings.append({
                    "booking_id": row.BookingID,
                    "address": row.Address,
                    "spot_number": row.SpotNumber,
                    "floor": row.Floor,
                    "start_time": row.StartTime.replace("T", " ") if row.StartTime else None,
                    "end_time": row.EndTime.replace("T", " ") if row.EndTime else None,
                    "cars": cars_list
                })

            return {
                "username": user.Username,
                "email": user.Email,
                "phone": user.PhoneNumber,
                "bookings": bookings
            }

    async def check_cancelled_bookings(self, user_id: int) -> dict:
        async for session in self.db_connection.get_session():
            try:
                query = select(CancelledBooking).where(CancelledBooking.UserID == user_id)
                result = await session.execute(query)
                cancellations = result.scalars().all()

                if not cancellations:
                    return {"show_cancellation_modal": False, "cancellation_message": ""}

                cancellation = cancellations[0]
                message = cancellation.CancellationReason

                await session.execute(
                    delete(CancelledBooking).where(CancelledBooking.UserID == user_id)
                )
                await session.commit()
                logger.info(f"Удалены записи CancelledBookings для UserID={user_id}")

                return {
                    "show_cancellation_modal": True,
                    "cancellation_message": message
                }
            except SQLAlchemyError as e:
                logger.error(f"Ошибка при проверке отмененных броней для UserID={user_id}: {e}")
                return {"show_cancellation_modal": False, "cancellation_message": ""}

    async def add_booking(self, data: SBookingData) -> tuple[int, int]:
        async for session in self.db_connection.get_session():
            try:
                location = await session.execute(
                    select(ParkingLocation.LocationID).where(ParkingLocation.Address == data.address)
                )
                location_id = location.scalar_one_or_none()
                if not location_id:
                    logger.error(f"Парковка не найдена для адреса: {data.address}.")
                    raise ValueError("Specified location not found.")

                spot_number = int(data.spot_number) if isinstance(data.spot_number, str) else data.spot_number

                query = select(ParkingSpot.SpotID, ParkingSpot.SpotNumber, ParkingSpot.Floor, ParkingSpot.IsAvailable).where(
                    ParkingSpot.LocationID == location_id,
                    ParkingSpot.SpotNumber == spot_number,
                    ParkingSpot.IsAvailable == 1
                )

                if data.floor is not None:
                    query = query.where(ParkingSpot.Floor == data.floor)
                else:
                    query = query.where(ParkingSpot.Floor.is_(None))

                logger.info(f"Запрос места: LocationID={location_id}, SpotNumber={spot_number}, Floor={data.floor}, IsAvailable=1")
                logger.debug(f"Выполняется SQL-запрос: {str(query)}")
                parking_spot = await session.execute(query)
                spot = parking_spot.fetchone()

                if not spot:
                    diag_query = select(ParkingSpot.SpotID, ParkingSpot.SpotNumber, ParkingSpot.Floor, ParkingSpot.IsAvailable).where(
                        ParkingSpot.LocationID == location_id,
                        ParkingSpot.SpotNumber == spot_number
                    )
                    if data.floor is not None:
                        diag_query = diag_query.where(ParkingSpot.Floor == data.floor)
                    else:
                        diag_query = diag_query.where(ParkingSpot.Floor.is_(None))
                    logger.debug(f"Выполняется диагностический SQL-запрос: {str(diag_query)}")
                    diag_result = await session.execute(diag_query)
                    diag_spot = diag_result.fetchone()
                    if diag_spot:
                        logger.error(f"Место найдено, но недоступно: SpotID={diag_spot.SpotID}, SpotNumber={diag_spot.SpotNumber}, Floor={diag_spot.Floor}, IsAvailable={diag_spot.IsAvailable}")
                    else:
                        logger.error(f"Место не существует: SpotNumber={spot_number}, Floor={data.floor}, LocationID={location_id}")
                    floor_str = f"на этаже {data.floor}" if data.floor else "без этажа"
                    raise ValueError(f"Место {spot_number} {floor_str} недоступно или не существует для адреса {data.address}")

                spot_id = spot.SpotID
                spot_number = spot.SpotNumber
                logger.info(f"Найдено место: SpotID={spot_id}, SpotNumber={spot_number}, Floor={spot.Floor}, IsAvailable={spot.IsAvailable}")

                booking = Booking(
                    UserID=data.user_id,
                    SpotID=spot_id,
                    StartTime=data.start_datetime,
                    EndTime=data.end_datetime,
                )
                session.add(booking)

                await session.execute(
                    update(ParkingSpot)
                    .where(ParkingSpot.SpotID == spot_id)
                    .values(IsAvailable=0)
                )

                await session.flush()
                booking_id = booking.BookingID

                await session.commit()
                logger.info(f"Бронирование успешно добавлено с ID: {booking_id} для пользователя {data.user_id}, место {spot_number}, этаж {data.floor}.")
                return booking_id, spot_number
            
            except IntegrityError as e:
                await session.rollback()
                logger.error(f"IntegrityError при добавлении бронирования: {e}")
                raise ValueError("Ошибка при добавлении бронирования: возможно, место уже занято.")
            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f"SQLAlchemyError при добавлении бронирования: {e}")
                raise ValueError("Неожиданная ошибка базы данных при добавлении бронирования.")
            except Exception as e:
                await session.rollback()
                logger.error(f"Неожиданная ошибка при добавлении бронирования: {e}")
                raise ValueError("Произошла непредвиденная ошибка.")
            
    async def add_car_info(self, car_info: SCarInfoForm) -> None:
        async for session in self.db_connection.get_session():
            result = await session.execute(select(User).where(User.UserID == car_info.user_id))
            user = result.scalar_one_or_none()
            if not user:
                raise HTTPException(status_code=404, detail="Пользователь не найден")

            try:
                car = Car(
                    UserID=car_info.user_id,
                    CarNumber=car_info.car_number,
                    CarBrand=car_info.car_brand,
                    BookingID=car_info.booking_id
                )
                session.add(car)
                await session.flush()
                await session.commit()
                logger.info(f"Добавлен автомобиль: UserID={car_info.user_id}, CarNumber={car_info.car_number}")
            except Exception as e:
                await session.rollback()
                logger.error(f"Ошибка при добавлении автомобиля: {e}")
                raise HTTPException(status_code=500, detail=f"Ошибка при сохранении автомобиля: {str(e)}")