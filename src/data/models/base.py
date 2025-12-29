from typing import List
from typing import Optional
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
import uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs
from datetime import datetime

class Base(AsyncAttrs, DeclarativeBase):
    pass