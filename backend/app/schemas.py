from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .models import TaskPriority, TaskStatus


class RegisterInput(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginInput(BaseModel):
    email: EmailStr
    password: str


class UserOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    email: EmailStr
    theme: str = "system"
    notifications_enabled: bool = True
    weekly_study_goal_minutes: int = 300


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    email: EmailStr | None = None
    theme: str | None = Field(default=None, pattern="^(light|dark|system)$")
    notifications_enabled: bool | None = None
    weekly_study_goal_minutes: int | None = Field(default=None, ge=30, le=4200)


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class TokenOutput(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOutput


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    description: str | None = Field(default=None, max_length=5000)
    status: TaskStatus = TaskStatus.pending
    priority: TaskPriority = TaskPriority.medium
    due_date: datetime | None = None
    subject_id: str | None = None
    goal_id: str | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=180)
    description: str | None = Field(default=None, max_length=5000)
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_date: datetime | None = None
    subject_id: str | None = None
    goal_id: str | None = None


class TaskOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    due_date: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    subject_id: str | None
    goal_id: str | None


class TaskPage(BaseModel):
    items: list[TaskOutput]
    page: int
    page_size: int
    total: int
    pages: int


class TaskStats(BaseModel):
    total: int
    pending: int
    in_progress: int
    completed: int
    overdue: int
    completion_rate: float


class SubjectInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    color: str = Field(default="#5267df", pattern=r"^#[0-9a-fA-F]{6}$")
    code: str | None = Field(default=None, max_length=30)
    period: str | None = Field(default=None, max_length=30)
    status: str = Field(default="PLANNED", pattern="^(PLANNED|IN_PROGRESS|COMPLETED|ARCHIVED)$")
    start_date: datetime | None = None
    target_date: datetime | None = None


class SubjectOutput(SubjectInput):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime
    updated_at: datetime


class SubjectStats(BaseModel):
    total_tasks: int
    completed_tasks: int
    total_sessions: int
    studied_minutes: int
    progress: int


class SubjectDetail(SubjectOutput):
    stats: SubjectStats
    related_tasks: list[TaskOutput]
    related_goals: list[dict]


class GoalInput(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    description: str | None = Field(default=None, max_length=3000)
    target: int = Field(default=100, ge=1, le=1000000)
    progress: int = Field(default=0, ge=0, le=1000000)
    priority: TaskPriority = TaskPriority.medium
    metric: str = Field(default="TASKS", pattern="^(TASKS|TIME)$")
    subject_id: str | None = None
    due_date: datetime | None = None


class GoalOutput(GoalInput):
    model_config = ConfigDict(from_attributes=True)
    id: str
    status: str
    completed_at: datetime | None
    created_at: datetime


class SessionStatus(str, Enum):
    running = "RUNNING"
    paused = "PAUSED"
    completed = "COMPLETED"
    cancelled = "CANCELLED"


class SessionInput(BaseModel):
    subject_id: str | None = None
    started_at: datetime
    ended_at: datetime | None = None
    duration_minutes: int = Field(default=25, ge=0, le=1440)
    duration_seconds: int = Field(default=0, ge=0)
    paused_duration_seconds: int = Field(default=0, ge=0)
    status: SessionStatus = SessionStatus.completed
    active_started_at: datetime | None = None
    paused_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=3000)


class SessionOutput(SessionInput):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime
    updated_at: datetime


class SessionStartInput(BaseModel):
    subject_id: str


class SessionStats(BaseModel):
    today_seconds: int
    week_seconds: int
    month_seconds: int
    total_seconds: int
    today_sessions: int
    week_sessions: int
    month_sessions: int
    total_sessions: int


class DashboardOutput(BaseModel):
    pending_tasks: int
    completed_tasks: int
    overdue_tasks: int
    active_goals: int
    completed_goals: int
    studied_minutes: int
    week_study_seconds: int
    weekly_study_goal_minutes: int
    current_streak: int
    recent_sessions: list[SessionOutput]


class NotificationOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    message: str
    kind: str
    read_at: datetime | None
    created_at: datetime


class CalendarEvent(BaseModel):
    id: str
    title: str
    event_type: str
    date: datetime
    status: str | None = None


class HistoryItem(BaseModel):
    id: str
    title: str
    event_type: str
    date: datetime
