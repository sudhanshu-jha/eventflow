from datetime import datetime
import logging

from .celery_app import celery_app, get_db_session
from ..models.event import Event
from ..models.webhook import Webhook
from ..services.webhook import WebhookService

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def process_event(self, event_id: str):
    """Process a tracked event asynchronously."""
    session = get_db_session()

    try:
        event = session.query(Event).filter(Event.id == event_id).first()
        if not event:
            logger.error(f"Event {event_id} not found")
            return {'success': False, 'error': 'Event not found'}

        # Mark as processing
        event.is_processed = 'processing'
        session.commit()

        # Enrich event data (example: add derived fields)
        if event.properties:
            enriched = dict(event.properties)

            # Add processing metadata
            enriched['_processed_at'] = datetime.utcnow().isoformat()
            enriched['_version'] = '1.0'

            event.properties = enriched

        # Trigger webhooks
        trigger_webhooks.delay(event_id)

        # Mark as processed
        event.is_processed = 'processed'
        event.processed_at = datetime.utcnow()
        session.commit()

        logger.info(f"Successfully processed event {event_id}")
        return {'success': True, 'event_id': event_id}

    except Exception as e:
        logger.error(f"Error processing event {event_id}: {str(e)}")
        session.rollback()

        # Mark as failed
        try:
            event = session.query(Event).filter(Event.id == event_id).first()
            if event:
                event.is_processed = 'failed'
                session.commit()
        except Exception:
            pass

        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=2 ** self.request.retries)

    finally:
        session.close()


@celery_app.task(bind=True, max_retries=3)
def trigger_webhooks(self, event_id: str):
    """Trigger webhooks for an event."""
    session = get_db_session()

    try:
        event = session.query(Event).filter(Event.id == event_id).first()
        if not event:
            return {'success': False, 'error': 'Event not found'}

        # Get user's active webhooks
        webhooks = session.query(Webhook).filter(
            Webhook.user_id == event.user_id,
            Webhook.is_active == True
        ).all()

        webhook_service = WebhookService()
        triggered_count = 0

        for webhook in webhooks:
            if webhook.should_trigger(event.event_type):
                # Queue individual webhook send
                send_single_webhook.delay(
                    str(webhook.id),
                    event_id
                )
                triggered_count += 1

        logger.info(f"Triggered {triggered_count} webhooks for event {event_id}")
        return {'success': True, 'triggered_count': triggered_count}

    except Exception as e:
        logger.error(f"Error triggering webhooks for event {event_id}: {str(e)}")
        raise self.retry(exc=e, countdown=2 ** self.request.retries)

    finally:
        session.close()


@celery_app.task(bind=True, max_retries=5)
def send_single_webhook(self, webhook_id: str, event_id: str):
    """Send a single webhook notification."""
    session = get_db_session()

    try:
        webhook = session.query(Webhook).filter(Webhook.id == webhook_id).first()
        event = session.query(Event).filter(Event.id == event_id).first()

        if not webhook or not event:
            return {'success': False, 'error': 'Webhook or event not found'}

        webhook_service = WebhookService()

        # Format payload
        from ..models.user import User
        user = session.query(User).filter(User.id == event.user_id).first()
        payload = webhook_service.format_event_payload(event, user)

        # Send webhook
        result = webhook_service.send_webhook(webhook.url, webhook.secret, payload)

        # Update webhook statistics
        if result['success']:
            webhook.success_count = str(int(webhook.success_count or '0') + 1)
        else:
            webhook.failure_count = str(int(webhook.failure_count or '0') + 1)

        webhook.last_triggered_at = datetime.utcnow()
        session.commit()

        if not result['success']:
            raise Exception(result.get('error', 'Webhook failed'))

        return result

    except Exception as e:
        logger.error(f"Error sending webhook {webhook_id}: {str(e)}")
        raise self.retry(exc=e, countdown=5 * (2 ** self.request.retries))

    finally:
        session.close()


@celery_app.task
def process_batch_events(event_ids: list):
    """Process multiple events in batch."""
    results = []
    for event_id in event_ids:
        try:
            result = process_event.delay(event_id)
            results.append({'event_id': event_id, 'task_id': result.id})
        except Exception as e:
            results.append({'event_id': event_id, 'error': str(e)})

    return results
