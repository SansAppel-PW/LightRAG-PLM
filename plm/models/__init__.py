from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    ...

__all__=["document", "Base"]