from typing import List, Dict
from fastapi import HTTPException, status
from sqlalchemy import select, update, func, distinct, delete, literal, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from logging_manager import logger
from db_conn import DB_connection
from users.user_models import User, ParkingLocation, ParkingSpot, UserRole, UserRoleMapping, Booking, CancelledBooking
from admin.admin_models import Car
from admin.admin_schemes import ParkingLocationSchema, ParkingSpotSchema, AdminUserSchema, UpdatePriceSchema, BookingSchema
from users.db_manager import pwd_context, SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from datetime import datetime, timezone
import jwt
from jwt.exceptions import InvalidTokenError

class AdminRepository:
    def __init__(self, user_db_connection: DB_connection, pay_db_connection: DB_connection):
        self.user_db_connection = user_db_connection

    async def get_current_admin(self, token: str) -> AdminUserSchema:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            email: str = payload.get("sub")
            if email is None:
                raise HTTPException(status_code=401, detail="Недействительный токен")
            user, role_name = await self.get_user_by_email(email)
            if role_name != "Admin":
                raise HTTPException(status_code=403, detail="Недостаточно прав")
            return AdminUserSchema(
                UserID=user.UserID,
                Username=user.Username,
                Email=user.Email,
                RoleName=role_name,
                Status=user.Status
            )
        except InvalidTokenError:
            raise HTTPException(status_code=401, detail="Недействительный токен")

    async def get_user_by_email(self, email: str):
        async for session in self.user_db_connection.get_session():
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
                return None, None
            return row

    async def get_all_users(self) -> List[AdminUserSchema]:
        async for session in self.user_db_connection.get_session():
            try:
                query = (
                    select(User, UserRole.RoleName)
                    .join(UserRoleMapping, User.UserID == UserRoleMapping.UserID)
                    .join(UserRole, UserRoleMapping.RoleID == UserRole.RoleID)
                )
                result = await session.execute(query)
                users = []
                for user, role_name in result.fetchall():
                    users.append(AdminUserSchema(
                        UserID=user.UserID,
                        Username=user.Username,
                        Email=user.Email,
                        RoleName=role_name,
                        Status=user.Status
                    ))
                logger.info(f"Получено {len(users)} пользователей")
                return users
            except SQLAlchemyError as e:
                logger.error(f"Ошибка при получении пользователей: {e}")
                raise HTTPException(status_code=500, detail="Ошибка при получении данных пользователей")

    async def get_parkings(self) -> List[ParkingLocationSchema]:
        async for session in self.user_db_connection.get_session():
            query = select(ParkingLocation)
            result = await session.execute(query)
            return [ParkingLocationSchema.from_orm(row) for row in result.scalars().all()]

    async def get_spots_by_parking(self, location_id: int) -> Dict:
        async for session in self.user_db_connection.get_session():
            try:
                floor_query = select(distinct(ParkingSpot.Floor)).where(ParkingSpot.LocationID == location_id)
                floor_result = await session.execute(floor_query)
                floors = [row[0] for row in floor_result.fetchall()]
                floors.sort(key=lambda x: (x is None, x))

                spots_query = select(ParkingSpot).where(ParkingSpot.LocationID == location_id)
                spots_result = await session.execute(spots_query)
                spots = [ParkingSpotSchema.from_orm(row) for row in spots_result.scalars().all()]

                logger.info(f"Получены данные для парковки {location_id}: {len(floors)} этажей, {len(spots)} мест")
                return {"floors": floors, "spots": spots}
            except SQLAlchemyError as e:
                logger.error(f"Ошибка при получении мест для парковки {location_id}: {e}")
                raise HTTPException(status_code=500, detail="Ошибка при получении данных")

    async def update_spot_status(self, spot_id: int, is_available: bool) -> None:
        async for session in self.user_db_connection.get_session():
            try:
                spot = await session.get(ParkingSpot, spot_id)
                if not spot:
                    raise HTTPException(status_code=404, detail="Место не найдено")

                if is_available:
                    subquery = (
                        select(
                            Booking.UserID,
                            func.max(Booking.Created).label("last_booking_time")
                        )
                        .where(Booking.SpotID == spot_id)
                        .group_by(Booking.UserID)
                        .subquery()
                    )

                    last_bookings_query = (
                        select(Booking)
                        .join(
                            subquery,
                            (Booking.UserID == subquery.c.UserID) & 
                            (Booking.Created == subquery.c.last_booking_time)
                        )
                        .where(Booking.SpotID == spot_id)
                    )

                    last_bookings_result = await session.execute(last_bookings_query)
                    last_bookings = last_bookings_result.scalars().all()

                    if last_bookings:
                        for booking in last_bookings:
                            await session.execute(
                                update(Car)
                                .where(Car.BookingID == booking.BookingID)
                                .values(BookingID=None)
                            )
                            logger.info(f"Обновлены записи Cars для BookingID={booking.BookingID}")

                            cancellation = CancelledBooking(
                                BookingID=booking.BookingID,
                                UserID=booking.UserID,
                                CancellationReason="Отменено администратором"
                            )
                            session.add(cancellation)
                            logger.info(f"Добавлена запись об отмене для BookingID={booking.BookingID}")

                        booking_ids = [b.BookingID for b in last_bookings]
                        await session.execute(
                            delete(Booking).where(Booking.BookingID.in_(booking_ids))
                        )
                        logger.info(f"Удалено {len(last_bookings)} последних бронирований для места {spot_id}")

                spot.IsAvailable = is_available
                await session.commit()
                logger.info(f"Статус места {spot_id} успешно обновлен на {is_available}")

            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f"Ошибка SQLAlchemy при обновлении места {spot_id}: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Ошибка базы данных: {str(e)}"
                )
            except Exception as e:
                await session.rollback()
                logger.error(f"Неожиданная ошибка при обновлении места {spot_id}: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Неожиданная ошибка: {str(e)}"
                )

    async def update_spot_price(self, spot_id: int, price: float) -> None:
        async for session in self.user_db_connection.get_session():
            try:
                if price < 0:
                    raise HTTPException(status_code=400, detail="Цена не может быть отрицательной")
                await session.execute(
                    update(ParkingSpot)
                    .where(ParkingSpot.SpotID == spot_id)
                    .values(Price=price)
                )
                await session.commit()
                logger.info(f"Цена места {spot_id} обновлена: Price={price}")
            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f"Ошибка при обновлении цены места: {e}")
                raise HTTPException(status_code=500, detail="Ошибка при обновлении цены места")

    async def get_user_bookings(self, user_id: int) -> List[BookingSchema]:
        try:
            async for user_session in self.user_db_connection.get_session():
                booking_query = (
                    select(
                        Booking.BookingID,
                        ParkingLocation.Address,
                        ParkingSpot.Floor,
                        Booking.StartTime,
                        Booking.EndTime
                    )
                    .join(ParkingSpot, Booking.SpotID == ParkingSpot.SpotID)
                    .join(ParkingLocation, ParkingSpot.LocationID == ParkingLocation.LocationID)
                    .where(Booking.UserID == user_id)
                )
                booking_result = await user_session.execute(booking_query)
                bookings_data = booking_result.fetchall()

                if not bookings_data:
                    logger.info(f"Нет бронирований для пользователя {user_id}")
                    return []

                booking_ids = [row.BookingID for row in bookings_data]

            async for user_session in self.user_db_connection.get_session():
                car_query = select(Car).where(Car.BookingID.in_(booking_ids))
                car_result = await user_session.execute(car_query)
                cars_list = car_result.scalars().all()
                cars_map = {car.BookingID: car for car in cars_list if car.BookingID is not None}

            bookings: List[BookingSchema] = []
            for row in bookings_data:
                car = cars_map.get(row.BookingID)
                bookings.append(
                    BookingSchema(
                        bookingId=row.BookingID,
                        address=row.Address,
                        floor=row.Floor,
                        startTime=row.StartTime,
                        endTime=row.EndTime,
                        carBrand=car.CarBrand if car else None,
                        carNumber=car.CarNumber if car else None
                    )
                )

            logger.info(f"Получено {len(bookings)} бронирований для пользователя {user_id}")
            return bookings

        except SQLAlchemyError as e:
            logger.error(f"Ошибка при получении бронирований пользователя {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Ошибка при получении данных бронирований")

    async def update_user_status(self, user_id: int, status: str) -> None:
        async for session in self.user_db_connection.get_session():
            try:
                await session.execute(
                    update(User)
                    .where(User.UserID == user_id)
                    .values(Status=status)
                )
                await session.commit()
                logger.info(f"Статус пользователя {user_id} обновлен на {status}")
            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f"Ошибка при обновлении статуса пользователя {user_id}: {e}")
                raise HTTPException(status_code=500, detail="Ошибка при обновлении статуса пользователя")

    async def get_parkings_analytics(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        async for session in self.user_db_connection.get_session():
            try:
                if start_date > end_date:
                    raise HTTPException(status_code=400, detail="Дата начала не может быть позже даты окончания")
                query = (
                    select(
                        ParkingLocation.Address,
                        func.count(Booking.BookingID).label("booking_count")
                    )
                    .join(ParkingSpot, ParkingLocation.LocationID == ParkingSpot.LocationID)
                    .join(Booking, ParkingSpot.SpotID == Booking.SpotID)
                    .where(Booking.StartTime >= start_date)
                    .where(Booking.StartTime <= end_date)
                    .group_by(ParkingLocation.Address)
                    .order_by(func.count(Booking.BookingID).desc())
                )
                result = await session.execute(query)
                analytics = [
                    {"address": row.Address, "booking_count": row.booking_count}
                    for row in result.fetchall()
                ]
                logger.info(f"Аналитика парковок за период {start_date} - {end_date}: {len(analytics)} записей")
                return analytics
            except SQLAlchemyError as e:
                logger.error(f"Ошибка при получении аналитики парковок: {e}")
                raise HTTPException(status_code=500, detail="Ошибка при получении аналитики парковок")
            
    async def update_booking_times_format(self) -> None:
        async for session in self.user_db_connection.get_session():
            try:
                query = text("""
                    UPDATE Bookings
                    SET StartTime = StartTime + :seconds,
                        EndTime = EndTime + :seconds
                    WHERE LEN(StartTime) = 16 AND LEN(EndTime) = 16
                """)
                result = await session.execute(query, {"seconds": ":00"})
                await session.commit()
                logger.info(f"Обновлено {result.rowcount} записей в Bookings с добавлением секунд")
            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f"Ошибка при обновлении формата времени в Bookings: {e}")
                raise HTTPException(status_code=500, detail="Ошибка при обновлении формата времени")

    async def get_spots_analytics(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        async for session in self.user_db_connection.get_session():
            try:
                if start_date > end_date:
                    raise HTTPException(status_code=400, detail="Дата начала не может быть позже даты окончания")
                
                await self.update_booking_times_format()

                query = text("""
                    SELECT TOP 5 
                        ps.SpotID, 
                        ps.SpotNumber, 
                        pl.Address, 
                        ps.Floor, 
                        AVG(CAST(DATEDIFF(second, b.StartTime, b.EndTime) AS FLOAT) / 3600.0) AS avg_hours
                    FROM ParkingSpots ps
                    JOIN Bookings b ON ps.SpotID = b.SpotID
                    JOIN ParkingLocations pl ON ps.LocationID = pl.LocationID
                    WHERE b.StartTime >= :start_date
                      AND b.StartTime <= :end_date
                      AND b.StartTime IS NOT NULL
                      AND b.EndTime IS NOT NULL
                    GROUP BY ps.SpotID, ps.SpotNumber, pl.Address, ps.Floor
                    ORDER BY AVG(CAST(DATEDIFF(second, b.StartTime, b.EndTime) AS FLOAT) / 3600.0) DESC
                """)
                result = await session.execute(query, {"start_date": start_date, "end_date": end_date})
                analytics = [
                    {
                        "spot_id": row.SpotID,
                        "spot_number": row.SpotNumber,
                        "address": row.Address,
                        "floor": row.Floor,
                        "avg_hours": float(row.avg_hours) if row.avg_hours else 0.0
                    }
                    for row in result.fetchall()
                ]
                logger.info(f"Аналитика мест за период {start_date} - {end_date}: {len(analytics)} записей")
                return analytics
            except SQLAlchemyError as e:
                logger.error(f"Ошибка при получении аналитики мест: {e}")
                raise HTTPException(status_code=500, detail="Ошибка при получении аналитики мест")

    async def get_revenue_analytics(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        async for user_session in self.user_db_connection.get_session():
            try:
                if start_date > end_date:
                    raise HTTPException(status_code=400, detail="Дата начала не может быть позже даты окончания")
                
                await self.update_booking_times_format()
                
                query = text("""
                    SELECT 
                        pl.Address, 
                        CAST(b.StartTime AS DATE) AS date, 
                        SUM(CAST(DATEDIFF(second, b.StartTime, b.EndTime) AS FLOAT) / 3600.0 * ps.Price) AS revenue
                    FROM Bookings b
                    JOIN ParkingSpots ps ON b.SpotID = ps.SpotID
                    JOIN ParkingLocations pl ON ps.LocationID = pl.LocationID
                    WHERE b.StartTime >= :start_date
                      AND b.StartTime <= :end_date
                      AND b.StartTime IS NOT NULL
                      AND b.EndTime IS NOT NULL
                    GROUP BY pl.Address, CAST(b.StartTime AS DATE)
                    ORDER BY CAST(b.StartTime AS DATE)
                """)
                result = await user_session.execute(query, {"start_date": start_date, "end_date": end_date})
                analytics = [
                    {
                        "address": row.Address,
                        "date": row.date.strftime('%Y-%m-%d'),
                        "revenue": float(row.revenue) if row.revenue else 0.0
                    }
                    for row in result.fetchall()
                ]
                logger.info(f"Аналитика доходов за период {start_date} - {end_date}: {len(analytics)} записей")
                return analytics
            except SQLAlchemyError as e:
                logger.error(f"Ошибка при получении аналитики доходов: {e}")
                raise HTTPException(status_code=500, detail="Ошибка при получении аналитики доходов")