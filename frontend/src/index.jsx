import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { ApolloProvider } from '@apollo/client'
import App from './App'
import { AuthProvider } from './context/AuthContext'
import { client } from './graphql/client'
import { initTelemetry, shutdownTelemetry } from './telemetry'
import './index.css'

// Initialize OpenTelemetry as early as possible
// This ensures all network requests are traced from the start
initTelemetry()

// Handle cleanup on page unload
window.addEventListener('beforeunload', () => {
  shutdownTelemetry()
})

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ApolloProvider client={client}>
      <BrowserRouter>
        <AuthProvider>
          <App />
        </AuthProvider>
      </BrowserRouter>
    </ApolloProvider>
  </React.StrictMode>
)
