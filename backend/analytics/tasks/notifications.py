from datetime import datetime
import logging

from .celery_app import celery_app, get_db_session
from ..models.notification import Notification
from ..models.user import User
from ..services.email import EmailService
from ..services.webhook import WebhookService

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def send_email_notification(self, notification_id: str):
    """Send an email notification."""
    session = get_db_session()

    try:
        notification = session.query(Notification).filter(
            Notification.id == notification_id
        ).first()

        if not notification:
            return {'success': False, 'error': 'Notification not found'}

        if notification.notification_type != 'email':
            return {'success': False, 'error': 'Not an email notification'}

        user = session.query(User).filter(User.id == notification.user_id).first()
        if not user:
            return {'success': False, 'error': 'User not found'}

        email_service = EmailService()

        try:
            email_service.send_notification_email(
                to_email=user.email,
                title=notification.title,
                content=notification.content
            )

            notification.status = 'sent'
            notification.sent_at = datetime.utcnow()
            session.commit()

            logger.info(f"Email notification {notification_id} sent successfully")
            return {'success': True, 'notification_id': str(notification_id)}

        except Exception as e:
            notification.status = 'failed'
            notification.error_message = str(e)
            notification.retry_count = str(int(notification.retry_count or '0') + 1)
            session.commit()
            raise

    except Exception as e:
        logger.error(f"Error sending email notification {notification_id}: {str(e)}")
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))

    finally:
        session.close()


@celery_app.task(bind=True, max_retries=5)
def send_webhook_notification(self, notification_id: str, webhook_url: str, secret: str):
    """Send a webhook notification."""
    session = get_db_session()

    try:
        notification = session.query(Notification).filter(
            Notification.id == notification_id
        ).first()

        if not notification:
            return {'success': False, 'error': 'Notification not found'}

        webhook_service = WebhookService()

        payload = {
            'type': 'notification',
            'notification': {
                'id': str(notification.id),
                'type': notification.notification_type,
                'title': notification.title,
                'content': notification.content,
                'extra_data': notification.extra_data,
                'created_at': notification.created_at.isoformat(),
            },
            'sent_at': datetime.utcnow().isoformat(),
        }

        result = webhook_service.send_webhook(webhook_url, secret, payload)

        if result['success']:
            notification.status = 'sent'
            notification.sent_at = datetime.utcnow()
        else:
            notification.retry_count = str(int(notification.retry_count or '0') + 1)
            if int(notification.retry_count) >= 5:
                notification.status = 'failed'
                notification.error_message = result.get('error', 'Max retries exceeded')

        session.commit()

        if not result['success']:
            raise Exception(result.get('error', 'Webhook failed'))

        return result

    except Exception as e:
        logger.error(f"Error sending webhook notification {notification_id}: {str(e)}")
        raise self.retry(exc=e, countdown=30 * (2 ** self.request.retries))

    finally:
        session.close()


@celery_app.task
def create_and_send_notification(user_id: str, notification_type: str,
                                  title: str, content: str, metadata: dict = None):
    """Create a notification and send it."""
    session = get_db_session()

    try:
        notification = Notification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            content=content,
            metadata=metadata or {},
            status='pending',
        )
        session.add(notification)
        session.commit()

        notification_id = str(notification.id)

        # Dispatch to appropriate handler
        if notification_type == 'email':
            send_email_notification.delay(notification_id)
        elif notification_type == 'in_app':
            # In-app notifications are immediately "sent"
            notification.status = 'sent'
            notification.sent_at = datetime.utcnow()
            session.commit()

        return {'success': True, 'notification_id': notification_id}

    except Exception as e:
        logger.error(f"Error creating notification: {str(e)}")
        session.rollback()
        return {'success': False, 'error': str(e)}

    finally:
        session.close()


@celery_app.task
def send_bulk_notifications(user_ids: list, notification_type: str,
                            title: str, content: str, metadata: dict = None):
    """Send notifications to multiple users."""
    results = []
    for user_id in user_ids:
        result = create_and_send_notification.delay(
            user_id, notification_type, title, content, metadata
        )
        results.append({'user_id': user_id, 'task_id': result.id})

    return results
