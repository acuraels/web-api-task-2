from typing import List, Optional, AsyncGenerator

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, ConfigDict

from sqlalchemy import String, Text, Boolean, Integer, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


# =======================
#   FastAPI app
# =======================

app = FastAPI(
    title="TODO API + WebSocket + Background. Устинов Даниил Николаевич РИ-330948",
    version="0.2.0",
)


@app.get("/ping")
async def ping():
    return {"message": "pong"}


# =======================
#   DB setup (SQLite + async)
# =======================

DATABASE_URL = "sqlite+aiosqlite:///./todo.db"


class Base(DeclarativeBase):
    pass


class TaskDB(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


@app.on_event("startup")
async def on_startup() -> None:
    """
    При старте приложения создаём таблицы (если их ещё нет).
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# =======================
#   Pydantic-модели
# =======================

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    completed: bool = False


class TaskCreate(TaskBase):
    """Модель для создания задачи (body в POST /tasks)."""
    pass


class TaskUpdate(BaseModel):
    """Модель для частичного обновления (body в PATCH /tasks/{id})."""
    title: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = None


class Task(TaskBase):
    """Модель, которая уходит наружу в ответах API."""
    id: int

    # важно для возврата ORM-объектов напрямую
    model_config = ConfigDict(from_attributes=True)


# =======================
#   REST /tasks (через БД)
# =======================

@app.get("/tasks", response_model=List[Task])
async def get_tasks(
    session: AsyncSession = Depends(get_session),
) -> List[Task]:
    stmt = select(TaskDB).order_by(TaskDB.id)
    result = await session.execute(stmt)
    tasks = result.scalars().all()
    return tasks


@app.get("/tasks/{task_id}", response_model=Task)
async def get_task(
    task_id: int,
    session: AsyncSession = Depends(get_session),
) -> Task:
    task = await session.get(TaskDB, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.post("/tasks", response_model=Task, status_code=201)
async def create_task(
    data: TaskCreate,
    session: AsyncSession = Depends(get_session),
) -> Task:
    task = TaskDB(
        title=data.title,
        description=data.description,
        completed=data.completed,
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)  # подтянуть id из БД
    return task


@app.patch("/tasks/{task_id}", response_model=Task)
async def update_task(
    task_id: int,
    data: TaskUpdate,
    session: AsyncSession = Depends(get_session),
) -> Task:
    task = await session.get(TaskDB, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(task, field, value)

    await session.commit()
    await session.refresh(task)
    return task


@app.delete("/tasks/{task_id}")
async def delete_task(
    task_id: int,
    session: AsyncSession = Depends(get_session),
):
    task = await session.get(TaskDB, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    await session.delete(task)
    await session.commit()
    return {"status": "deleted"}
