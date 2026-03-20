import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { trackPageView } from '../telemetry'

/**
 * Hook for automatic page view tracking.
 * Tracks page views whenever the route changes.
 */
export function usePageTracking() {
  const location = useLocation()

  useEffect(() => {
    const pageNames = {
      '/': 'Dashboard',
      '/login': 'Login',
      '/register': 'Register',
      '/events': 'Events',
      '/settings': 'Settings',
    }

    const pageName = pageNames[location.pathname] || 'Unknown'
    trackPageView(pageName, location.pathname)
  }, [location.pathname])
}
