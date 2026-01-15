import { gql } from '@apollo/client'

export const REGISTER = gql`
  mutation Register($email: String!, $password: String!, $name: String) {
    register(email: $email, password: $password, name: $name) {
      success
      user {
        id
        email
        name
        apiKey
        createdAt
      }
      tokens {
        accessToken
        refreshToken
        tokenType
        expiresIn
      }
      error
    }
  }
`

export const LOGIN = gql`
  mutation Login($email: String!, $password: String!) {
    login(email: $email, password: $password) {
      success
      user {
        id
        email
        name
        apiKey
        createdAt
      }
      tokens {
        accessToken
        refreshToken
        tokenType
        expiresIn
      }
      error
    }
  }
`

export const REFRESH_TOKEN = gql`
  mutation RefreshToken($refreshToken: String!) {
    refreshToken(refreshToken: $refreshToken) {
      success
      tokens {
        accessToken
        refreshToken
        tokenType
        expiresIn
      }
      error
    }
  }
`

export const TRACK_EVENT = gql`
  mutation TrackEvent(
    $eventType: String!
    $eventName: String!
    $properties: JSONString
    $sessionId: String
    $url: String
    $referrer: String
  ) {
    trackEvent(
      eventType: $eventType
      eventName: $eventName
      properties: $properties
      sessionId: $sessionId
      url: $url
      referrer: $referrer
    ) {
      success
      event {
        id
        eventType
        eventName
        properties
        timestamp
      }
      error
    }
  }
`

export const MARK_NOTIFICATION_READ = gql`
  mutation MarkNotificationRead($id: ID!) {
    markNotificationRead(id: $id) {
      success
      notification {
        id
        isRead
        readAt
      }
      error
    }
  }
`

export const CREATE_WEBHOOK = gql`
  mutation CreateWebhook($name: String!, $url: String!, $events: [String]!) {
    createWebhook(name: $name, url: $url, events: $events) {
      success
      webhook {
        id
        name
        url
        secret
        events
        isActive
        createdAt
      }
      error
    }
  }
`

export const UPDATE_WEBHOOK = gql`
  mutation UpdateWebhook(
    $id: ID!
    $name: String
    $url: String
    $events: [String]
    $isActive: Boolean
  ) {
    updateWebhook(id: $id, name: $name, url: $url, events: $events, isActive: $isActive) {
      success
      webhook {
        id
        name
        url
        events
        isActive
      }
      error
    }
  }
`

export const DELETE_WEBHOOK = gql`
  mutation DeleteWebhook($id: ID!) {
    deleteWebhook(id: $id) {
      success
      error
    }
  }
`

export const REGENERATE_WEBHOOK_SECRET = gql`
  mutation RegenerateWebhookSecret($id: ID!) {
    regenerateWebhookSecret(id: $id) {
      success
      newSecret
      error
    }
  }
`
