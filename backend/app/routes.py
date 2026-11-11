from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .database import get_db
from .dependencies import current_user
from .models import AuditLog, Goal, Notification, Subject, StudySession, Task, TaskPriority, TaskStatus, User
from .schemas import (DashboardOutput, GoalInput, GoalOutput, LoginInput, RegisterInput, SessionInput, SessionOutput,
                      SessionStartInput, SessionStats, SessionStatus,
                      SubjectInput, SubjectOutput, TaskCreate, TaskOutput, TaskUpdate, TokenOutput, UserOutput, UserUpdate, PasswordChange,
                      NotificationOutput, CalendarEvent, HistoryItem, TaskPage, TaskStats, SubjectStats, SubjectDetail)
from .security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/v1")
auth = APIRouter(prefix="/auth", tags=["auth"])
tasks = APIRouter(prefix="/tasks", tags=["tasks"])
subjects = APIRouter(prefix="/subjects", tags=["subjects"])
goals = APIRouter(prefix="/goals", tags=["goals"])
sessions = APIRouter(prefix="/study-sessions", tags=["study-sessions"])
dashboard = APIRouter(prefix="/dashboard", tags=["dashboard"])
users = APIRouter(prefix="/users", tags=["users"])
calendar = APIRouter(prefix="/calendar", tags=["calendar"])
notifications = APIRouter(prefix="/notifications", tags=["notifications"])
history = APIRouter(prefix="/history", tags=["history"])


def audit(db: Session, event: str, user_id: str | None = None):
    db.add(AuditLog(event=event, user_id=user_id))


@auth.post("/register", response_model=TokenOutput, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterInput, db: Session = Depends(get_db)):
    email = payload.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="Não foi possível criar a conta com esses dados.")
    user = User(name=payload.name.strip(), email=email, password_hash=hash_password(payload.password))
    db.add(user)
    audit(db, "REGISTER", user.id)
    db.commit()
    db.refresh(user)
    return TokenOutput(access_token=create_access_token(user.id), user=user)


@auth.post("/login", response_model=TokenOutput)
def login(payload: LoginInput, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email ou senha inválidos.")
    audit(db, "LOGIN", user.id); db.commit()
    return TokenOutput(access_token=create_access_token(user.id), user=user)


@auth.get("/me", response_model=UserOutput)
def me(user: User = Depends(current_user)):
    return user


@users.patch("/me", response_model=UserOutput)
def update_me(payload: UserUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    data = payload.model_dump(exclude_unset=True)
    if "email" in data:
        data["email"] = data["email"].lower()
        existing = db.scalar(select(User).where(User.email == data["email"], User.id != user.id))
        if existing: raise HTTPException(409, "Não foi possível atualizar o perfil.")
    for key, value in data.items(): setattr(user, key, value)
    audit(db, "PROFILE_UPDATED", user.id); db.commit(); db.refresh(user)
    return user


@users.post("/me/password", status_code=204)
def change_password(payload: PasswordChange, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(400, "Senha atual inválida.")
    user.password_hash = hash_password(payload.new_password)
    audit(db, "PASSWORD_CHANGED", user.id); db.commit()


@users.delete("/me", status_code=204)
def delete_me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    audit(db, "ACCOUNT_DELETED", user.id)
    db.query(Notification).filter(Notification.user_id == user.id).delete(synchronize_session=False)
    db.query(StudySession).filter(StudySession.user_id == user.id).delete(synchronize_session=False)
    db.query(Task).filter(Task.user_id == user.id).delete(synchronize_session=False)
    db.query(Goal).filter(Goal.user_id == user.id).delete(synchronize_session=False)
    db.query(Subject).filter(Subject.user_id == user.id).delete(synchronize_session=False)
    db.query(AuditLog).filter(AuditLog.user_id == user.id).delete(synchronize_session=False)
    db.delete(user); db.commit()


def validate_task_links(payload, user: User, db: Session):
    if payload.subject_id and not db.scalar(select(Subject).where(Subject.id == payload.subject_id, Subject.user_id == user.id)):
        raise HTTPException(404, "Disciplina não encontrada.")
    if payload.goal_id and not db.scalar(select(Goal).where(Goal.id == payload.goal_id, Goal.user_id == user.id)):
        raise HTTPException(404, "Meta não encontrada.")


def recalculate_goal(goal_id: str | None, user_id: str, db: Session):
    if not goal_id:
        return
    goal = db.scalar(select(Goal).where(Goal.id == goal_id, Goal.user_id == user_id))
    if not goal:
        return
    if goal.metric == "TIME":
        if goal.subject_id:
            seconds = db.scalar(select(func.coalesce(func.sum(StudySession.duration_seconds), 0)).where(
                StudySession.subject_id == goal.subject_id,
                StudySession.user_id == user_id,
                StudySession.status == SessionStatus.completed.value,
            )) or 0
            goal.progress = int(seconds) // 60
        goal.status = "COMPLETED" if goal.progress >= goal.target else ("IN_PROGRESS" if goal.progress else "PLANNED")
        goal.completed_at = datetime.now(timezone.utc) if goal.status == "COMPLETED" else None
        return
    total = db.scalar(select(func.count(Task.id)).where(Task.goal_id == goal.id, Task.user_id == user_id)) or 0
    completed = db.scalar(select(func.count(Task.id)).where(Task.goal_id == goal.id, Task.user_id == user_id, Task.status == TaskStatus.completed)) or 0
    goal.progress = completed
    goal.status = "COMPLETED" if total and completed == total else ("IN_PROGRESS" if completed else ("OVERDUE" if goal.due_date and goal.due_date < datetime.now(timezone.utc) else "PLANNED"))
    goal.completed_at = datetime.now(timezone.utc) if goal.status == "COMPLETED" else None


@tasks.post("", response_model=TaskOutput, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    validate_task_links(payload, user, db)
    task = Task(**payload.model_dump(), user_id=user.id)
    if task.status == TaskStatus.completed:
        task.completed_at = datetime.now(timezone.utc)
    db.add(task)
    recalculate_goal(payload.goal_id, user.id, db)
    db.commit()
    db.refresh(task)
    return task


@tasks.get("", response_model=TaskPage)
def list_tasks(status_filter: TaskStatus | None = Query(default=None, alias="status"), priority: TaskPriority | None = None,
               subject_id: str | None = None, goal_id: str | None = None, search: str | None = Query(default=None, max_length=100),
               due: str | None = Query(default=None, pattern="^(today|week|upcoming|overdue)$"),
               sort: str = Query(default="smart", pattern="^(smart|created_at|updated_at|due_date|priority|status)$"),
               page: int = Query(default=1, ge=1), page_size: int = Query(default=10, ge=1, le=50),
               user: User = Depends(current_user), db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc); query = select(Task).where(Task.user_id == user.id)
    if status_filter:
        query = query.where(Task.status == status_filter)
    if priority:
        query = query.where(Task.priority == priority)
    if subject_id: query = query.where(Task.subject_id == subject_id)
    if goal_id: query = query.where(Task.goal_id == goal_id)
    if search:
        term = f"%{search}%"; query = query.where(or_(Task.title.ilike(term), Task.description.ilike(term)))
    if due == "today": query = query.where(Task.due_date >= now.replace(hour=0, minute=0, second=0, microsecond=0), Task.due_date < now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1))
    if due == "week": query = query.where(Task.due_date >= now, Task.due_date < now + timedelta(days=7))
    if due == "upcoming": query = query.where(Task.due_date >= now)
    if due == "overdue": query = query.where(Task.due_date < now, Task.status != TaskStatus.completed)
    if sort == "created_at": query = query.order_by(desc(Task.created_at))
    elif sort == "updated_at": query = query.order_by(desc(Task.updated_at))
    elif sort == "due_date": query = query.order_by(asc(Task.due_date).nullslast())
    elif sort == "priority": query = query.order_by(Task.priority, desc(Task.created_at))
    elif sort == "status": query = query.order_by(Task.status, desc(Task.created_at))
    else: query = query.order_by((Task.status != TaskStatus.completed).desc(), Task.due_date.asc().nullslast(), desc(Task.created_at))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    records = list(db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all())
    return TaskPage(items=records, page=page, page_size=page_size, total=total, pages=max(1, (total + page_size - 1) // page_size))


@tasks.get("/stats", response_model=TaskStats)
def task_stats(user: User = Depends(current_user), db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc); base = select(Task).where(Task.user_id == user.id).subquery()
    total = db.scalar(select(func.count()).select_from(base)) or 0
    pending = db.scalar(select(func.count()).select_from(base).where(base.c.status == TaskStatus.pending.value)) or 0
    in_progress = db.scalar(select(func.count()).select_from(base).where(base.c.status == TaskStatus.in_progress.value)) or 0
    completed = db.scalar(select(func.count()).select_from(base).where(base.c.status == TaskStatus.completed.value)) or 0
    overdue = db.scalar(select(func.count()).select_from(base).where(base.c.due_date < now, base.c.status != TaskStatus.completed.value)) or 0
    return TaskStats(total=total, pending=pending, in_progress=in_progress, completed=completed, overdue=overdue, completion_rate=round((completed / total) * 100, 1) if total else 0)


def owned_task(task_id: str, user: User, db: Session) -> Task:
    task = db.scalar(select(Task).where(Task.id == task_id, Task.user_id == user.id))
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada.")
    return task


@tasks.get("/{task_id}", response_model=TaskOutput)
def get_task(task_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return owned_task(task_id, user, db)


@tasks.patch("/{task_id}", response_model=TaskOutput)
def update_task(task_id: str, payload: TaskUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    task = owned_task(task_id, user, db)
    previous_goal = task.goal_id
    validate_task_links(payload, user, db)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, key, value)
    if task.status == TaskStatus.completed and not task.completed_at:
        task.completed_at = datetime.now(timezone.utc)
    elif task.status != TaskStatus.completed:
        task.completed_at = None
    recalculate_goal(previous_goal, user.id, db)
    recalculate_goal(task.goal_id, user.id, db)
    db.commit()
    db.refresh(task)
    return task


@tasks.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    task = owned_task(task_id, user, db)
    goal_id = task.goal_id
    db.delete(task)
    db.commit()
    recalculate_goal(goal_id, user.id, db); db.commit()


@subjects.post("", response_model=SubjectOutput, status_code=201)
def create_subject(payload: SubjectInput, user: User = Depends(current_user), db: Session = Depends(get_db)):
    subject = Subject(**payload.model_dump(), user_id=user.id)
    db.add(subject); db.commit(); db.refresh(subject)
    return subject


@subjects.get("", response_model=list[SubjectOutput])
def list_subjects(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return list(db.scalars(select(Subject).where(Subject.user_id == user.id).order_by(Subject.name)).all())


def subject_stats(subject_id: str, user_id: str, db: Session):
    total_tasks = db.scalar(select(func.count(Task.id)).where(Task.subject_id == subject_id, Task.user_id == user_id)) or 0
    completed_tasks = db.scalar(select(func.count(Task.id)).where(Task.subject_id == subject_id, Task.user_id == user_id, Task.status == TaskStatus.completed)) or 0
    total_sessions = db.scalar(select(func.count(StudySession.id)).where(StudySession.subject_id == subject_id, StudySession.user_id == user_id, StudySession.status == SessionStatus.completed.value)) or 0
    seconds = db.scalar(select(func.coalesce(func.sum(StudySession.duration_seconds), 0)).where(StudySession.subject_id == subject_id, StudySession.user_id == user_id, StudySession.status == SessionStatus.completed.value)) or 0
    return SubjectStats(total_tasks=total_tasks, completed_tasks=completed_tasks, total_sessions=total_sessions, studied_minutes=int(seconds) // 60, progress=round(completed_tasks / total_tasks * 100) if total_tasks else 0)


@subjects.get("/stats")
def subject_summary(user: User = Depends(current_user), db: Session = Depends(get_db)):
    records = list(db.scalars(select(Subject).where(Subject.user_id == user.id)).all())
    return {"total": len(records), "active": sum(s.status != "COMPLETED" and s.status != "ARCHIVED" for s in records), "in_progress": sum(s.status == "IN_PROGRESS" for s in records), "completed": sum(s.status == "COMPLETED" for s in records), "overdue": sum(bool(s.target_date and s.target_date < datetime.now(timezone.utc) and s.status != "COMPLETED") for s in records)}


@subjects.get("/{subject_id}", response_model=SubjectDetail)
def get_subject_detail(subject_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    subject = db.scalar(select(Subject).where(Subject.id == subject_id, Subject.user_id == user.id))
    if not subject: raise HTTPException(404, "Disciplina não encontrada.")
    tasks_related = list(db.scalars(select(Task).where(Task.subject_id == subject.id, Task.user_id == user.id)).all())
    goals_related = list(db.scalars(select(Goal).where(Goal.subject_id == subject.id, Goal.user_id == user.id)).all())
    for goal in goals_related:
        recalculate_goal(goal.id, user.id, db)
    # TaskOutput aceita objetos ORM, mas related_goals é uma lista de dicts.
    # Serializar explicitamente evita ResponseValidationError/HTTP 500.
    related_goals = [GoalOutput.model_validate(goal).model_dump() for goal in goals_related]
    return SubjectDetail.model_validate({**SubjectOutput.model_validate(subject).model_dump(), "stats": subject_stats(subject.id, user.id, db), "related_tasks": tasks_related, "related_goals": related_goals})


@subjects.delete("/{subject_id}", status_code=204)
def delete_subject(subject_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    subject = db.scalar(select(Subject).where(Subject.id == subject_id, Subject.user_id == user.id))
    if not subject: raise HTTPException(404, "Disciplina não encontrada.")
    related_goals = list(db.scalars(select(Goal).where(Goal.subject_id == subject.id, Goal.user_id == user.id)).all())
    related_goal_ids = {goal.id for goal in related_goals}
    task_filters = [Task.subject_id == subject.id]
    if related_goal_ids:
        task_filters.append(Task.goal_id.in_(related_goal_ids))
    affected_goal_ids = {
        goal_id for goal_id in db.scalars(select(Task.goal_id).where(
            Task.user_id == user.id,
            Task.goal_id.is_not(None),
            or_(*task_filters),
        )).all()
        if goal_id not in related_goal_ids
    }
    db.query(Task).filter(Task.user_id == user.id, or_(*task_filters)).delete(synchronize_session=False)
    if related_goal_ids:
        db.query(Goal).filter(Goal.user_id == user.id, Goal.id.in_(related_goal_ids)).delete(synchronize_session=False)
    db.query(StudySession).filter(StudySession.subject_id == subject.id, StudySession.user_id == user.id).update(
        {StudySession.subject_id: None}, synchronize_session=False
    )
    db.delete(subject); db.commit()
    for goal_id in affected_goal_ids:
        recalculate_goal(goal_id, user.id, db)
    if affected_goal_ids:
        db.commit()


@subjects.patch("/{subject_id}", response_model=SubjectOutput)
def update_subject(subject_id: str, payload: SubjectInput, user: User = Depends(current_user), db: Session = Depends(get_db)):
    subject = db.scalar(select(Subject).where(Subject.id == subject_id, Subject.user_id == user.id))
    if not subject: raise HTTPException(404, "Disciplina não encontrada.")
    for key, value in payload.model_dump().items(): setattr(subject, key, value)
    db.commit(); db.refresh(subject)
    return subject


@goals.post("", response_model=GoalOutput, status_code=201)
def create_goal(payload: GoalInput, user: User = Depends(current_user), db: Session = Depends(get_db)):
    data = payload.model_dump()
    if data.get("metric") == "TIME" and not data.get("subject_id"):
        raise HTTPException(400, "Metas de tempo precisam estar vinculadas a uma disciplina.")
    if data.get("subject_id") and not db.scalar(select(Subject).where(Subject.id == data["subject_id"], Subject.user_id == user.id)):
        raise HTTPException(404, "Disciplina não encontrada.")
    data["progress"] = 0
    goal = Goal(**data, user_id=user.id, status="PLANNED")
    if goal.status == "COMPLETED": goal.completed_at = datetime.now(timezone.utc)
    db.add(goal); db.commit(); db.refresh(goal)
    return goal


@goals.get("", response_model=list[GoalOutput])
def list_goals(user: User = Depends(current_user), db: Session = Depends(get_db)):
    records = list(db.scalars(select(Goal).where(Goal.user_id == user.id).order_by(Goal.due_date.asc().nullslast())).all())
    for goal in records: recalculate_goal(goal.id, user.id, db)
    db.commit()
    return records


@goals.get("/stats")
def goal_stats(user: User = Depends(current_user), db: Session = Depends(get_db)):
    records = list(db.scalars(select(Goal).where(Goal.user_id == user.id)).all())
    for goal in records: recalculate_goal(goal.id, user.id, db)
    db.commit()
    return {"active": sum(goal.status != "COMPLETED" for goal in records), "in_progress": sum(goal.status == "IN_PROGRESS" for goal in records), "completed": sum(goal.status == "COMPLETED" for goal in records), "overdue": sum(goal.status == "OVERDUE" for goal in records)}


@goals.get("/{goal_id}")
def goal_detail(goal_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    goal = db.scalar(select(Goal).where(Goal.id == goal_id, Goal.user_id == user.id))
    if not goal: raise HTTPException(404, "Meta não encontrada.")
    recalculate_goal(goal.id, user.id, db); db.commit(); db.refresh(goal)
    related = list(db.scalars(select(Task).where(Task.goal_id == goal.id, Task.user_id == user.id)).all())
    return {**GoalOutput.model_validate(goal).model_dump(), "related_tasks": related, "total_tasks": len(related), "completed_tasks": sum(task.status == TaskStatus.completed for task in related)}


@goals.patch("/{goal_id}", response_model=GoalOutput)
def update_goal(goal_id: str, payload: GoalInput, user: User = Depends(current_user), db: Session = Depends(get_db)):
    goal = db.scalar(select(Goal).where(Goal.id == goal_id, Goal.user_id == user.id))
    if not goal: raise HTTPException(404, "Meta não encontrada.")
    data = payload.model_dump()
    if data.get("metric") == "TIME" and not data.get("subject_id"):
        raise HTTPException(400, "Metas de tempo precisam estar vinculadas a uma disciplina.")
    if data.get("subject_id") and not db.scalar(select(Subject).where(Subject.id == data["subject_id"], Subject.user_id == user.id)):
        raise HTTPException(404, "Disciplina não encontrada.")
    for key, value in data.items(): setattr(goal, key, value)
    recalculate_goal(goal.id, user.id, db)
    db.commit(); db.refresh(goal)
    return goal


@goals.delete("/{goal_id}", status_code=204)
def delete_goal(goal_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    goal = db.scalar(select(Goal).where(Goal.id == goal_id, Goal.user_id == user.id))
    if not goal: raise HTTPException(404, "Meta não encontrada.")
    db.query(Task).filter(Task.goal_id == goal.id, Task.user_id == user.id).delete(synchronize_session=False)
    db.delete(goal); db.commit()


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _elapsed_seconds(started: datetime | None, ended: datetime) -> int:
    if not started:
        return 0
    return max(0, int((_utc(ended) - _utc(started)).total_seconds()))


def _session_seconds(session: StudySession, now: datetime | None = None) -> int:
    total = max(0, int(session.duration_seconds or 0))
    if session.status == SessionStatus.running.value and session.active_started_at:
        total += _elapsed_seconds(session.active_started_at, now or datetime.now(timezone.utc))
    return total


def _session_payload(session: StudySession, now: datetime | None = None) -> dict:
    seconds = _session_seconds(session, now)
    return {
        "id": session.id,
        "subject_id": session.subject_id,
        "started_at": session.started_at,
        "ended_at": session.ended_at,
        "duration_minutes": seconds // 60,
        "duration_seconds": seconds,
        "paused_duration_seconds": int(session.paused_duration_seconds or 0),
        "status": session.status or SessionStatus.completed.value,
        "active_started_at": session.active_started_at,
        "paused_at": session.paused_at,
        "notes": session.notes,
        "created_at": session.created_at,
        "updated_at": session.updated_at or session.created_at,
    }


def _owned_subject(subject_id: str, user: User, db: Session) -> Subject:
    subject = db.scalar(select(Subject).where(Subject.id == subject_id, Subject.user_id == user.id))
    if not subject:
        raise HTTPException(404, "Disciplina não encontrada.")
    return subject


def _required_subject(subject_id: str | None, user: User, db: Session) -> Subject:
    if not subject_id:
        raise HTTPException(400, "Uma sessão precisa estar vinculada a uma disciplina.")
    return _owned_subject(subject_id, user, db)


def _owned_session(session_id: str, user: User, db: Session) -> StudySession:
    session = db.scalar(select(StudySession).where(StudySession.id == session_id, StudySession.user_id == user.id))
    if not session:
        raise HTTPException(404, "Sessão não encontrada.")
    return session


@sessions.post("", response_model=SessionOutput, status_code=201)
def create_session(payload: SessionInput, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Compatibilidade para registros históricos; novos estudos usam /start."""
    _required_subject(payload.subject_id, user, db)
    if payload.status != SessionStatus.completed:
        raise HTTPException(400, "Use o fluxo de início, pausa e finalização para sessões ativas.")
    seconds = payload.duration_seconds or payload.duration_minutes * 60
    now = datetime.now(timezone.utc)
    session = StudySession(subject_id=payload.subject_id, started_at=payload.started_at, ended_at=payload.ended_at or now,
                           duration_minutes=seconds // 60, duration_seconds=seconds, paused_duration_seconds=0,
                           status=SessionStatus.completed.value, notes=payload.notes, user_id=user.id, updated_at=now)
    db.add(session); db.commit(); db.refresh(session)
    return _session_payload(session)


@sessions.post("/start", response_model=SessionOutput, status_code=201)
def start_session(payload: SessionStartInput, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _owned_subject(payload.subject_id, user, db)
    active = db.scalar(select(StudySession).where(StudySession.user_id == user.id, StudySession.status.in_([SessionStatus.running.value, SessionStatus.paused.value])))
    if active:
        raise HTTPException(409, "Você já possui uma sessão de estudo em andamento.")
    now = datetime.now(timezone.utc)
    session = StudySession(subject_id=payload.subject_id, started_at=now, active_started_at=now,
                           duration_minutes=0, duration_seconds=0, paused_duration_seconds=0,
                           status=SessionStatus.running.value, user_id=user.id, updated_at=now)
    db.add(session)
    try:
        db.commit(); db.refresh(session)
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Você já possui uma sessão de estudo em andamento.")
    return _session_payload(session, now)


@sessions.get("/active", response_model=SessionOutput | None)
def active_session(user: User = Depends(current_user), db: Session = Depends(get_db)):
    session = db.scalar(select(StudySession).where(StudySession.user_id == user.id, StudySession.status.in_([SessionStatus.running.value, SessionStatus.paused.value])).order_by(StudySession.created_at.desc()))
    return _session_payload(session) if session else None


@sessions.post("/{session_id}/pause", response_model=SessionOutput)
def pause_session(session_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    session = _owned_session(session_id, user, db)
    if session.status != SessionStatus.running.value:
        raise HTTPException(409, "A sessão só pode ser pausada enquanto está em andamento.")
    now = datetime.now(timezone.utc)
    session.duration_seconds = _session_seconds(session, now)
    session.duration_minutes = session.duration_seconds // 60
    session.paused_at = now; session.active_started_at = None; session.status = SessionStatus.paused.value; session.updated_at = now
    db.commit(); db.refresh(session)
    return _session_payload(session, now)


@sessions.post("/{session_id}/resume", response_model=SessionOutput)
def resume_session(session_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    session = _owned_session(session_id, user, db)
    if session.status != SessionStatus.paused.value:
        raise HTTPException(409, "A sessão só pode ser retomada quando está pausada.")
    now = datetime.now(timezone.utc)
    session.paused_duration_seconds = int(session.paused_duration_seconds or 0) + _elapsed_seconds(session.paused_at, now)
    session.paused_at = None; session.active_started_at = now; session.status = SessionStatus.running.value; session.updated_at = now
    db.commit(); db.refresh(session)
    return _session_payload(session, now)


@sessions.post("/{session_id}/finish", response_model=SessionOutput)
def finish_session(session_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    session = _owned_session(session_id, user, db)
    if session.status not in (SessionStatus.running.value, SessionStatus.paused.value):
        raise HTTPException(409, "A sessão já foi finalizada ou cancelada.")
    now = datetime.now(timezone.utc)
    session.duration_seconds = _session_seconds(session, now)
    session.duration_minutes = session.duration_seconds // 60
    session.ended_at = now; session.active_started_at = None; session.paused_at = None; session.status = SessionStatus.completed.value; session.updated_at = now
    db.commit(); db.refresh(session)
    return _session_payload(session, now)


@sessions.post("/{session_id}/cancel", response_model=SessionOutput)
def cancel_session(session_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    session = _owned_session(session_id, user, db)
    if session.status not in (SessionStatus.running.value, SessionStatus.paused.value):
        raise HTTPException(409, "A sessão não está ativa.")
    now = datetime.now(timezone.utc)
    session.duration_seconds = 0; session.duration_minutes = 0; session.ended_at = now; session.active_started_at = None; session.paused_at = None; session.status = SessionStatus.cancelled.value; session.updated_at = now
    db.commit(); db.refresh(session)
    return _session_payload(session, now)


@sessions.get("", response_model=list[SessionOutput])
def list_sessions(user: User = Depends(current_user), db: Session = Depends(get_db)):
    records = list(db.scalars(select(StudySession).where(StudySession.user_id == user.id).order_by(StudySession.started_at.desc())).all())
    return [_session_payload(item) for item in records]


@sessions.get("/stats", response_model=SessionStats)
def session_stats(user: User = Depends(current_user), db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = day_start - timedelta(days=day_start.weekday())
    month_start = day_start.replace(day=1)
    records = list(db.scalars(select(StudySession).where(StudySession.user_id == user.id, StudySession.status == SessionStatus.completed.value)).all())
    def summarize(start: datetime):
        selected = [item for item in records if _utc(item.started_at) >= start]
        return sum(int(item.duration_seconds or item.duration_minutes * 60) for item in selected), len(selected)
    today, today_count = summarize(day_start); week, week_count = summarize(week_start); month, month_count = summarize(month_start)
    return SessionStats(today_seconds=today, week_seconds=week, month_seconds=month, total_seconds=sum(int(item.duration_seconds or item.duration_minutes * 60) for item in records), today_sessions=today_count, week_sessions=week_count, month_sessions=month_count, total_sessions=len(records))


@sessions.delete("/{session_id}", status_code=204)
def delete_session(session_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    session = _owned_session(session_id, user, db)
    if session.status in (SessionStatus.running.value, SessionStatus.paused.value):
        raise HTTPException(409, "Finalize ou cancele a sessão antes de apagá-la.")
    subject_id = session.subject_id
    db.delete(session); db.commit()
    if subject_id:
        goal_ids = db.scalars(select(Goal.id).where(
            Goal.user_id == user.id,
            Goal.subject_id == subject_id,
            Goal.metric == "TIME",
        )).all()
        for goal_id in goal_ids:
            recalculate_goal(goal_id, user.id, db)
        if goal_ids:
            db.commit()


@sessions.patch("/{session_id}", response_model=SessionOutput)
def update_session(session_id: str, payload: SessionInput, user: User = Depends(current_user), db: Session = Depends(get_db)):
    session = _owned_session(session_id, user, db)
    if session.status != SessionStatus.cancelled.value:
        raise HTTPException(409, "Sessões em andamento ou concluídas não podem ser editadas.")
    _required_subject(payload.subject_id, user, db)
    session.subject_id = payload.subject_id; session.notes = payload.notes; db.commit(); db.refresh(session)
    return _session_payload(session)


@dashboard.get("", response_model=DashboardOutput)
def get_dashboard(user: User = Depends(current_user), db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = day_start - timedelta(days=now.weekday())
    pending = db.scalar(select(func.count(Task.id)).where(Task.user_id == user.id, Task.status == TaskStatus.pending)) or 0
    completed = db.scalar(select(func.count(Task.id)).where(Task.user_id == user.id, Task.status == TaskStatus.completed)) or 0
    overdue = db.scalar(select(func.count(Task.id)).where(Task.user_id == user.id, Task.status != TaskStatus.completed, Task.due_date < now)) or 0
    active_goals = db.scalar(select(func.count(Goal.id)).where(Goal.user_id == user.id, Goal.status == "ACTIVE")) or 0
    completed_goals = db.scalar(select(func.count(Goal.id)).where(Goal.user_id == user.id, Goal.status == "COMPLETED")) or 0
    studied_seconds = db.scalar(select(func.coalesce(func.sum(StudySession.duration_seconds), 0)).where(StudySession.user_id == user.id, StudySession.status == SessionStatus.completed.value)) or 0
    week_study_seconds = db.scalar(select(func.coalesce(func.sum(StudySession.duration_seconds), 0)).where(
        StudySession.user_id == user.id,
        StudySession.status == SessionStatus.completed.value,
        StudySession.started_at >= week_start,
        StudySession.started_at <= now,
    )) or 0
    studied = int(studied_seconds) // 60
    recent = list(db.scalars(select(StudySession).where(StudySession.user_id == user.id, StudySession.status == SessionStatus.completed.value).order_by(StudySession.started_at.desc()).limit(5)).all())
    return DashboardOutput(pending_tasks=pending, completed_tasks=completed, overdue_tasks=overdue, active_goals=active_goals,
                           completed_goals=completed_goals, studied_minutes=studied, week_study_seconds=int(week_study_seconds),
                           weekly_study_goal_minutes=user.weekly_study_goal_minutes, current_streak=0, recent_sessions=recent)


@calendar.get("", response_model=list[CalendarEvent])
def get_calendar(user: User = Depends(current_user), db: Session = Depends(get_db)):
    events: list[CalendarEvent] = []
    for task in db.scalars(select(Task).where(Task.user_id == user.id, Task.due_date.is_not(None))).all():
        events.append(CalendarEvent(id=task.id, title=task.title, event_type="TASK", date=task.due_date, status=task.status.value))
    for goal in db.scalars(select(Goal).where(Goal.user_id == user.id, Goal.due_date.is_not(None))).all():
        events.append(CalendarEvent(id=goal.id, title=goal.title, event_type="GOAL", date=goal.due_date, status=goal.status))
    subject_names = {subject.id: subject.name for subject in db.scalars(select(Subject).where(Subject.user_id == user.id)).all()}
    for session in db.scalars(select(StudySession).where(StudySession.user_id == user.id, StudySession.status == SessionStatus.completed.value)).all():
        subject_name = subject_names.get(session.subject_id, "Disciplina")
        events.append(CalendarEvent(id=session.id, title=f"Estudo · {subject_name}", event_type="STUDY_SESSION", date=session.started_at, status=session.status))
    return sorted(events, key=lambda event: event.date)


@history.get("", response_model=list[HistoryItem])
def get_history(user: User = Depends(current_user), db: Session = Depends(get_db)):
    items: list[HistoryItem] = []
    for task in db.scalars(select(Task).where(Task.user_id == user.id, Task.status == TaskStatus.completed)).all():
        items.append(HistoryItem(id=task.id, title=task.title, event_type="TASK_COMPLETED", date=task.completed_at or task.updated_at))
    for goal in db.scalars(select(Goal).where(Goal.user_id == user.id, Goal.status == "COMPLETED")).all():
        items.append(HistoryItem(id=goal.id, title=goal.title, event_type="GOAL_COMPLETED", date=goal.completed_at or goal.created_at))
    for session in db.scalars(select(StudySession).where(StudySession.user_id == user.id, StudySession.status == SessionStatus.completed.value)).all():
        items.append(HistoryItem(id=session.id, title=f"Sessão de {session.duration_minutes} minutos", event_type="STUDY_SESSION", date=session.started_at))
    return sorted(items, key=lambda item: item.date, reverse=True)


@notifications.get("", response_model=list[NotificationOutput])
def list_notifications(user: User = Depends(current_user), db: Session = Depends(get_db)):
    if user.notifications_enabled:
        now = datetime.now(timezone.utc)
        cutoff = (now + timedelta(days=3)).date()
        reminders = set()
        for task in db.scalars(select(Task).where(
            Task.user_id == user.id,
            Task.status != TaskStatus.completed,
            Task.due_date.is_not(None),
        )).all():
            due_at = _utc(task.due_date)
            if due_at.date() <= cutoff:
                days_left = (due_at.date() - now.date()).days
                timing = "está vencida" if days_left < 0 else "vence hoje" if days_left == 0 else f"vence em {days_left} dia(s)"
                reminders.add(("Prazo de tarefa", f'A tarefa "{task.title}" {timing} ({due_at.strftime("%d/%m/%Y")}).'))
        for goal in db.scalars(select(Goal).where(
            Goal.user_id == user.id,
            Goal.status != "COMPLETED",
            Goal.due_date.is_not(None),
        )).all():
            due_at = _utc(goal.due_date)
            if due_at.date() <= cutoff:
                days_left = (due_at.date() - now.date()).days
                timing = "está vencida" if days_left < 0 else "vence hoje" if days_left == 0 else f"vence em {days_left} dia(s)"
                reminders.add(("Prazo de meta", f'A meta "{goal.title}" {timing} ({due_at.strftime("%d/%m/%Y")}).'))
        existing = list(db.scalars(select(Notification).where(
            Notification.user_id == user.id,
            Notification.kind == "DEADLINE",
        )).all())
        existing_keys = {(item.title, item.message) for item in existing}
        for item in existing:
            if (item.title, item.message) not in reminders:
                db.delete(item)
        for title, message in reminders - existing_keys:
            db.add(Notification(user_id=user.id, title=title, message=message, kind="DEADLINE"))
        db.commit()
    return list(db.scalars(select(Notification).where(Notification.user_id == user.id).order_by(Notification.created_at.desc()).limit(50)).all())


@notifications.patch("/{notification_id}/read", response_model=NotificationOutput)
def mark_notification_read(notification_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    notification = db.scalar(select(Notification).where(Notification.id == notification_id, Notification.user_id == user.id))
    if not notification: raise HTTPException(404, "Notificação não encontrada.")
    notification.read_at = datetime.now(timezone.utc); db.commit(); db.refresh(notification)
    return notification


router.include_router(auth)
router.include_router(tasks)
router.include_router(subjects)
router.include_router(goals)
router.include_router(sessions)
router.include_router(dashboard)
router.include_router(users)
router.include_router(calendar)
router.include_router(history)
router.include_router(notifications)
