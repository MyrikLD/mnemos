import sqlalchemy as sa

from .base import Base


class RevokedToken(Base):
    __tablename__ = "revoked_tokens"

    jti = sa.Column(sa.String(255), primary_key=True)
    expires_at = sa.Column(sa.DateTime, nullable=False, index=True)
