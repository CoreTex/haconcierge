from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Owner(Base):
    __tablename__ = "owners"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(30), unique=True, nullable=False)
    aliases = Column(JSON, default=list)  # ["Mama", "Anna", "Mutter von Max"]
    notify_on_task = Column(Boolean, default=True)
    notify_on_appointment = Column(Boolean, default=True)
    notify_on_keyword = Column(Boolean, default=True)
    o365_email = Column(String(200), nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    keywords = relationship("Keyword", back_populates="owner", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="owner")
    appointments = relationship("Appointment", back_populates="owner")


class Keyword(Base):
    __tablename__ = "keywords"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("owners.id"), nullable=False)
    word = Column(String(100), nullable=False)
    case_sensitive = Column(Boolean, default=False)
    active = Column(Boolean, default=True)

    owner = relationship("Owner", back_populates="keywords")


class WhatsAppGroup(Base):
    __tablename__ = "whatsapp_groups"

    id = Column(Integer, primary_key=True, index=True)
    jid = Column(String(100), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    monitored = Column(Boolean, default=True)
    participant_count = Column(Integer, default=0)
    last_seen = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    wa_message_id = Column(String(100), unique=True, nullable=False)
    chat_jid = Column(String(100), nullable=False)
    sender_jid = Column(String(100), nullable=False)
    sender_name = Column(String(200), nullable=True)
    content = Column(Text, nullable=False)
    is_group = Column(Boolean, default=False)
    timestamp = Column(DateTime, nullable=False)
    processed = Column(Boolean, default=False)
    ai_result = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    tasks = relationship("Task", back_populates="source_message")
    appointments = relationship("Appointment", back_populates="source_message")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("owners.id"), nullable=True)
    source_message_id = Column(Integer, ForeignKey("messages.id"), nullable=True)
    due_date = Column(DateTime, nullable=True)
    status = Column(String(20), default="open")  # open, in_progress, done
    o365_task_id = Column(String(200), nullable=True)
    o365_plan_id = Column(String(200), nullable=True)
    ha_event_fired = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("Owner", back_populates="tasks")
    source_message = relationship("Message", back_populates="tasks")


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("owners.id"), nullable=True)
    source_message_id = Column(Integer, ForeignKey("messages.id"), nullable=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    location = Column(String(500), nullable=True)
    status = Column(String(20), default="confirmed")
    o365_event_id = Column(String(200), nullable=True)
    ha_event_fired = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("Owner", back_populates="appointments")
    source_message = relationship("Message", back_populates="appointments")


class KeywordHit(Base):
    __tablename__ = "keyword_hits"

    id = Column(Integer, primary_key=True, index=True)
    keyword_id = Column(Integer, ForeignKey("keywords.id"), nullable=False)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False)
    matched_text = Column(String(500), nullable=False)
    ha_event_fired = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
