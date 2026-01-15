from celery import Celery
from celery.schedules import crontab
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# Load configuration
DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    'postgresql://postgres:postgres@localhost:5432/analytics'
)
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/1')

# Create Celery app
celery_app = Celery(
    'analytics',
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        'analytics.tasks.event_processing',
        'analytics.tasks.notifications',
        'analytics.tasks.aggregations',
    ]
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes
    task_soft_time_limit=240,  # 4 minutes
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)

# Task routing
celery_app.conf.task_routes = {
    'analytics.tasks.event_processing.*': {'queue': 'events'},
    'analytics.tasks.notifications.*': {'queue': 'notifications'},
    'analytics.tasks.aggregations.*': {'queue': 'reports'},
}

# Scheduled tasks (beat)
celery_app.conf.beat_schedule = {
    'generate-daily-report': {
        'task': 'analytics.tasks.aggregations.generate_daily_report',
        'schedule': crontab(hour=0, minute=5),  # Run at 00:05 daily
    },
    'cleanup-old-events': {
        'task': 'analytics.tasks.aggregations.cleanup_old_events',
        'schedule': crontab(hour=3, minute=0),  # Run at 03:00 daily
    },
}


def get_db_session():
    """Create a database session for Celery tasks."""
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    return Session()
