import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from . import Base


class Event(Base):
    __tablename__ = 'events'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)

    # Event identification
    event_type = Column(String(50), nullable=False, index=True)  # 'page_view', 'click', 'custom'
    event_name = Column(String(255), nullable=False, index=True)  # 'home_page', 'signup_button', etc.

    # Event data
    properties = Column(JSONB, default=dict)  # Flexible properties for the event

    # Session tracking
    session_id = Column(String(64), nullable=True, index=True)

    # Context
    url = Column(Text, nullable=True)
    referrer = Column(Text, nullable=True)
    user_agent = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)

    # Timestamps
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    processed_at = Column(DateTime, nullable=True)

    # Status
    is_processed = Column(String(20), default='pending')  # 'pending', 'processed', 'failed'

    # Relationships
    user = relationship('User', back_populates='events')

    __table_args__ = (
        Index('idx_events_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_events_type_name', 'event_type', 'event_name'),
    )

    def __repr__(self):
        return f'<Event {self.event_type}:{self.event_name}>'

    def to_dict(self):
        return {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'event_type': self.event_type,
            'event_name': self.event_name,
            'properties': self.properties,
            'session_id': self.session_id,
            'url': self.url,
            'referrer': self.referrer,
            'timestamp': self.timestamp.isoformat(),
            'is_processed': self.is_processed,
        }
