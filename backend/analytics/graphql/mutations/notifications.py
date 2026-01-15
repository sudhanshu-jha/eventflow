import graphene
from datetime import datetime

from ...models.notification import Notification


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


class MarkNotificationRead(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    success = graphene.Boolean()
    notification = graphene.Field(NotificationType)
    error = graphene.String()

    def mutate(self, info, id):
        user = info.context.get('user')
        if not user:
            return MarkNotificationRead(success=False, error='Authentication required')

        dbsession = info.context.get('dbsession')
        notification = dbsession.query(Notification).filter(
            Notification.id == id,
            Notification.user_id == user.id
        ).first()

        if not notification:
            return MarkNotificationRead(success=False, error='Notification not found')

        notification.is_read = True
        notification.read_at = datetime.utcnow()

        return MarkNotificationRead(
            success=True,
            notification=NotificationType(
                id=str(notification.id),
                notification_type=notification.notification_type,
                title=notification.title,
                content=notification.content,
                extra_data=notification.extra_data,
                status=notification.status,
                is_read=notification.is_read,
                created_at=notification.created_at,
                sent_at=notification.sent_at,
                read_at=notification.read_at,
            )
        )


class MarkAllNotificationsRead(graphene.Mutation):
    success = graphene.Boolean()
    count = graphene.Int()
    error = graphene.String()

    def mutate(self, info):
        user = info.context.get('user')
        if not user:
            return MarkAllNotificationsRead(success=False, error='Authentication required')

        dbsession = info.context.get('dbsession')
        now = datetime.utcnow()

        count = dbsession.query(Notification).filter(
            Notification.user_id == user.id,
            Notification.is_read == False
        ).update({
            'is_read': True,
            'read_at': now
        })

        return MarkAllNotificationsRead(success=True, count=count)


class CreateInAppNotification(graphene.Mutation):
    class Arguments:
        title = graphene.String(required=True)
        content = graphene.String(required=True)
        extra_data = graphene.JSONString()

    success = graphene.Boolean()
    notification = graphene.Field(NotificationType)
    error = graphene.String()

    def mutate(self, info, title, content, extra_data=None):
        user = info.context.get('user')
        if not user:
            return CreateInAppNotification(success=False, error='Authentication required')

        dbsession = info.context.get('dbsession')

        notification = Notification(
            user_id=user.id,
            notification_type='in_app',
            title=title,
            content=content,
            extra_data=extra_data or {},
            status='sent',
            sent_at=datetime.utcnow(),
        )
        dbsession.add(notification)
        dbsession.flush()

        return CreateInAppNotification(
            success=True,
            notification=NotificationType(
                id=str(notification.id),
                notification_type=notification.notification_type,
                title=notification.title,
                content=notification.content,
                extra_data=notification.extra_data,
                status=notification.status,
                is_read=notification.is_read,
                created_at=notification.created_at,
                sent_at=notification.sent_at,
            )
        )
