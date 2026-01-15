import hmac
import hashlib
import json
import logging
from datetime import datetime

import requests

logger = logging.getLogger(__name__)


class WebhookService:
    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    def generate_signature(self, payload: str, secret: str) -> str:
        """Generate HMAC-SHA256 signature for webhook payload."""
        return hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    def send_webhook(self, url: str, secret: str, event_data: dict) -> dict:
        """Send a webhook notification to the specified URL."""
        payload = json.dumps(event_data, default=str)
        signature = self.generate_signature(payload, secret)

        headers = {
            'Content-Type': 'application/json',
            'X-Webhook-Signature': signature,
            'X-Webhook-Timestamp': datetime.utcnow().isoformat(),
        }

        try:
            response = requests.post(
                url,
                data=payload,
                headers=headers,
                timeout=self.timeout
            )

            result = {
                'success': response.status_code < 400,
                'status_code': response.status_code,
                'response_body': response.text[:1000] if response.text else None,
            }

            if result['success']:
                logger.info(f"Webhook sent successfully to {url}")
            else:
                logger.warning(f"Webhook to {url} returned status {response.status_code}")

            return result

        except requests.Timeout:
            logger.error(f"Webhook to {url} timed out")
            return {
                'success': False,
                'error': 'Request timed out',
            }
        except requests.RequestException as e:
            logger.error(f"Webhook to {url} failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
            }

    def verify_signature(self, payload: str, signature: str, secret: str) -> bool:
        """Verify a webhook signature (for receiving webhooks)."""
        expected = self.generate_signature(payload, secret)
        return hmac.compare_digest(expected, signature)

    def format_event_payload(self, event, user) -> dict:
        """Format an event into a webhook payload."""
        return {
            'event': {
                'id': str(event.id),
                'type': event.event_type,
                'name': event.event_name,
                'properties': event.properties,
                'timestamp': event.timestamp.isoformat(),
                'session_id': event.session_id,
                'url': event.url,
            },
            'user': {
                'id': str(user.id),
                'email': user.email,
            },
            'sent_at': datetime.utcnow().isoformat(),
        }
