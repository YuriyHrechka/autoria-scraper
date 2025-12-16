from datetime import datetime
from sqlalchemy import String, Integer, BigInteger, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from database.session import Base


class Car(Base):
    """Represents a car listing entity in the database.

    This model maps to the 'cars' table and stores detailed information
    about vehicles, likely scraped or collected from an external source.

    Attributes:
        id (int): Unique primary key identifier for the record.
        url (str): The unique URL of the source listing. Indexed for fast lookups.
        title (str): The title or name of the car advertisement.
        price_usd (int): The price of the car in US dollars.
        odometer (int): The distance the car has traveled (mileage).
        username (str): The name of the seller or user who posted the ad.
        phone_number (int): The contact phone number (stored as BigInteger).
        image_url (str): The URL to the main image of the car.
        images_count (int): The total number of images available in the listing.
        car_number (str): The license plate number of the car.
        car_vin (str): The Vehicle Identification Number (VIN).
        datetime_found (datetime): The timestamp when the record was created/found.
            Defaults to the current server time.
    """

    __tablename__ = "cars"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    url: Mapped[str] = mapped_column(String, unique=True, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    price_usd: Mapped[int] = mapped_column(Integer, nullable=True)
    odometer: Mapped[int] = mapped_column(Integer, nullable=True)
    username: Mapped[str] = mapped_column(String, nullable=True)
    phone_number: Mapped[int] = mapped_column(BigInteger, nullable=True)
    image_url: Mapped[str] = mapped_column(String, nullable=True)
    images_count: Mapped[int] = mapped_column(Integer, nullable=True)
    car_number: Mapped[str] = mapped_column(String, nullable=True)
    car_vin: Mapped[str] = mapped_column(String, nullable=True)
    datetime_found: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        """Returns a string representation of the Car instance.

        Returns:
            str: A formatted string containing the ID, title, and price.
        """
        return f"<Car(id={self.id}, title='{self.title}', price={self.price_usd}), odometer={self.odometer}>"
