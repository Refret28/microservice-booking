from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, Numeric, String, DateTime, func


class Model(DeclarativeBase):
    pass

class Payment(Model):
    __tablename__ = "Payments"
    PaymentID: Mapped[int] = mapped_column(Integer, primary_key=True)
    UserID: Mapped[int] = mapped_column(Integer, nullable=False)
    BookingID: Mapped[int] = mapped_column(Integer, nullable=False)
    TransactionID: Mapped[str] = mapped_column(String(100), nullable=False)
    PaymentStatus: Mapped[str] = mapped_column(String(50), default="Pending")
    Status: Mapped[str] = mapped_column(String(15), nullable=False)
    Amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    Created: Mapped[DateTime] = mapped_column(DateTime, default=func.now())