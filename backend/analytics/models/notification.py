import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from . import Base


class Notification(Base):
    __tablename__ = 'notifications'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)

    # Notification type
    notification_type = Column(String(20), nullable=False)  # 'email', 'in_app', 'webhook'

    # Content
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    extra_data = Column(JSONB, default=dict)  # Additional data (e.g., email subject, webhook payload)

    # Status
    status = Column(String(20), default='pending', nullable=False, index=True)  # 'pending', 'sent', 'failed', 'read'
    error_message = Column(Text, nullable=True)

    # For in-app notifications
    is_read = Column(Boolean, default=False, nullable=False)
    read_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    sent_at = Column(DateTime, nullable=True)

    # Retry tracking
    retry_count = Column(String(10), default='0')

    # Relationships
    user = relationship('User', back_populates='notifications')

    def __repr__(self):
        return f'<Notification {self.notification_type}:{self.title}>'

    def to_dict(self):
        return {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'notification_type': self.notification_type,
            'title': self.title,
            'content': self.content,
            'extra_data': self.extra_data,
            'status': self.status,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat(),
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'read_at': self.read_at.isoformat() if self.read_at else None,
        }
