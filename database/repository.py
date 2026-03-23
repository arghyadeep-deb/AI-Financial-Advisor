from sqlalchemy.orm import Session
from backend.models.models import User, FinancialProfile, FinancialState, Thread, Message
from datetime import datetime


class UserRepository:

    def __init__(self, db: Session):
        self.db = db

    def create(self, email: str, full_name: str, hashed_password: str) -> User:
        user = User(
            email=email,
            full_name=full_name,
            hashed_password=hashed_password
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_by_email(self, email: str) -> User:
        return self.db.query(User).filter(User.email == email).first()

    def get_by_id(self, user_id: int) -> User:
        return self.db.query(User).filter(User.id == user_id).first()


class ProfileRepository:

    def __init__(self, db: Session):
        self.db = db

    def create_or_update(self, user_id: int, data: dict) -> FinancialProfile:
        profile = self.db.query(FinancialProfile).filter(
            FinancialProfile.user_id == user_id
        ).first()

        if profile:
            for key, value in data.items():
                setattr(profile, key, value)
            profile.updated_at = datetime.utcnow()
        else:
            profile = FinancialProfile(user_id=user_id, **data)
            self.db.add(profile)

        self.db.commit()
        self.db.refresh(profile)
        return profile

    def get_by_user(self, user_id: int) -> FinancialProfile:
        return self.db.query(FinancialProfile).filter(
            FinancialProfile.user_id == user_id
        ).first()


class FinancialStateRepository:

    def __init__(self, db: Session):
        self.db = db

    def create_or_update(self, user_id: int, data: dict) -> FinancialState:
        state = self.db.query(FinancialState).filter(
            FinancialState.user_id == user_id
        ).first()

        if state:
            for key, value in data.items():
                setattr(state, key, value)
            state.last_updated = datetime.utcnow()
        else:
            state = FinancialState(user_id=user_id, **data)
            self.db.add(state)

        self.db.commit()
        self.db.refresh(state)
        return state

    def get_by_user(self, user_id: int) -> FinancialState:
        return self.db.query(FinancialState).filter(
            FinancialState.user_id == user_id
        ).first()


class ThreadRepository:

    def __init__(self, db: Session):
        self.db = db

    def create(self, user_id: int, title: str, thread_type: str) -> Thread:
        thread = Thread(
            user_id=user_id,
            title=title,
            thread_type=thread_type
        )
        self.db.add(thread)
        self.db.commit()
        self.db.refresh(thread)
        return thread

    def get_user_threads(self, user_id: int):
        return (
            self.db.query(Thread)
            .filter(Thread.user_id == user_id)
            .order_by(Thread.created_at.desc())
            .all()
        )

    def get_thread(self, thread_id: int) -> Thread:
        return self.db.query(Thread).filter(Thread.id == thread_id).first()


class MessageRepository:

    def __init__(self, db: Session):
        self.db = db

    def create(self, thread_id: int, role: str, content: str, metadata: dict = None) -> Message:
        msg = Message(
            thread_id=thread_id,
            role=role,
            content=content,
            message_metadata=metadata or {}
        )
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)
        return msg

    def get_thread_messages(self, thread_id: int):
        return (
            self.db.query(Message)
            .filter(Message.thread_id == thread_id)
            .order_by(Message.created_at)
            .all()
        )