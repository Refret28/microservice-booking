import uuid
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import select

from logging_manager import logger
from db_conn import DB_connection
from payments.pay_models import Payment


class PayRepository:
    def __init__(self, db_connection: DB_connection) -> None:
        self.db_connection = db_connection

    async def add_telegram_payment(self, booking_id: int, amount: float, telegram_transaction_id: str, user_id: int) -> str:
        async for session in self.db_connection.get_session():
            transaction_id = str(uuid.uuid4())
            payment = Payment(
                BookingID=booking_id,
                UserID=user_id,  
                TransactionID=telegram_transaction_id,
                PaymentStatus="Completed",
                Status="Completed",
                Amount=amount,                
            )
            session.add(payment)

            try:
                logger.info(f"Добавление Telegram-платежа: BookingID={booking_id}, UserID={user_id}, TransactionID={telegram_transaction_id}, Amount={amount}")
                await session.flush()
                await session.commit()
                logger.info(f"Telegram-платеж успешно сохранен: TransactionID={transaction_id}")
                return transaction_id
            except IntegrityError as e:
                await session.rollback()
                logger.error(f"IntegrityError при сохранении Telegram-платежа: {str(e)}")
                raise ValueError(f"Ошибка при сохранении данных об оплате: {str(e)}")
            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f"SQLAlchemyError при сохранении Telegram-платежа: {str(e)}")
                raise ValueError(f"Ошибка базы данных при сохранении платежа: {str(e)}")
            except Exception as e:
                await session.rollback()
                logger.error(f"Неизвестная ошибка при сохранении Telegram-платежа: {str(e)}")
                raise ValueError(f"Неизвестная ошибка при сохранении платежа: {str(e)}")

    async def get_booking_details(self, booking_id: str) -> dict:
        async for session in self.db_connection.get_session():
            query = select(
                Payment.UserID.label("user_id"),
                Payment.Amount.label("amount"),
                Payment.Status.label("payment_status"),
                Payment.TransactionID.label("transaction_id"),
            ).where(
                Payment.BookingID == booking_id
            )

            try:
                logger.info(f"Запрос данных для BookingID={booking_id}")
                result = await session.execute(query)
                details = result.mappings().first()
                logger.info(f"Результат запроса: {details}")

                if not details:
                    logger.warning(f"Данные для BookingID={booking_id} не найдены")
                    return {}

                return {
                    "user_id": details.get("user_id", None),
                    "amount": float(details.get("amount", 0)),
                    "payment_status": details.get("payment_status", "Не указано"),
                    "transaction_id": details.get("transaction_id", "Не указано")
                }
            except SQLAlchemyError as e:
                logger.error(f"Ошибка при запросе данных для BookingID={booking_id}: {str(e)}")
                raise

    async def cancel_booking(self, booking_id: int):
        async for session in self.db_connection.get_session():
            query = """
                UPDATE Payments
                SET PaymentStatus = 'Cancelled', Status = 'Cancelled'
                WHERE BookingID = %s
            """
            try:
                logger.info(f"Отмена бронирования: BookingID={booking_id}")
                await session.execute(query, (booking_id,))
                await session.commit()
                logger.info(f"Бронирование успешно отменено: BookingID={booking_id}")
            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f"Ошибка при отмене бронирования: {str(e)}")
                raise ValueError(f"Ошибка базы данных при отмене бронирования: {str(e)}")