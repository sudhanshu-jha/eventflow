import graphene
from datetime import datetime

from ...models.event import Event


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


class TrackEvent(graphene.Mutation):
    class Arguments:
        event_type = graphene.String(required=True)
        event_name = graphene.String(required=True)
        properties = graphene.JSONString()
        session_id = graphene.String()
        url = graphene.String()
        referrer = graphene.String()
        timestamp = graphene.DateTime()

    success = graphene.Boolean()
    event = graphene.Field(EventType)
    error = graphene.String()

    def mutate(self, info, event_type, event_name, properties=None,
               session_id=None, url=None, referrer=None, timestamp=None):
        user = info.context.get('user')
        if not user:
            return TrackEvent(success=False, error='Authentication required')

        # Validate event_type
        valid_types = ['page_view', 'click', 'custom', 'form_submit', 'scroll', 'error']
        if event_type not in valid_types:
            return TrackEvent(
                success=False,
                error=f'Invalid event_type. Must be one of: {", ".join(valid_types)}'
            )

        dbsession = info.context.get('dbsession')

        event = Event(
            user_id=user.id,
            event_type=event_type,
            event_name=event_name,
            properties=properties or {},
            session_id=session_id,
            url=url,
            referrer=referrer,
            timestamp=timestamp or datetime.utcnow(),
            is_processed='pending',
        )
        dbsession.add(event)
        dbsession.flush()

        # Trigger async processing
        try:
            from ...tasks.event_processing import process_event
            process_event.delay(str(event.id))
        except Exception:
            pass  # Celery may not be running in dev

        return TrackEvent(
            success=True,
            event=EventType(
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
        )


class TrackBatchEvents(graphene.Mutation):
    class Arguments:
        events = graphene.List(graphene.JSONString, required=True)

    success = graphene.Boolean()
    tracked_count = graphene.Int()
    error = graphene.String()

    def mutate(self, info, events):
        user = info.context.get('user')
        if not user:
            return TrackBatchEvents(success=False, error='Authentication required')

        if len(events) > 100:
            return TrackBatchEvents(
                success=False,
                error='Maximum 100 events per batch'
            )

        dbsession = info.context.get('dbsession')
        tracked_count = 0

        for event_data in events:
            if not isinstance(event_data, dict):
                continue

            event = Event(
                user_id=user.id,
                event_type=event_data.get('event_type', 'custom'),
                event_name=event_data.get('event_name', 'unknown'),
                properties=event_data.get('properties', {}),
                session_id=event_data.get('session_id'),
                url=event_data.get('url'),
                referrer=event_data.get('referrer'),
                timestamp=datetime.utcnow(),
                is_processed='pending',
            )
            dbsession.add(event)
            tracked_count += 1

        return TrackBatchEvents(success=True, tracked_count=tracked_count)
