from typing import List
from typing import Optional
from sqlalchemy import ForeignKey 
from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

