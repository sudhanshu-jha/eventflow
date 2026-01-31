/**
 * React hook for component-level telemetry.
 * Provides easy access to tracing and event recording within React components.
 */

import { useCallback, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { 
  createComponentTracker, 
  trackPageView, 
  trackUserAction, 
  trackError,
  withSpan,
} from '../telemetry'

/**
 * Hook for component-level telemetry.
 * @param {string} componentName - Name of the component for tracing context
 * @returns {Object} Telemetry functions scoped to the component
 * 
 * @example
 * function MyComponent() {
 *   const { trackAction, trackError, withSpan } = useTelemetry('MyComponent')
 *   
 *   const handleClick = () => {
 *     trackAction('button_clicked', { buttonId: 'submit' })
 *   }
 * }
 */
export function useTelemetry(componentName) {
  const tracker = createComponentTracker(componentName)
  
  return {
    trackAction: useCallback(tracker.trackAction, [componentName]),
    trackError: useCallback(tracker.trackError, [componentName]),
    withSpan: useCallback(tracker.withSpan, [componentName]),
  }
}

/**
 * Hook for automatic page view tracking.
 * Tracks page views whenever the route changes.
 * 
 * @example
 * function App() {
 *   usePageTracking()
 *   return <Routes>...</Routes>
 * }
 */
export function usePageTracking() {
  const location = useLocation()
  
  useEffect(() => {
    // Map paths to readable page names
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

/**
 * Hook for tracking user actions.
 * Returns a memoized function for tracking user interactions.
 * 
 * @returns {Function} trackAction function
 * 
 * @example
 * function Button() {
 *   const trackAction = useTrackAction()
 *   return <button onClick={() => trackAction('click', { element: 'button' })}>Click</button>
 * }
 */
export function useTrackAction() {
  return useCallback((action, details = {}) => {
    trackUserAction(action, details)
  }, [])
}

/**
 * Hook for tracking errors in error boundaries.
 * 
 * @returns {Function} trackError function
 * 
 * @example
 * function ErrorBoundary({ children }) {
 *   const handleError = useTrackError()
 *   // ... use in componentDidCatch
 * }
 */
export function useTrackError() {
  return useCallback((error, context = {}) => {
    trackError(error, context)
  }, [])
}

/**
 * Hook for wrapping async operations in a span.
 * Useful for tracking data fetching or other async operations.
 * 
 * @param {string} operationName - Name of the operation
 * @returns {Function} Function that wraps async operations
 * 
 * @example
 * function DataFetcher() {
 *   const tracedFetch = useTracedOperation('fetchData')
 *   
 *   const fetchData = async () => {
 *     return tracedFetch(async () => {
 *       const response = await fetch('/api/data')
 *       return response.json()
 *     })
 *   }
 * }
 */
export function useTracedOperation(operationName) {
  return useCallback(
    (fn, attributes = {}) => withSpan(operationName, fn, attributes),
    [operationName]
  )
}

export default useTelemetry
