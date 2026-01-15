import graphene
from graphene import relay
from datetime import datetime, timedelta
from sqlalchemy import func, and_

from ...models.user import User
from ...models.event import Event
from ...models.notification import Notification
from ...models.webhook import Webhook


# GraphQL Types
class UserType(graphene.ObjectType):
    id = graphene.ID()
    email = graphene.String()
    name = graphene.String()
    api_key = graphene.String()
    created_at = graphene.DateTime()
    is_active = graphene.Boolean()


class EventType(graphene.ObjectType):
    id = graphene.ID()
    event_type = graphene.String()
    event_name = graphene.String()
    properties = graphene.JSONString()
    session_id = graphene.String()
    url = graphene.String()
    referrer = graphene.String()
    timestamp = graphene.DateTime()
    is_processed = graphene.String()


class NotificationType(graphene.ObjectType):
    id = graphene.ID()
    notification_type = graphene.String()
    title = graphene.String()
    content = graphene.String()
    extra_data = graphene.JSONString()
    status = graphene.String()
    is_read = graphene.Boolean()
    created_at = graphene.DateTime()
    sent_at = graphene.DateTime()
    read_at = graphene.DateTime()


class WebhookType(graphene.ObjectType):
    id = graphene.ID()
    name = graphene.String()
    url = graphene.String()
    secret = graphene.String()
    events = graphene.List(graphene.String)
    is_active = graphene.Boolean()
    last_triggered_at = graphene.DateTime()
    success_count = graphene.String()
    failure_count = graphene.String()
    created_at = graphene.DateTime()


class EventStatsType(graphene.ObjectType):
    total_events = graphene.Int()
    events_today = graphene.Int()
    events_this_week = graphene.Int()
    unique_sessions = graphene.Int()
    top_events = graphene.List(graphene.JSONString)
    events_by_type = graphene.List(graphene.JSONString)


class EventsConnection(graphene.ObjectType):
    events = graphene.List(EventType)
    total_count = graphene.Int()
    has_next_page = graphene.Boolean()


class Query(graphene.ObjectType):
    # User queries
    me = graphene.Field(UserType)

    # Event queries
    events = graphene.Field(
        EventsConnection,
        event_type=graphene.String(),
        event_name=graphene.String(),
        start_date=graphene.DateTime(),
        end_date=graphene.DateTime(),
        limit=graphene.Int(default_value=50),
        offset=graphene.Int(default_value=0),
    )
    event = graphene.Field(EventType, id=graphene.ID(required=True))
    event_stats = graphene.Field(EventStatsType)

    # Notification queries
    notifications = graphene.List(
        NotificationType,
        status=graphene.String(),
        notification_type=graphene.String(),
        unread_only=graphene.Boolean(default_value=False),
        limit=graphene.Int(default_value=50),
    )
    unread_notification_count = graphene.Int()

    # Webhook queries
    webhooks = graphene.List(WebhookType)
    webhook = graphene.Field(WebhookType, id=graphene.ID(required=True))

    def resolve_me(self, info):
        user = info.context.get('user')
        if not user:
            return None
        return UserType(
            id=str(user.id),
            email=user.email,
            name=user.name,
            api_key=user.api_key,
            created_at=user.created_at,
            is_active=user.is_active,
        )

    def resolve_events(self, info, event_type=None, event_name=None,
                       start_date=None, end_date=None, limit=50, offset=0):
        user = info.context.get('user')
        if not user:
            return None

        dbsession = info.context.get('dbsession')
        query = dbsession.query(Event).filter(Event.user_id == user.id)

        if event_type:
            query = query.filter(Event.event_type == event_type)
        if event_name:
            query = query.filter(Event.event_name.ilike(f'%{event_name}%'))
        if start_date:
            query = query.filter(Event.timestamp >= start_date)
        if end_date:
            query = query.filter(Event.timestamp <= end_date)

        total_count = query.count()
        events = query.order_by(Event.timestamp.desc()).offset(offset).limit(limit).all()

        return EventsConnection(
            events=[EventType(
                id=str(e.id),
                event_type=e.event_type,
                event_name=e.event_name,
                properties=e.properties,
                session_id=e.session_id,
                url=e.url,
                referrer=e.referrer,
                timestamp=e.timestamp,
                is_processed=e.is_processed,
            ) for e in events],
            total_count=total_count,
            has_next_page=(offset + limit) < total_count,
        )

    def resolve_event(self, info, id):
        user = info.context.get('user')
        if not user:
            return None

        dbsession = info.context.get('dbsession')
        event = dbsession.query(Event).filter(
            and_(Event.id == id, Event.user_id == user.id)
        ).first()

        if not event:
            return None

        return EventType(
            id=str(event.id),
            event_type=event.event_type,
            event_name=event.event_name,
            properties=event.properties,
            session_id=event.session_id,
            url=event.url,
            referrer=event.referrer,
            timestamp=event.timestamp,
            is_processed=event.is_processed,
        )

    def resolve_event_stats(self, info):
        user = info.context.get('user')
        if not user:
            return None

        dbsession = info.context.get('dbsession')
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=7)

        base_query = dbsession.query(Event).filter(Event.user_id == user.id)

        total_events = base_query.count()
        events_today = base_query.filter(Event.timestamp >= today_start).count()
        events_this_week = base_query.filter(Event.timestamp >= week_start).count()

        unique_sessions = dbsession.query(func.count(func.distinct(Event.session_id))).filter(
            Event.user_id == user.id
        ).scalar() or 0

        # Top events
        top_events_result = dbsession.query(
            Event.event_name,
            func.count(Event.id).label('count')
        ).filter(Event.user_id == user.id).group_by(
            Event.event_name
        ).order_by(func.count(Event.id).desc()).limit(10).all()

        top_events = [{'name': name, 'count': count} for name, count in top_events_result]

        # Events by type
        events_by_type_result = dbsession.query(
            Event.event_type,
            func.count(Event.id).label('count')
        ).filter(Event.user_id == user.id).group_by(Event.event_type).all()

        events_by_type = [{'type': etype, 'count': count} for etype, count in events_by_type_result]

        return EventStatsType(
            total_events=total_events,
            events_today=events_today,
            events_this_week=events_this_week,
            unique_sessions=unique_sessions,
            top_events=top_events,
            events_by_type=events_by_type,
        )

    def resolve_notifications(self, info, status=None, notification_type=None,
                              unread_only=False, limit=50):
        user = info.context.get('user')
        if not user:
            return []

        dbsession = info.context.get('dbsession')
        query = dbsession.query(Notification).filter(Notification.user_id == user.id)

        if status:
            query = query.filter(Notification.status == status)
        if notification_type:
            query = query.filter(Notification.notification_type == notification_type)
        if unread_only:
            query = query.filter(Notification.is_read == False)

        notifications = query.order_by(Notification.created_at.desc()).limit(limit).all()

        return [NotificationType(
            id=str(n.id),
            notification_type=n.notification_type,
            title=n.title,
            content=n.content,
            extra_data=n.extra_data,
            status=n.status,
            is_read=n.is_read,
            created_at=n.created_at,
            sent_at=n.sent_at,
            read_at=n.read_at,
        ) for n in notifications]

    def resolve_unread_notification_count(self, info):
        user = info.context.get('user')
        if not user:
            return 0

        dbsession = info.context.get('dbsession')
        return dbsession.query(Notification).filter(
            and_(Notification.user_id == user.id, Notification.is_read == False)
        ).count()

    def resolve_webhooks(self, info):
        user = info.context.get('user')
        if not user:
            return []

        dbsession = info.context.get('dbsession')
        webhooks = dbsession.query(Webhook).filter(Webhook.user_id == user.id).all()

        return [WebhookType(
            id=str(w.id),
            name=w.name,
            url=w.url,
            secret=w.secret,
            events=w.events,
            is_active=w.is_active,
            last_triggered_at=w.last_triggered_at,
            success_count=w.success_count,
            failure_count=w.failure_count,
            created_at=w.created_at,
        ) for w in webhooks]

    def resolve_webhook(self, info, id):
        user = info.context.get('user')
        if not user:
            return None

        dbsession = info.context.get('dbsession')
        webhook = dbsession.query(Webhook).filter(
            and_(Webhook.id == id, Webhook.user_id == user.id)
        ).first()

        if not webhook:
            return None

        return WebhookType(
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
