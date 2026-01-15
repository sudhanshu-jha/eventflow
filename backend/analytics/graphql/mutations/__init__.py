import graphene
from datetime import datetime
import secrets

from ...models.user import User
from ...models.event import Event
from ...models.notification import Notification
from ...models.webhook import Webhook
from ...services.auth import AuthService
from .auth import Register, Login, RefreshToken
from .events import TrackEvent
from .notifications import MarkNotificationRead, CreateInAppNotification


# Webhook Mutations
class CreateWebhook(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        url = graphene.String(required=True)
        events = graphene.List(graphene.String, required=True)

    success = graphene.Boolean()
    webhook = graphene.Field('analytics.graphql.queries.WebhookType')
    error = graphene.String()

    def mutate(self, info, name, url, events):
        from ..queries import WebhookType

        user = info.context.get('user')
        if not user:
            return CreateWebhook(success=False, error='Authentication required')

        dbsession = info.context.get('dbsession')

        webhook = Webhook(
            user_id=user.id,
            name=name,
            url=url,
            events=events,
            secret=secrets.token_hex(32),
        )
        dbsession.add(webhook)
        dbsession.flush()

        return CreateWebhook(
            success=True,
            webhook=WebhookType(
                id=str(webhook.id),
                name=webhook.name,
                url=webhook.url,
                secret=webhook.secret,
                events=webhook.events,
                is_active=webhook.is_active,
                created_at=webhook.created_at,
            )
        )


class UpdateWebhook(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        name = graphene.String()
        url = graphene.String()
        events = graphene.List(graphene.String)
        is_active = graphene.Boolean()

    success = graphene.Boolean()
    webhook = graphene.Field('analytics.graphql.queries.WebhookType')
    error = graphene.String()

    def mutate(self, info, id, name=None, url=None, events=None, is_active=None):
        from ..queries import WebhookType

        user = info.context.get('user')
        if not user:
            return UpdateWebhook(success=False, error='Authentication required')

        dbsession = info.context.get('dbsession')
        webhook = dbsession.query(Webhook).filter(
            Webhook.id == id,
            Webhook.user_id == user.id
        ).first()

        if not webhook:
            return UpdateWebhook(success=False, error='Webhook not found')

        if name is not None:
            webhook.name = name
        if url is not None:
            webhook.url = url
        if events is not None:
            webhook.events = events
        if is_active is not None:
            webhook.is_active = is_active

        webhook.updated_at = datetime.utcnow()

        return UpdateWebhook(
            success=True,
            webhook=WebhookType(
                id=str(webhook.id),
                name=webhook.name,
                url=webhook.url,
                secret=webhook.secret,
                events=webhook.events,
                is_active=webhook.is_active,
                last_triggered_at=webhook.last_triggered_at,
                success_count=webhook.success_count,
                failure_count=webhook.failure_count,
                created_at=webhook.created_at,
            )
        )


class DeleteWebhook(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    success = graphene.Boolean()
    error = graphene.String()

    def mutate(self, info, id):
        user = info.context.get('user')
        if not user:
            return DeleteWebhook(success=False, error='Authentication required')

        dbsession = info.context.get('dbsession')
        webhook = dbsession.query(Webhook).filter(
            Webhook.id == id,
            Webhook.user_id == user.id
        ).first()

        if not webhook:
            return DeleteWebhook(success=False, error='Webhook not found')

        dbsession.delete(webhook)
        return DeleteWebhook(success=True)


class RegenerateWebhookSecret(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    success = graphene.Boolean()
    new_secret = graphene.String()
    error = graphene.String()

    def mutate(self, info, id):
        user = info.context.get('user')
        if not user:
            return RegenerateWebhookSecret(success=False, error='Authentication required')

        dbsession = info.context.get('dbsession')
        webhook = dbsession.query(Webhook).filter(
            Webhook.id == id,
            Webhook.user_id == user.id
        ).first()

        if not webhook:
            return RegenerateWebhookSecret(success=False, error='Webhook not found')

        webhook.secret = secrets.token_hex(32)
        webhook.updated_at = datetime.utcnow()

        return RegenerateWebhookSecret(success=True, new_secret=webhook.secret)


class Mutation(graphene.ObjectType):
    # Auth mutations
    register = Register.Field()
    login = Login.Field()
    refresh_token = RefreshToken.Field()

    # Event mutations
    track_event = TrackEvent.Field()

    # Notification mutations
    mark_notification_read = MarkNotificationRead.Field()
    create_in_app_notification = CreateInAppNotification.Field()

    # Webhook mutations
    create_webhook = CreateWebhook.Field()
    update_webhook = UpdateWebhook.Field()
    delete_webhook = DeleteWebhook.Field()
    regenerate_webhook_secret = RegenerateWebhookSecret.Field()
