from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from .database import Base

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    description = Column(Text)
    venue = Column(String(150))
    date = Column(String(50), nullable=False)
    start_time = Column(String(20), nullable=False)
    end_time = Column(String(20), nullable=False)
    event_code = Column(String(20), unique=True, nullable=False, index=True)
    status = Column(String(30), default="UPCOMING")
    coordinator_token = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    participants = relationship("Participant", back_populates="event", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="event", cascade="all, delete-orphan")
    help_requests = relationship("HelpRequest", back_populates="event", cascade="all, delete-orphan")
    resource_requests = relationship("ResourceRequest", back_populates="event", cascade="all, delete-orphan")
    handoffs = relationship("Handoff", back_populates="event", cascade="all, delete-orphan")

class Participant(Base):
    __tablename__ = "participants"
    id = Column(Integer, primary_key=True, index=True)
    anonymous_id = Column(String(50), nullable=False)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    role = Column(String(30), default="VOLUNTEER")
    created_at = Column(DateTime, default=datetime.utcnow)

    event = relationship("Event", back_populates="participants")
    tasks = relationship("Task", back_populates="assigned_to")
    help_requests = relationship("HelpRequest", back_populates="created_by")
    help_assignments = relationship("HelpAssignment", back_populates="participant")
    handoffs_from = relationship("Handoff", foreign_keys="Handoff.from_participant_id", back_populates="from_participant")
    handoffs_to = relationship("Handoff", foreign_keys="Handoff.to_participant_id", back_populates="to_participant")

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    location = Column(String(150))
    priority = Column(String(30), default="NORMAL")
    status = Column(String(30), default="PENDING")
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    assigned_to_id = Column(Integer, ForeignKey("participants.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    event = relationship("Event", back_populates="tasks")
    assigned_to = relationship("Participant", back_populates="tasks")

class HelpRequest(Base):
    __tablename__ = "help_requests"
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    location = Column(String(150))
    priority = Column(String(30), default="NORMAL")
    required_people = Column(Integer, default=1)
    status = Column(String(30), default="OPEN")
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    created_by_id = Column(Integer, ForeignKey("participants.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    event = relationship("Event", back_populates="help_requests")
    created_by = relationship("Participant", back_populates="help_requests")
    assignments = relationship("HelpAssignment", back_populates="request", cascade="all, delete-orphan")

class HelpAssignment(Base):
    __tablename__ = "help_assignments"
    id = Column(Integer, primary_key=True)
    request_id = Column(Integer, ForeignKey("help_requests.id"), nullable=False)
    participant_id = Column(Integer, ForeignKey("participants.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    request = relationship("HelpRequest", back_populates="assignments")
    participant = relationship("Participant", back_populates="help_assignments")

class ResourceRequest(Base):
    __tablename__ = "resource_requests"
    id = Column(Integer, primary_key=True)
    item = Column(String(200), nullable=False)
    quantity = Column(Integer, default=1)
    location = Column(String(150))
    priority = Column(String(30), default="NORMAL")
    status = Column(String(30), default="REQUESTED")
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    event = relationship("Event", back_populates="resource_requests")

class Handoff(Base):
    __tablename__ = "handoffs"
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    from_participant_id = Column(Integer, ForeignKey("participants.id"), nullable=False)
    to_participant_id = Column(Integer, ForeignKey("participants.id"), nullable=True)
    what_happened = Column(Text)
    remaining = Column(Text)
    issues = Column(Text)
    next_action = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    event = relationship("Event", back_populates="handoffs")
    from_participant = relationship("Participant", foreign_keys=[from_participant_id], back_populates="handoffs_from")
    to_participant = relationship("Participant", foreign_keys=[to_participant_id], back_populates="handoffs_to")
