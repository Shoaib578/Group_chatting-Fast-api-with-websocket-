from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .database import Base

class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String)
    email = Column(String, unique=True)
    online = Column(Boolean,default=False)
    password_hash = Column(String)

    # Establish one-to-many relationship with Message model
    messages = relationship("Message", back_populates="sender")
