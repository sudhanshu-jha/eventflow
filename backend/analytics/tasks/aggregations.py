from datetime import datetime, timedelta
import logging

from sqlalchemy import func

from .celery_app import celery_app, get_db_session
from ..models.event import Event
from ..models.user import User
from ..models.notification import Notification

logger = logging.getLogger(__name__)


@celery_app.task
def generate_daily_report():
    """Generate daily analytics report for all users."""
    session = get_db_session()

    try:
        yesterday = datetime.utcnow().date() - timedelta(days=1)
        start_of_day = datetime.combine(yesterday, datetime.min.time())
        end_of_day = datetime.combine(yesterday, datetime.max.time())

        # Get all active users
        users = session.query(User).filter(User.is_active == True).all()

        reports_generated = 0
        for user in users:
            try:
                report = generate_user_daily_report(
                    session, user, start_of_day, end_of_day
                )
                if report:
                    # Create in-app notification with report
                    notification = Notification(
                        user_id=user.id,
                        notification_type='in_app',
                        title=f'Daily Report - {yesterday.strftime("%Y-%m-%d")}',
                        content=format_report_content(report),
                        extra_data={'report': report, 'date': yesterday.isoformat()},
                        status='sent',
                        sent_at=datetime.utcnow(),
                    )
                    session.add(notification)
                    reports_generated += 1

            except Exception as e:
                logger.error(f"Error generating report for user {user.id}: {str(e)}")

        session.commit()
        logger.info(f"Generated {reports_generated} daily reports")
        return {'success': True, 'reports_generated': reports_generated}

    except Exception as e:
        logger.error(f"Error in daily report generation: {str(e)}")
        session.rollback()
        return {'success': False, 'error': str(e)}

    finally:
        session.close()


def generate_user_daily_report(session, user, start_date, end_date):
    """Generate a daily report for a specific user."""
    base_query = session.query(Event).filter(
        Event.user_id == user.id,
        Event.timestamp >= start_date,
        Event.timestamp <= end_date
    )

    total_events = base_query.count()
    if total_events == 0:
        return None

    # Events by type
    events_by_type = session.query(
        Event.event_type,
        func.count(Event.id).label('count')
    ).filter(
        Event.user_id == user.id,
        Event.timestamp >= start_date,
        Event.timestamp <= end_date
    ).group_by(Event.event_type).all()

    # Top events
    top_events = session.query(
        Event.event_name,
        func.count(Event.id).label('count')
    ).filter(
        Event.user_id == user.id,
        Event.timestamp >= start_date,
        Event.timestamp <= end_date
    ).group_by(Event.event_name).order_by(
        func.count(Event.id).desc()
    ).limit(10).all()

    # Unique sessions
    unique_sessions = session.query(
        func.count(func.distinct(Event.session_id))
    ).filter(
        Event.user_id == user.id,
        Event.timestamp >= start_date,
        Event.timestamp <= end_date
    ).scalar() or 0

    return {
        'total_events': total_events,
        'unique_sessions': unique_sessions,
        'events_by_type': {t: c for t, c in events_by_type},
        'top_events': [{'name': n, 'count': c} for n, c in top_events],
    }


def format_report_content(report):
    """Format report data into readable content."""
    lines = [
        f"Total Events: {report['total_events']}",
        f"Unique Sessions: {report['unique_sessions']}",
        "",
        "Events by Type:",
    ]

    for event_type, count in report['events_by_type'].items():
        lines.append(f"  - {event_type}: {count}")

    lines.extend(["", "Top Events:"])
    for event in report['top_events'][:5]:
        lines.append(f"  - {event['name']}: {event['count']}")

    return "\n".join(lines)


@celery_app.task
def cleanup_old_events(days_to_keep: int = 90):
    """Clean up events older than specified days."""
    session = get_db_session()

    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

        # Count events to delete
        count = session.query(Event).filter(Event.timestamp < cutoff_date).count()

        if count > 0:
            # Delete in batches to avoid long transactions
            batch_size = 10000
            deleted = 0

            while deleted < count:
                subquery = session.query(Event.id).filter(
                    Event.timestamp < cutoff_date
                ).limit(batch_size).subquery()

                result = session.query(Event).filter(
                    Event.id.in_(subquery)
                ).delete(synchronize_session='fetch')

                session.commit()
                deleted += result

                if result == 0:
                    break

            logger.info(f"Cleaned up {deleted} old events")
            return {'success': True, 'deleted_count': deleted}
        else:
            logger.info("No old events to clean up")
            return {'success': True, 'deleted_count': 0}

    except Exception as e:
        logger.error(f"Error cleaning up old events: {str(e)}")
        session.rollback()
        return {'success': False, 'error': str(e)}

    finally:
        session.close()


@celery_app.task
def generate_event_aggregations(user_id: str, time_range: str = '7d'):
    """Generate aggregated statistics for a user."""
    session = get_db_session()

    try:
        # Parse time range
        if time_range.endswith('d'):
            days = int(time_range[:-1])
        elif time_range.endswith('w'):
            days = int(time_range[:-1]) * 7
        elif time_range.endswith('m'):
            days = int(time_range[:-1]) * 30
        else:
            days = 7

        start_date = datetime.utcnow() - timedelta(days=days)

        # Daily event counts
        daily_counts = session.query(
            func.date(Event.timestamp).label('date'),
            func.count(Event.id).label('count')
        ).filter(
            Event.user_id == user_id,
            Event.timestamp >= start_date
        ).group_by(func.date(Event.timestamp)).all()

        # Hourly distribution
        hourly_distribution = session.query(
            func.extract('hour', Event.timestamp).label('hour'),
            func.count(Event.id).label('count')
        ).filter(
            Event.user_id == user_id,
            Event.timestamp >= start_date
        ).group_by(func.extract('hour', Event.timestamp)).all()

        return {
            'success': True,
            'daily_counts': [{'date': str(d), 'count': c} for d, c in daily_counts],
            'hourly_distribution': [{'hour': int(h), 'count': c} for h, c in hourly_distribution],
        }

    except Exception as e:
        logger.error(f"Error generating aggregations: {str(e)}")
        return {'success': False, 'error': str(e)}

    finally:
        session.close()
