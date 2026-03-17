import sqlalchemy as sa

from .base import Base


class User(Base):
    __tablename__ = "users"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    username = sa.Column(sa.String(255), unique=True, nullable=False)
    password_hash = sa.Column(sa.String(255), nullable=False)
    created_at = sa.Column(
        sa.DateTime(timezone=False), server_default=sa.func.now(), nullable=False
    )
