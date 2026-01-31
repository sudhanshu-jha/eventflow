/**
 * OpenTelemetry configuration for EventFlow frontend.
 * 
 * This module provides complete browser observability including:
 * - Distributed tracing for fetch/XHR requests
 * - Document load performance monitoring
 * - User interaction tracking
 * - Context propagation for backend correlation
 */

import { WebTracerProvider } from '@opentelemetry/sdk-trace-web';
import { BatchSpanProcessor } from '@opentelemetry/sdk-trace-base';
import { Resource } from '@opentelemetry/resources';
import { 
  SEMRESATTRS_SERVICE_NAME, 
  SEMRESATTRS_SERVICE_VERSION,
  SEMRESATTRS_DEPLOYMENT_ENVIRONMENT 
} from '@opentelemetry/semantic-conventions';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { ZoneContextManager } from '@opentelemetry/context-zone';
import { registerInstrumentations } from '@opentelemetry/instrumentation';
import { FetchInstrumentation } from '@opentelemetry/instrumentation-fetch';
import { XMLHttpRequestInstrumentation } from '@opentelemetry/instrumentation-xml-http-request';
import { DocumentLoadInstrumentation } from '@opentelemetry/instrumentation-document-load';
import { UserInteractionInstrumentation } from '@opentelemetry/instrumentation-user-interaction';
import { W3CTraceContextPropagator } from '@opentelemetry/core';
import { trace, context } from '@opentelemetry/api';

// Configuration from environment variables (Vite)
const OTEL_ENDPOINT = import.meta.env.VITE_OTEL_EXPORTER_OTLP_ENDPOINT || 'http://localhost:4318';
const SERVICE_NAME = import.meta.env.VITE_OTEL_SERVICE_NAME || 'eventflow-frontend';
const ENVIRONMENT = import.meta.env.MODE || 'development';

// Store provider reference for shutdown
let tracerProvider = null;

/**
 * Initialize OpenTelemetry for the browser.
 * Should be called as early as possible in the application lifecycle.
 */
export function initTelemetry() {
  if (tracerProvider) {
    console.debug('Telemetry already initialized');
    return tracerProvider;
  }

  console.info('Initializing OpenTelemetry for frontend...');

  // Create resource with service information
  const resource = new Resource({
    [SEMRESATTRS_SERVICE_NAME]: SERVICE_NAME,
    [SEMRESATTRS_SERVICE_VERSION]: '1.0.0',
    [SEMRESATTRS_DEPLOYMENT_ENVIRONMENT]: ENVIRONMENT,
  });

  // Create tracer provider
  tracerProvider = new WebTracerProvider({
    resource,
  });

  // Configure OTLP exporter (HTTP/JSON for browser compatibility)
  const exporter = new OTLPTraceExporter({
    url: `${OTEL_ENDPOINT}/v1/traces`,
    headers: {},
  });

  // Add batch processor for efficient trace export
  tracerProvider.addSpanProcessor(
    new BatchSpanProcessor(exporter, {
      maxQueueSize: 100,
      maxExportBatchSize: 10,
      scheduledDelayMillis: 500,
      exportTimeoutMillis: 30000,
    })
  );

  // Register the provider globally
  tracerProvider.register({
    contextManager: new ZoneContextManager(),
    propagator: new W3CTraceContextPropagator(),
  });

  // Backend URLs to instrument (add trace headers)
  const backendUrls = [
    /localhost:6543/,
    /backend:6543/,
    /\/graphql/,
    /\/api\//,
  ];

  // Register auto-instrumentations
  registerInstrumentations({
    instrumentations: [
      // Fetch API instrumentation
      new FetchInstrumentation({
        propagateTraceHeaderCorsUrls: backendUrls,
        clearTimingResources: true,
        applyCustomAttributesOnSpan: (span, request, result) => {
          // Add custom attributes to fetch spans
          span.setAttribute('http.request_content_type', request.headers?.get?.('content-type') || 'unknown');
          if (result instanceof Response) {
            span.setAttribute('http.response_content_type', result.headers?.get?.('content-type') || 'unknown');
          }
        },
      }),

      // XMLHttpRequest instrumentation (for Apollo Client and other XHR users)
      new XMLHttpRequestInstrumentation({
        propagateTraceHeaderCorsUrls: backendUrls,
      }),

      // Document load instrumentation (page load performance)
      new DocumentLoadInstrumentation(),

      // User interaction instrumentation (clicks, etc.)
      new UserInteractionInstrumentation({
        eventNames: ['click', 'submit'],
        shouldPreventSpanCreation: (eventType, element) => {
          // Don't create spans for clicks on non-interactive elements
          const interactiveElements = ['BUTTON', 'A', 'INPUT', 'SELECT', 'TEXTAREA'];
          return !interactiveElements.includes(element.tagName);
        },
      }),
    ],
  });

  console.info('OpenTelemetry initialized successfully');
  return tracerProvider;
}

/**
 * Get a tracer instance for manual instrumentation.
 * @param {string} name - Tracer name (usually component or module name)
 * @returns {Tracer} OpenTelemetry tracer
 */
export function getTracer(name = 'eventflow-frontend') {
  return trace.getTracer(name);
}

/**
 * Create a custom span for tracking specific operations.
 * @param {string} name - Span name
 * @param {Function} fn - Function to execute within the span
 * @param {Object} attributes - Additional span attributes
 * @returns {*} Result of the function
 */
export async function withSpan(name, fn, attributes = {}) {
  const tracer = getTracer();
  return tracer.startActiveSpan(name, async (span) => {
    try {
      // Add custom attributes
      Object.entries(attributes).forEach(([key, value]) => {
        span.setAttribute(key, value);
      });

      const result = await fn();
      span.setStatus({ code: 1 }); // OK
      return result;
    } catch (error) {
      span.setStatus({ code: 2, message: error.message }); // ERROR
      span.recordException(error);
      throw error;
    } finally {
      span.end();
    }
  });
}

/**
 * Record a custom event/span for analytics.
 * @param {string} eventName - Name of the event
 * @param {Object} attributes - Event attributes
 */
export function recordEvent(eventName, attributes = {}) {
  const tracer = getTracer();
  const span = tracer.startSpan(eventName);
  
  Object.entries(attributes).forEach(([key, value]) => {
    span.setAttribute(key, value);
  });
  
  span.end();
}

/**
 * Track a page view.
 * @param {string} pageName - Name of the page
 * @param {string} path - URL path
 */
export function trackPageView(pageName, path) {
  recordEvent('page_view', {
    'page.name': pageName,
    'page.path': path,
    'page.url': window.location.href,
    'page.referrer': document.referrer,
  });
}

/**
 * Track a user action.
 * @param {string} action - Action name
 * @param {Object} details - Action details
 */
export function trackUserAction(action, details = {}) {
  recordEvent('user_action', {
    'user.action': action,
    ...details,
  });
}

/**
 * Track an error.
 * @param {Error} error - Error object
 * @param {Object} context - Additional context
 */
export function trackError(error, errorContext = {}) {
  const tracer = getTracer();
  const span = tracer.startSpan('error');
  
  span.setStatus({ code: 2, message: error.message });
  span.recordException(error);
  
  Object.entries(errorContext).forEach(([key, value]) => {
    span.setAttribute(key, value);
  });
  
  span.end();
}

/**
 * Create a React hook for component-level tracing.
 * Usage: const { trackAction } = useTelemetry('MyComponent')
 */
export function createComponentTracker(componentName) {
  return {
    trackAction: (action, attributes = {}) => {
      recordEvent(`${componentName}.${action}`, {
        'component.name': componentName,
        ...attributes,
      });
    },
    trackError: (error, errorContext = {}) => {
      trackError(error, {
        'component.name': componentName,
        ...errorContext,
      });
    },
    withSpan: (name, fn, attributes = {}) => {
      return withSpan(`${componentName}.${name}`, fn, {
        'component.name': componentName,
        ...attributes,
      });
    },
  };
}

/**
 * Shutdown telemetry gracefully.
 * Should be called when the application is about to unmount.
 */
export function shutdownTelemetry() {
  if (tracerProvider) {
    tracerProvider.shutdown().then(() => {
      console.info('OpenTelemetry shutdown complete');
    });
  }
}

/**
 * Get current trace context for manual propagation.
 * Useful for passing trace context to web workers or iframes.
 */
export function getTraceContext() {
  const activeSpan = trace.getActiveSpan();
  if (!activeSpan) {
    return null;
  }
  
  const spanContext = activeSpan.spanContext();
  return {
    traceId: spanContext.traceId,
    spanId: spanContext.spanId,
    traceFlags: spanContext.traceFlags,
  };
}

// Export context for advanced usage
export { trace, context };
