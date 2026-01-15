import uuid
import secrets
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship

from . import Base


class Webhook(Base):
    __tablename__ = 'webhooks'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)

    # Webhook configuration
    name = Column(String(255), nullable=False)
    url = Column(Text, nullable=False)
    secret = Column(String(64), nullable=False, default=lambda: secrets.token_hex(32))

    # Events to trigger on
    events = Column(ARRAY(String), default=list)  # ['page_view', 'click', 'custom', '*']

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Statistics
    last_triggered_at = Column(DateTime, nullable=True)
    success_count = Column(String(20), default='0')
    failure_count = Column(String(20), default='0')

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship('User', back_populates='webhooks')

    def __repr__(self):
        return f'<Webhook {self.name}>'

    def to_dict(self):
        return {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'name': self.name,
            'url': self.url,
            'events': self.events,
            'is_active': self.is_active,
            'last_triggered_at': self.last_triggered_at.isoformat() if self.last_triggered_at else None,
            'success_count': self.success_count,
            'failure_count': self.failure_count,
            'created_at': self.created_at.isoformat(),
        }

    def should_trigger(self, event_type):
        """Check if this webhook should be triggered for the given event type."""
        if not self.is_active:
            return False
        if '*' in self.events:
            return True
        return event_type in self.events
