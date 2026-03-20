"""
Seed script — populates the database with realistic demo data.

Usage (from the backend/ directory):
    python scripts/seed.py                  # uses DATABASE_URL env var
    python scripts/seed.py --reset          # drop all rows first, then seed
    python scripts/seed.py --users 5        # create 5 users (default: 3)

Inside Docker:
    docker-compose exec backend python scripts/seed.py --reset
"""

import argparse
import os
import random
import secrets
import sys
import uuid
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# Bootstrap: make sure the analytics package is importable when this script
# is run directly from the backend/ directory.
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bcrypt
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from analytics.models import Base
from analytics.models.user import User
from analytics.models.event import Event
from analytics.models.notification import Notification
from analytics.models.webhook import Webhook

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    'postgresql://eventflow:eventflow@localhost:5433/eventflow',
)

SEED_USERS = [
    {'email': 'alice@demo.com',   'password': 'AlicePass1!', 'name': 'Alice Chen'},
    {'email': 'bob@demo.com',     'password': 'BobPass1!',   'name': 'Bob Nguyen'},
    {'email': 'charlie@demo.com', 'password': 'CharlieP1!',  'name': 'Charlie Osei'},
]

EVENT_TYPES = ['page_view', 'click', 'form_submit', 'custom', 'scroll', 'error']

EVENT_NAMES = {
    'page_view':   ['home_page', 'pricing_page', 'docs_page', 'login_page', 'dashboard'],
    'click':       ['cta_button', 'nav_link', 'signup_button', 'download_btn', 'logo'],
    'form_submit': ['contact_form', 'signup_form', 'feedback_form', 'newsletter'],
    'custom':      ['video_play', 'file_upload', 'search_query', 'api_call'],
    'scroll':      ['50_percent', '75_percent', '100_percent'],
    'error':       ['404_not_found', 'api_timeout', 'validation_error', 'payment_failed'],
}

URLS = [
    'https://app.eventflow.io/',
    'https://app.eventflow.io/dashboard',
    'https://app.eventflow.io/events',
    'https://app.eventflow.io/settings',
    'https://app.eventflow.io/pricing',
    'https://app.eventflow.io/docs',
]

REFERRERS = [
    'https://google.com',
    'https://twitter.com',
    'https://github.com',
    '',
    '',
    '',  # organic / direct (higher weight)
]

NOTIFICATION_TEMPLATES = [
    {
        'type': 'in_app',
        'title': 'Welcome to EventFlow!',
        'content': 'Your account is set up and ready. Start tracking events with your API key.',
        'status': 'sent',
        'is_read': True,
    },
    {
        'type': 'in_app',
        'title': 'Daily report ready',
        'content': 'Your analytics report for yesterday is available. You recorded 142 events across 38 sessions.',
        'status': 'sent',
        'is_read': False,
    },
    {
        'type': 'in_app',
        'title': 'Webhook delivery failure',
        'content': 'Your webhook "Slack Alerts" failed to deliver 3 events. Check the endpoint URL.',
        'status': 'sent',
        'is_read': False,
    },
    {
        'type': 'email',
        'title': 'Weekly summary',
        'content': 'Here is your weekly analytics summary: 1,024 events, 87 unique sessions, top page: /dashboard.',
        'status': 'sent',
        'is_read': True,
    },
    {
        'type': 'in_app',
        'title': 'New login detected',
        'content': 'A new login was detected from 203.0.113.42 (Berlin, DE). If this was not you, change your password.',
        'status': 'sent',
        'is_read': False,
    },
]

WEBHOOK_TEMPLATES = [
    {
        'name': 'Slack Alerts',
        'url': 'https://hooks.slack.com/services/DEMO/DEMO/demo',
        'events': ['error', 'form_submit'],
        'is_active': True,
        'success_count': '47',
        'failure_count': '3',
    },
    {
        'name': 'Data Warehouse',
        'url': 'https://ingest.example.com/eventflow',
        'events': ['*'],
        'is_active': True,
        'success_count': '1204',
        'failure_count': '0',
    },
    {
        'name': 'Legacy CRM (disabled)',
        'url': 'https://crm.legacy.internal/hook',
        'events': ['form_submit'],
        'is_active': False,
        'success_count': '12',
        'failure_count': '91',
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()


def random_past(days_back: int = 30) -> datetime:
    offset = timedelta(
        days=random.randint(0, days_back),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
        seconds=random.randint(0, 59),
    )
    return datetime.utcnow() - offset


def make_session_id() -> str:
    return secrets.token_hex(16)


# ---------------------------------------------------------------------------
# Seed functions
# ---------------------------------------------------------------------------

def reset_tables(session):
    print('  Deleting existing rows...')
    for table in ('notifications', 'events', 'webhooks', 'users'):
        session.execute(text(f'DELETE FROM {table}'))
    session.flush()


def seed_users(session, user_specs):
    users = []
    for spec in user_specs:
        user = User(
            email=spec['email'],
            password_hash=hash_password(spec['password']),
            api_key=secrets.token_hex(32),
            name=spec['name'],
            is_active=True,
            created_at=random_past(90),
        )
        session.add(user)
        users.append(user)
        print(f'  User: {spec["email"]}')
    session.flush()
    return users


def seed_events(session, users, events_per_user: int = 60):
    total = 0
    for user in users:
        # Group events into sessions (5–15 events per session)
        remaining = events_per_user
        while remaining > 0:
            session_size = min(random.randint(5, 15), remaining)
            sid = make_session_id()
            session_start = random_past(30)

            for i in range(session_size):
                etype = random.choice(EVENT_TYPES)
                ename = random.choice(EVENT_NAMES[etype])
                ts = session_start + timedelta(seconds=i * random.randint(10, 120))

                event = Event(
                    user_id=user.id,
                    event_type=etype,
                    event_name=ename,
                    properties={
                        'page': random.choice(URLS),
                        'duration_ms': random.randint(100, 5000),
                        'user_agent': 'Mozilla/5.0 (seed)',
                    },
                    session_id=sid,
                    url=random.choice(URLS),
                    referrer=random.choice(REFERRERS),
                    timestamp=ts,
                    is_processed=random.choice(['processed', 'processed', 'processed', 'pending']),
                )
                session.add(event)
                total += 1

            remaining -= session_size

    session.flush()
    print(f'  Events: {total} across {len(users)} users')


def seed_notifications(session, users):
    total = 0
    for user in users:
        templates = random.sample(NOTIFICATION_TEMPLATES, k=random.randint(3, len(NOTIFICATION_TEMPLATES)))
        for tmpl in templates:
            created = random_past(14)
            n = Notification(
                user_id=user.id,
                notification_type=tmpl['type'],
                title=tmpl['title'],
                content=tmpl['content'],
                status=tmpl['status'],
                is_read=tmpl['is_read'],
                created_at=created,
                sent_at=created + timedelta(seconds=random.randint(1, 30)) if tmpl['status'] == 'sent' else None,
                read_at=created + timedelta(minutes=random.randint(5, 120)) if tmpl['is_read'] else None,
            )
            session.add(n)
            total += 1
    session.flush()
    print(f'  Notifications: {total}')


def seed_webhooks(session, users):
    total = 0
    for user in users:
        # Give each user 1–2 webhooks
        templates = random.sample(WEBHOOK_TEMPLATES, k=random.randint(1, 2))
        for tmpl in templates:
            w = Webhook(
                user_id=user.id,
                name=tmpl['name'],
                url=tmpl['url'],
                secret=secrets.token_hex(32),
                events=tmpl['events'],
                is_active=tmpl['is_active'],
                success_count=tmpl['success_count'],
                failure_count=tmpl['failure_count'],
                last_triggered_at=random_past(7) if tmpl['is_active'] else None,
                created_at=random_past(60),
            )
            session.add(w)
            total += 1
    session.flush()
    print(f'  Webhooks: {total}')


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Seed EventFlow demo data')
    parser.add_argument('--reset',  action='store_true', help='Delete all existing rows before seeding')
    parser.add_argument('--users',  type=int, default=3,  help='Number of users to create (max 3 built-in, extras are auto-generated)')
    args = parser.parse_args()

    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        print(f'\nConnecting to: {DATABASE_URL[:DATABASE_URL.index("@") + 1]}...\n')

        if args.reset:
            print('--- Reset ---')
            reset_tables(session)

        # Extend user list if --users > 3
        user_specs = SEED_USERS[:args.users]
        for i in range(len(user_specs), args.users):
            idx = i + 1
            user_specs.append({
                'email': f'user{idx}@demo.com',
                'password': f'UserPass{idx}!',
                'name': f'Demo User {idx}',
            })

        print('--- Seeding ---')
        users = seed_users(session, user_specs)
        seed_events(session, users)
        seed_notifications(session, users)
        seed_webhooks(session, users)

        session.commit()
        print('\nDone. You can log in with any of the credentials above.\n')

    except Exception as exc:
        session.rollback()
        print(f'\nSeed failed: {exc}')
        raise
    finally:
        session.close()


if __name__ == '__main__':
    main()
