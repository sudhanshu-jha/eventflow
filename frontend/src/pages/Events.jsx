import { useState } from 'react'
import { useQuery, useMutation } from '@apollo/client'
import { GET_EVENTS } from '../graphql/queries'
import { TRACK_EVENT } from '../graphql/mutations'
import { format } from 'date-fns'

const EVENT_TYPES = ['page_view', 'click', 'custom', 'form_submit', 'scroll', 'error']

export default function Events() {
  const [filters, setFilters] = useState({
    eventType: '',
    eventName: '',
    limit: 50,
    offset: 0,
  })
  const [showTrackForm, setShowTrackForm] = useState(false)
  const [selectedEvent, setSelectedEvent] = useState(null)

  const { data, loading, refetch } = useQuery(GET_EVENTS, {
    variables: filters,
  })

  const events = data?.events?.events || []
  const totalCount = data?.events?.totalCount || 0
  const hasNextPage = data?.events?.hasNextPage || false

  const handleFilterChange = (key, value) => {
    setFilters((prev) => ({
      ...prev,
      [key]: value,
      offset: 0,
    }))
  }

  const handlePageChange = (direction) => {
    const newOffset = direction === 'next'
      ? filters.offset + filters.limit
      : Math.max(0, filters.offset - filters.limit)
    setFilters((prev) => ({ ...prev, offset: newOffset }))
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Events</h1>
        <button
          onClick={() => setShowTrackForm(true)}
          className="btn-primary"
        >
          Track Event
        </button>
      </div>

      {/* Filters */}
      <div className="card">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Event Type</label>
            <select
              value={filters.eventType}
              onChange={(e) => handleFilterChange('eventType', e.target.value)}
              className="input"
            >
              <option value="">All types</option>
              {EVENT_TYPES.map((type) => (
                <option key={type} value={type}>{type}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Event Name</label>
            <input
              type="text"
              value={filters.eventName}
              onChange={(e) => handleFilterChange('eventName', e.target.value)}
              placeholder="Search by name..."
              className="input"
            />
          </div>
          <div className="flex items-end">
            <button onClick={() => refetch()} className="btn-secondary">
              Refresh
            </button>
          </div>
        </div>
      </div>

      {/* Events Table */}
      <div className="card">
        {loading ? (
          <div className="flex justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>
        ) : events.length > 0 ? (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-600">Event Name</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-600">Type</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-600">Session</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-600">URL</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-600">Timestamp</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-600">Status</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-600">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {events.map((event) => (
                    <tr key={event.id} className="border-b hover:bg-gray-50">
                      <td className="py-3 px-4 font-medium">{event.eventName}</td>
                      <td className="py-3 px-4">
                        <span className={`inline-block px-2 py-1 rounded-full text-xs ${getTypeColor(event.eventType)}`}>
                          {event.eventType}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-sm text-gray-600 font-mono">
                        {event.sessionId?.slice(0, 8) || '-'}
                      </td>
                      <td className="py-3 px-4 text-sm text-gray-600 truncate max-w-xs">
                        {event.url || '-'}
                      </td>
                      <td className="py-3 px-4 text-sm text-gray-600">
                        {format(new Date(event.timestamp), 'MMM d, yyyy HH:mm:ss')}
                      </td>
                      <td className="py-3 px-4">
                        <span className={`inline-block px-2 py-1 rounded-full text-xs ${getStatusColor(event.isProcessed)}`}>
                          {event.isProcessed}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <button
                          onClick={() => setSelectedEvent(event)}
                          className="text-blue-600 hover:underline text-sm"
                        >
                          View
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="flex items-center justify-between mt-4 pt-4 border-t">
              <span className="text-sm text-gray-600">
                Showing {filters.offset + 1}-{Math.min(filters.offset + filters.limit, totalCount)} of {totalCount} events
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => handlePageChange('prev')}
                  disabled={filters.offset === 0}
                  className="btn-secondary disabled:opacity-50"
                >
                  Previous
                </button>
                <button
                  onClick={() => handlePageChange('next')}
                  disabled={!hasNextPage}
                  className="btn-secondary disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            </div>
          </>
        ) : (
          <p className="text-center text-gray-500 py-8">No events found</p>
        )}
      </div>

      {/* Track Event Modal */}
      {showTrackForm && (
        <TrackEventModal
          onClose={() => setShowTrackForm(false)}
          onSuccess={() => {
            setShowTrackForm(false)
            refetch()
          }}
        />
      )}

      {/* Event Detail Modal */}
      {selectedEvent && (
        <EventDetailModal
          event={selectedEvent}
          onClose={() => setSelectedEvent(null)}
        />
      )}
    </div>
  )
}

function TrackEventModal({ onClose, onSuccess }) {
  const [formData, setFormData] = useState({
    eventType: 'custom',
    eventName: '',
    properties: '{}',
    url: '',
  })
  const [error, setError] = useState('')

  const [trackEvent, { loading }] = useMutation(TRACK_EVENT)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')

    try {
      JSON.parse(formData.properties)
    } catch {
      setError('Invalid JSON in properties')
      return
    }

    const { data } = await trackEvent({
      variables: {
        eventType: formData.eventType,
        eventName: formData.eventName,
        properties: formData.properties,
        url: formData.url || undefined,
      },
    })

    if (data?.trackEvent?.success) {
      onSuccess()
    } else {
      setError(data?.trackEvent?.error || 'Failed to track event')
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-md">
        <h2 className="text-xl font-bold mb-4">Track Event</h2>

        {error && (
          <div className="mb-4 p-3 bg-red-100 text-red-700 rounded-lg text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Event Type</label>
            <select
              value={formData.eventType}
              onChange={(e) => setFormData((prev) => ({ ...prev, eventType: e.target.value }))}
              className="input"
            >
              {EVENT_TYPES.map((type) => (
                <option key={type} value={type}>{type}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Event Name</label>
            <input
              type="text"
              value={formData.eventName}
              onChange={(e) => setFormData((prev) => ({ ...prev, eventName: e.target.value }))}
              className="input"
              required
              placeholder="e.g., button_click"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Properties (JSON)</label>
            <textarea
              value={formData.properties}
              onChange={(e) => setFormData((prev) => ({ ...prev, properties: e.target.value }))}
              className="input font-mono text-sm"
              rows={4}
              placeholder='{"key": "value"}'
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">URL (optional)</label>
            <input
              type="text"
              value={formData.url}
              onChange={(e) => setFormData((prev) => ({ ...prev, url: e.target.value }))}
              className="input"
              placeholder="https://example.com/page"
            />
          </div>

          <div className="flex gap-3 pt-4">
            <button type="button" onClick={onClose} className="btn-secondary flex-1">
              Cancel
            </button>
            <button type="submit" disabled={loading} className="btn-primary flex-1">
              {loading ? 'Tracking...' : 'Track Event'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function EventDetailModal({ event, onClose }) {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-lg">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold">Event Details</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="space-y-4">
          <DetailRow label="ID" value={event.id} mono />
          <DetailRow label="Event Name" value={event.eventName} />
          <DetailRow label="Event Type" value={event.eventType} />
          <DetailRow label="Session ID" value={event.sessionId || '-'} mono />
          <DetailRow label="URL" value={event.url || '-'} />
          <DetailRow label="Referrer" value={event.referrer || '-'} />
          <DetailRow label="Status" value={event.isProcessed} />
          <DetailRow label="Timestamp" value={format(new Date(event.timestamp), 'PPpp')} />

          <div>
            <span className="text-sm font-medium text-gray-600">Properties</span>
            <pre className="mt-1 p-3 bg-gray-100 rounded-lg text-sm overflow-x-auto">
              {JSON.stringify(event.properties, null, 2) || '{}'}
            </pre>
          </div>
        </div>

        <button onClick={onClose} className="btn-secondary w-full mt-6">
          Close
        </button>
      </div>
    </div>
  )
}

function DetailRow({ label, value, mono }) {
  return (
    <div>
      <span className="text-sm font-medium text-gray-600">{label}</span>
      <p className={`text-gray-900 ${mono ? 'font-mono text-sm' : ''}`}>{value}</p>
    </div>
  )
}

function getTypeColor(type) {
  const colors = {
    page_view: 'bg-blue-100 text-blue-800',
    click: 'bg-green-100 text-green-800',
    custom: 'bg-purple-100 text-purple-800',
    form_submit: 'bg-yellow-100 text-yellow-800',
    error: 'bg-red-100 text-red-800',
  }
  return colors[type] || 'bg-gray-100 text-gray-800'
}

function getStatusColor(status) {
  const colors = {
    pending: 'bg-yellow-100 text-yellow-800',
    processing: 'bg-blue-100 text-blue-800',
    processed: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
  }
  return colors[status] || 'bg-gray-100 text-gray-800'
}
