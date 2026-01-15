import { useState } from 'react'
import { useQuery, useMutation } from '@apollo/client'
import { GET_WEBHOOKS, GET_ME } from '../graphql/queries'
import { CREATE_WEBHOOK, UPDATE_WEBHOOK, DELETE_WEBHOOK, REGENERATE_WEBHOOK_SECRET } from '../graphql/mutations'
import { format } from 'date-fns'

const EVENT_TYPES = ['page_view', 'click', 'custom', 'form_submit', 'scroll', 'error', '*']

export default function Settings() {
  const [activeTab, setActiveTab] = useState('api')

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Settings</h1>

      {/* Tabs */}
      <div className="border-b">
        <nav className="flex gap-8">
          <TabButton active={activeTab === 'api'} onClick={() => setActiveTab('api')}>
            API Key
          </TabButton>
          <TabButton active={activeTab === 'webhooks'} onClick={() => setActiveTab('webhooks')}>
            Webhooks
          </TabButton>
        </nav>
      </div>

      {activeTab === 'api' && <ApiKeySection />}
      {activeTab === 'webhooks' && <WebhooksSection />}
    </div>
  )
}

function TabButton({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className={`pb-4 text-sm font-medium border-b-2 transition-colors ${
        active
          ? 'border-blue-600 text-blue-600'
          : 'border-transparent text-gray-500 hover:text-gray-700'
      }`}
    >
      {children}
    </button>
  )
}

function ApiKeySection() {
  const { data, loading } = useQuery(GET_ME)
  const [copied, setCopied] = useState(false)

  const user = data?.me
  const apiKey = user?.apiKey

  const copyToClipboard = async () => {
    if (apiKey) {
      await navigator.clipboard.writeText(apiKey)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  if (loading) {
    return <div className="card"><p className="text-gray-500">Loading...</p></div>
  }

  return (
    <div className="card">
      <h2 className="text-lg font-semibold mb-4">API Key</h2>
      <p className="text-sm text-gray-600 mb-4">
        Use this API key to track events from your applications.
      </p>

      <div className="flex items-center gap-4">
        <code className="flex-1 p-3 bg-gray-100 rounded-lg font-mono text-sm break-all">
          {apiKey}
        </code>
        <button onClick={copyToClipboard} className="btn-secondary whitespace-nowrap">
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>

      <div className="mt-6 p-4 bg-blue-50 rounded-lg">
        <h3 className="font-medium text-blue-900 mb-2">Usage Example</h3>
        <pre className="text-sm text-blue-800 overflow-x-auto">
{`fetch('/api/track', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': '${apiKey?.slice(0, 16)}...'
  },
  body: JSON.stringify({
    event_type: 'page_view',
    event_name: 'home_page',
    properties: { source: 'organic' }
  })
})`}
        </pre>
      </div>
    </div>
  )
}

function WebhooksSection() {
  const { data, loading, refetch } = useQuery(GET_WEBHOOKS)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [editingWebhook, setEditingWebhook] = useState(null)

  const webhooks = data?.webhooks || []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-600">
          Webhooks allow you to receive real-time notifications when events are tracked.
        </p>
        <button onClick={() => setShowCreateForm(true)} className="btn-primary">
          Add Webhook
        </button>
      </div>

      {loading ? (
        <div className="card"><p className="text-gray-500">Loading...</p></div>
      ) : webhooks.length > 0 ? (
        <div className="space-y-4">
          {webhooks.map((webhook) => (
            <WebhookCard
              key={webhook.id}
              webhook={webhook}
              onEdit={() => setEditingWebhook(webhook)}
              onRefetch={refetch}
            />
          ))}
        </div>
      ) : (
        <div className="card text-center py-8">
          <p className="text-gray-500">No webhooks configured yet.</p>
        </div>
      )}

      {showCreateForm && (
        <WebhookFormModal
          onClose={() => setShowCreateForm(false)}
          onSuccess={() => {
            setShowCreateForm(false)
            refetch()
          }}
        />
      )}

      {editingWebhook && (
        <WebhookFormModal
          webhook={editingWebhook}
          onClose={() => setEditingWebhook(null)}
          onSuccess={() => {
            setEditingWebhook(null)
            refetch()
          }}
        />
      )}
    </div>
  )
}

function WebhookCard({ webhook, onEdit, onRefetch }) {
  const [showSecret, setShowSecret] = useState(false)
  const [deleteWebhook] = useMutation(DELETE_WEBHOOK)
  const [regenerateSecret] = useMutation(REGENERATE_WEBHOOK_SECRET)

  const handleDelete = async () => {
    if (confirm('Are you sure you want to delete this webhook?')) {
      await deleteWebhook({ variables: { id: webhook.id } })
      onRefetch()
    }
  }

  const handleRegenerateSecret = async () => {
    if (confirm('Are you sure? This will invalidate the current secret.')) {
      await regenerateSecret({ variables: { id: webhook.id } })
      onRefetch()
    }
  }

  return (
    <div className="card">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="font-semibold">{webhook.name}</h3>
          <p className="text-sm text-gray-600 break-all">{webhook.url}</p>
        </div>
        <span className={`px-2 py-1 rounded-full text-xs ${webhook.isActive ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>
          {webhook.isActive ? 'Active' : 'Inactive'}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-4 text-sm">
        <div>
          <span className="text-gray-500">Events:</span>
          <div className="flex flex-wrap gap-1 mt-1">
            {webhook.events?.map((event) => (
              <span key={event} className="px-2 py-0.5 bg-gray-100 rounded text-xs">
                {event}
              </span>
            ))}
          </div>
        </div>
        <div>
          <span className="text-gray-500">Stats:</span>
          <p className="text-green-600">{webhook.successCount} successful</p>
          <p className="text-red-600">{webhook.failureCount} failed</p>
        </div>
      </div>

      <div className="mb-4">
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-500">Secret:</span>
          <button
            onClick={() => setShowSecret(!showSecret)}
            className="text-sm text-blue-600 hover:underline"
          >
            {showSecret ? 'Hide' : 'Show'}
          </button>
        </div>
        {showSecret && (
          <code className="block mt-1 p-2 bg-gray-100 rounded text-xs font-mono break-all">
            {webhook.secret}
          </code>
        )}
      </div>

      <div className="flex gap-2 pt-4 border-t">
        <button onClick={onEdit} className="btn-secondary text-sm">
          Edit
        </button>
        <button onClick={handleRegenerateSecret} className="btn-secondary text-sm">
          Regenerate Secret
        </button>
        <button onClick={handleDelete} className="text-red-600 hover:underline text-sm ml-auto">
          Delete
        </button>
      </div>
    </div>
  )
}

function WebhookFormModal({ webhook, onClose, onSuccess }) {
  const [formData, setFormData] = useState({
    name: webhook?.name || '',
    url: webhook?.url || '',
    events: webhook?.events || ['*'],
    isActive: webhook?.isActive ?? true,
  })
  const [error, setError] = useState('')

  const [createWebhook, { loading: createLoading }] = useMutation(CREATE_WEBHOOK)
  const [updateWebhook, { loading: updateLoading }] = useMutation(UPDATE_WEBHOOK)

  const loading = createLoading || updateLoading
  const isEditing = !!webhook

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')

    try {
      if (isEditing) {
        const { data } = await updateWebhook({
          variables: {
            id: webhook.id,
            name: formData.name,
            url: formData.url,
            events: formData.events,
            isActive: formData.isActive,
          },
        })
        if (!data?.updateWebhook?.success) {
          throw new Error(data?.updateWebhook?.error || 'Update failed')
        }
      } else {
        const { data } = await createWebhook({
          variables: {
            name: formData.name,
            url: formData.url,
            events: formData.events,
          },
        })
        if (!data?.createWebhook?.success) {
          throw new Error(data?.createWebhook?.error || 'Creation failed')
        }
      }
      onSuccess()
    } catch (err) {
      setError(err.message)
    }
  }

  const toggleEvent = (event) => {
    setFormData((prev) => {
      const events = prev.events.includes(event)
        ? prev.events.filter((e) => e !== event)
        : [...prev.events, event]
      return { ...prev, events }
    })
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-md">
        <h2 className="text-xl font-bold mb-4">
          {isEditing ? 'Edit Webhook' : 'Create Webhook'}
        </h2>

        {error && (
          <div className="mb-4 p-3 bg-red-100 text-red-700 rounded-lg text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData((prev) => ({ ...prev, name: e.target.value }))}
              className="input"
              required
              placeholder="My Webhook"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">URL</label>
            <input
              type="url"
              value={formData.url}
              onChange={(e) => setFormData((prev) => ({ ...prev, url: e.target.value }))}
              className="input"
              required
              placeholder="https://example.com/webhook"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Events</label>
            <div className="flex flex-wrap gap-2">
              {EVENT_TYPES.map((event) => (
                <button
                  key={event}
                  type="button"
                  onClick={() => toggleEvent(event)}
                  className={`px-3 py-1 rounded-full text-sm transition-colors ${
                    formData.events.includes(event)
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {event === '*' ? 'All Events' : event}
                </button>
              ))}
            </div>
          </div>

          {isEditing && (
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="isActive"
                checked={formData.isActive}
                onChange={(e) => setFormData((prev) => ({ ...prev, isActive: e.target.checked }))}
                className="rounded"
              />
              <label htmlFor="isActive" className="text-sm text-gray-700">Active</label>
            </div>
          )}

          <div className="flex gap-3 pt-4">
            <button type="button" onClick={onClose} className="btn-secondary flex-1">
              Cancel
            </button>
            <button type="submit" disabled={loading} className="btn-primary flex-1">
              {loading ? 'Saving...' : isEditing ? 'Update' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
