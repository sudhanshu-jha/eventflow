import { useQuery } from '@apollo/client'
import { GET_EVENT_STATS, GET_EVENTS } from '../graphql/queries'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import { format } from 'date-fns'

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899']

export default function Dashboard() {
  const { data: statsData, loading: statsLoading } = useQuery(GET_EVENT_STATS)
  const { data: eventsData, loading: eventsLoading } = useQuery(GET_EVENTS, {
    variables: { limit: 10 },
  })

  const stats = statsData?.eventStats
  const recentEvents = eventsData?.events?.events || []

  if (statsLoading || eventsLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  const topEventsData = (stats?.topEvents || []).map((event, index) => ({
    name: event.name,
    count: event.count,
    fill: COLORS[index % COLORS.length],
  }))

  const eventsByTypeData = (stats?.eventsByType || []).map((item, index) => ({
    name: item.type,
    value: item.count,
    fill: COLORS[index % COLORS.length],
  }))

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard label="Total Events" value={stats?.totalEvents || 0} />
        <StatCard label="Events Today" value={stats?.eventsToday || 0} />
        <StatCard label="Events This Week" value={stats?.eventsThisWeek || 0} />
        <StatCard label="Unique Sessions" value={stats?.uniqueSessions || 0} />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Events Chart */}
        <div className="card">
          <h2 className="text-lg font-semibold mb-4">Top Events</h2>
          {topEventsData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={topEventsData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" />
                <YAxis dataKey="name" type="category" width={120} tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="count" fill="#3B82F6" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-gray-500 text-center py-8">No events recorded yet</p>
          )}
        </div>

        {/* Events by Type Chart */}
        <div className="card">
          <h2 className="text-lg font-semibold mb-4">Events by Type</h2>
          {eventsByTypeData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={eventsByTypeData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  outerRadius={100}
                  dataKey="value"
                >
                  {eventsByTypeData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-gray-500 text-center py-8">No events recorded yet</p>
          )}
        </div>
      </div>

      {/* Recent Events */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4">Recent Events</h2>
        {recentEvents.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-600">Event</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-600">Type</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-600">URL</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-600">Time</th>
                </tr>
              </thead>
              <tbody>
                {recentEvents.map((event) => (
                  <tr key={event.id} className="border-b hover:bg-gray-50">
                    <td className="py-3 px-4">
                      <span className="font-medium">{event.eventName}</span>
                    </td>
                    <td className="py-3 px-4">
                      <span className={`inline-block px-2 py-1 rounded-full text-xs ${getTypeColor(event.eventType)}`}>
                        {event.eventType}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-sm text-gray-600 truncate max-w-xs">
                      {event.url || '-'}
                    </td>
                    <td className="py-3 px-4 text-sm text-gray-600">
                      {format(new Date(event.timestamp), 'MMM d, HH:mm')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-gray-500 text-center py-8">No events recorded yet. Start tracking!</p>
        )}
      </div>
    </div>
  )
}

function StatCard({ label, value }) {
  return (
    <div className="stat-card">
      <span className="stat-value">{value.toLocaleString()}</span>
      <span className="stat-label">{label}</span>
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
