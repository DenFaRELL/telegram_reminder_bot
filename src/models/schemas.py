from datetime import datetime, time
from typing import Optional
from pydantic import BaseModel, Field

class UserBase(BaseModel):
    telegram_id: int
    username: Optional[str] = None
    full_name: str

class UserCreate(UserBase):
    pass

class User(UserBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class ScheduleBase(BaseModel):
    day_of_week: int = Field(ge=0, le=6, description="0-понедельник, 6-воскресенье")
    start_time: str  # HH:MM
    end_time: str    # HH:MM
    subject_name: str
    subject_type: str = "lecture"
    room_number: Optional[str] = None

class ScheduleCreate(ScheduleBase):
    user_id: int

class Schedule(ScheduleBase):
    id: int
    user_id: int
    is_active: bool = True
    
    class Config:
        from_attributes = True

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    priority: str = "medium"

class TaskCreate(TaskBase):
    user_id: int

class Task(TaskBase):
    id: int
    user_id: int
    is_completed: bool = False
    created_at: datetime
    
    class Config:
        from_attributes = True

class EventBase(BaseModel):
    title: str
    description: Optional[str] = None
    event_date: datetime
    reminder_before: int = 24  # часы до события
    is_recurring: bool = False
    recurrence_pattern: Optional[str] = None  # daily/weekly/monthly

class EventCreate(EventBase):
    user_id: int

class Event(EventBase):
    id: int
    user_id: int
    next_reminder_time: Optional[datetime] = None
    
    class Config:
        from_attributes = True