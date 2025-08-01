from sqlalchemy.orm import Session
from typing import List, Optional
import hashlib

from app.models.database import User


class UserService:
    """Сервис для работы с пользователями"""

    @staticmethod
    def _hash_password(password: str) -> str:
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def is_first_user(self, db: Session) -> bool:
        return db.query(User).count() == 0

    def get_user_by_username(self, db: Session, username: str) -> Optional[User]:
        return db.query(User).filter(User.username == username).first()

    def create_user(
        self,
        db: Session,
        username: str,
        password: str,
        *,
        is_admin: bool = False,
        is_active: bool = False,
    ) -> User:
        user = User(
            username=username,
            password_hash=self._hash_password(password),
            is_admin=is_admin,
            is_active=is_active,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def authenticate_user(
        self, db: Session, username: str, password: str
    ) -> Optional[User]:
        user = self.get_user_by_username(db, username)
        if not user:
            return None
        if user.password_hash != self._hash_password(password):
            return None
        if not user.is_active:
            return None
        return user

    def get_all_users(self, db: Session) -> List[User]:
        return db.query(User).all()

    def approve_user(self, db: Session, user_id: int) -> None:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.is_active = True
            db.commit()

    def delete_user(self, db: Session, user_id: int) -> None:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            db.delete(user)
            db.commit()


user_service = UserService()
