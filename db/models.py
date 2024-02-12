import uuid
from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    select,
)
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship

from db.main import Base


class BaseModel(Base):
    __abstract__ = True
    id = Column(String, primary_key=True)
    created_at = Column(DateTime, default=datetime.now)

    @classmethod
    async def create(
        cls, db: AsyncSession, identifier=None, created_at=None, **kwargs
    ):
        if not identifier:
            identifier = str(uuid4())
        if not created_at:
            created_at = datetime.now()

        transaction = cls(id=identifier, created_at=created_at, **kwargs)
        try:
            db.add(transaction)
            await db.commit()
            await db.refresh(transaction)
        except IntegrityError as e:
            await db.rollback()
            raise RuntimeError(e) from e

        return transaction

    @classmethod
    async def get(cls, db: AsyncSession, identifier: str):
        try:
            transaction = await db.get(cls, identifier)
        except NoResultFound:
            return None
        return transaction

    @classmethod
    async def get_all(
        cls, db: AsyncSession, skip: int = 0, limit: int = 100
    ):
        stmt = select(cls).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()


join_client_address = Table(
    "join_client_address",
    BaseModel.metadata,
    Column("client_id", String, ForeignKey("clients.id")),
    Column("address_id", String, ForeignKey("addresses.id")),
)


class Client(BaseModel):
    __tablename__ = "clients"
    name = Column(String, nullable=True, index=False, unique=False)
    phone = Column(BigInteger, nullable=True, index=True, unique=True)
    email = Column(String, nullable=True, index=True, unique=True)
    message = Column(String, nullable=True, index=False, unique=False)
    submission_amount = Column(
        Integer, nullable=False, index=False, unique=False
    )
    is_spam = Column(
        Boolean, nullable=False, index=False, unique=False, default=False
    )

    addresses = relationship(
        "Address", secondary=join_client_address, back_populates="clients"
    )

    @classmethod
    async def get_by_phone(cls, db: AsyncSession, phone: int):
        stmt = select(cls).filter(cls.phone == phone)
        result = await db.execute(stmt)
        return result.scalars().first()

    @classmethod
    async def get_by_email(cls, db: AsyncSession, email: str):
        stmt = select(cls).filter(cls.email == email)
        result = await db.execute(stmt)
        return result.scalars().first()

    @classmethod
    async def get_by_ip_address(cls, db: AsyncSession, ip_address: str):
        stmt = select(Address).filter_by(ip=ip_address)
        result = await db.execute(stmt)
        return result.scalars().first()

    async def increment_submission_amount(self, db: AsyncSession):
        self.submission_amount += 1

        if self.submission_amount > 5:
            self.is_spam = True

        db.add(self)
        try:
            await db.commit()  # Commit the transaction
            await db.refresh(self)  # Refresh the instance from the database
        except Exception as e:
            await db.rollback()  # Rollback in case of error
            raise RuntimeError(f"Failed to increment count: {e}") from e

    @classmethod
    async def get_submission_amount(
        cls, db: AsyncSession
    ):  # pylint: disable=W0613
        return cls.submission_amount

    async def set_spam(self, db: AsyncSession):
        self.is_spam = True
        db.add(self)
        try:
            await db.commit()  # Commit the transaction
            await db.refresh(self)  # Refresh the instance from the database
        except Exception as e:
            await db.rollback()  # Rollback in case of error
            raise RuntimeError(f"Failed to increment count: {e}") from e

    async def set_email(self, db: AsyncSession, email: str):
        self.email = email
        db.add(self)
        try:
            await db.commit()
            await db.refresh(self)
        except Exception as e:
            await db.rollback()
            raise RuntimeError(f"Failed to set email: {e}") from e

    async def set_phone(self, db: AsyncSession, phone: str):
        self.phone = phone
        db.add(self)
        try:
            await db.commit()
            await db.refresh(self)
        except Exception as e:
            await db.rollback()
            raise RuntimeError(f"Failed to set email: {e}") from e

    async def add_ip_address(self, db: AsyncSession, ip_address: str):
        # Check if the IP address already exists
        existing_address = await Client.get_by_ip_address(db, ip_address)
        address_newly_associated = False

        if existing_address:
            # Increment submission_amount if it already exists
            await existing_address.increment_submission_amount(db)
        else:
            # Create a new Address record if it does not exist
            existing_address = Address(
                ip=ip_address,
                submission_amount=1,
                is_spam=False,
                id=str(uuid.uuid4()),
            )
            db.add(existing_address)
            address_newly_associated = True

        try:
            await db.commit()
            await db.refresh(self)
            if existing_address:
                await db.refresh(existing_address)
        except Exception as e:
            await db.rollback()
            raise RuntimeError(f"Failed to add IP address: {e}") from e

        await db.flush()

        if (
            address_newly_associated
            or not (
                await db.execute(
                    select(join_client_address).filter_by(
                        client_id=self.id, address_id=existing_address.id
                    )
                )
            ).first()
        ):
            # Directly use the association table for linking
            await db.execute(
                join_client_address.insert().values(
                    client_id=self.id, address_id=existing_address.id
                )
            )

        try:
            await db.commit()
            await db.refresh(self)
            if existing_address:
                await db.refresh(existing_address)
        except Exception as e:
            await db.rollback()
            raise RuntimeError(f"Failed to add IP address: {e}") from e


class Address(BaseModel):
    __tablename__ = "addresses"
    ip = Column(String, nullable=False, index=True, unique=True)
    submission_amount = Column(
        Integer, nullable=False, index=False, unique=False
    )
    is_spam = Column(Boolean, nullable=False, index=False)

    clients = relationship(
        "Client", secondary=join_client_address, back_populates="addresses"
    )

    async def increment_submission_amount(self, db: AsyncSession):

        self.submission_amount += 1

        if self.submission_amount > 5:
            self.is_spam = True

        db.add(self)  # Mark the instance as modified
        try:
            await db.commit()  # Commit the transaction
            await db.refresh(self)  # Refresh the instance from the database
        except Exception as e:
            await db.rollback()  # Rollback in case of error
            raise RuntimeError(f"Failed to increment count: {e}") from e

    @classmethod
    async def get_submission_amount(
        cls, db: AsyncSession
    ):  # pylint: disable=W0613
        return cls.submission_amount

    async def set_spam(self, db: AsyncSession):
        self.is_spam = True
        db.add(self)
        try:
            await db.commit()  # Commit the transaction
            await db.refresh(self)  # Refresh the instance from the database
        except Exception as e:
            await db.rollback()  # Rollback in case of error
            raise RuntimeError(f"Failed to increment count: {e}") from e
