from datetime import datetime

from cryptography.fernet import Fernet, InvalidToken
from flask import current_app

from database import db


class SocialAccount(db.Model):
    __tablename__ = "social_accounts"
    __table_args__ = (
        db.UniqueConstraint("user_id", "platform", name="uq_user_platform"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    platform = db.Column(db.String(20), nullable=False)
    platform_user_id = db.Column(db.String(255), nullable=False)
    access_token = db.Column(db.Text, nullable=False)
    refresh_token = db.Column(db.Text, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship("User", back_populates="social_accounts")

    @staticmethod
    def _fernet():
        key = current_app.config.get("TOKEN_ENCRYPTION_KEY")
        if not key:
            raise RuntimeError("TOKEN_ENCRYPTION_KEY is not configured")
        return Fernet(key.encode() if isinstance(key, str) else key)

    @classmethod
    def encrypt_token(cls, token):
        if not token:
            return None
        return cls._fernet().encrypt(token.encode()).decode()

    @classmethod
    def decrypt_token(cls, encrypted_token):
        if not encrypted_token:
            return None
        try:
            return cls._fernet().decrypt(encrypted_token.encode()).decode()
        except InvalidToken as exc:
            raise RuntimeError("Unable to decrypt stored OAuth token") from exc

    def set_access_token(self, token):
        self.access_token = self.encrypt_token(token)

    def get_access_token(self):
        return self.decrypt_token(self.access_token)

    def set_refresh_token(self, token):
        self.refresh_token = self.encrypt_token(token)

    def get_refresh_token(self):
        return self.decrypt_token(self.refresh_token)

