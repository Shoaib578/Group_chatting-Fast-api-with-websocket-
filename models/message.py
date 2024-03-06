from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .database import Base

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey('user.id'))  # Foreign key constraint
    content = Column(String)

    # Establish relationship with User model
    sender = relationship("User", back_populates="messages")