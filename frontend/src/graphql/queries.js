import { gql } from '@apollo/client'

export const GET_ME = gql`
  query GetMe {
    me {
      id
      email
      name
      apiKey
      createdAt
      isActive
    }
  }
`

export const GET_EVENTS = gql`
  query GetEvents(
    $eventType: String
    $eventName: String
    $startDate: DateTime
    $endDate: DateTime
    $limit: Int
    $offset: Int
  ) {
    events(
      eventType: $eventType
      eventName: $eventName
      startDate: $startDate
      endDate: $endDate
      limit: $limit
      offset: $offset
    ) {
      events {
        id
        eventType
        eventName
        properties
        sessionId
        url
        referrer
        timestamp
        isProcessed
      }
      totalCount
      hasNextPage
    }
  }
`

export const GET_EVENT = gql`
  query GetEvent($id: ID!) {
    event(id: $id) {
      id
      eventType
      eventName
      properties
      sessionId
      url
      referrer
      timestamp
      isProcessed
    }
  }
`

export const GET_EVENT_STATS = gql`
  query GetEventStats {
    eventStats {
      totalEvents
      eventsToday
      eventsThisWeek
      uniqueSessions
      topEvents {
        name
        count
      }
      eventsByType {
        type
        count
      }
    }
  }
`

export const GET_NOTIFICATIONS = gql`
  query GetNotifications(
    $status: String
    $notificationType: String
    $unreadOnly: Boolean
    $limit: Int
  ) {
    notifications(
      status: $status
      notificationType: $notificationType
      unreadOnly: $unreadOnly
      limit: $limit
    ) {
      id
      notificationType
      title
      content
      extraData
      status
      isRead
      createdAt
      sentAt
      readAt
    }
    unreadNotificationCount
  }
`

export const GET_WEBHOOKS = gql`
  query GetWebhooks {
    webhooks {
      id
      name
      url
      secret
      events
      isActive
      lastTriggeredAt
      successCount
      failureCount
      createdAt
    }
  }
`

export const GET_WEBHOOK = gql`
  query GetWebhook($id: ID!) {
    webhook(id: $id) {
      id
      name
      url
      secret
      events
      isActive
      lastTriggeredAt
      successCount
      failureCount
      createdAt
    }
  }
`
