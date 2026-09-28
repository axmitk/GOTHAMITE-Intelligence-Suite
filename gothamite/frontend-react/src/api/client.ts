import type {
  Artifact,
  CorrelationResult,
  EdgeDetails,
  EntitySearchResponse,
  GraphPayload,
  HealthResponse,
  PersonaDossier,
  RelationshipStatus,
} from '../types/api';
import { getSession } from '../workbench/api';

/**
 * GOTHAMITE Typed API Client
 * Wraps native fetch calls for each endpoint in ARCHITECTURE.md §4.
 * Uses configurable API base URL with environment variable fallback.
 */

const isBrowser = typeof window !== 'undefined';
const envApiUrl =
  typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_BASE_URL;

const API_BASE_URL = (envApiUrl || (isBrowser ? '/api/v1' : 'http://localhost:8000/api/v1')).replace(
  /\/+$/,
  ''
);
const ROOT_BASE_URL = API_BASE_URL.startsWith('/api/v1')
  ? ''
  : API_BASE_URL.replace(/\/api\/v1$/, '');

export class ApiError extends Error {
  status: number;
  body?: unknown;

  constructor(status: number, message: string, body?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.body = body;
  }
}

async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers || {});
  if (isBrowser && url.includes('/api/v1/')) {
    const session = await getSession();
    headers.set('X-CSRF-Token', session.csrf);
  }
  if (!headers.has('Accept')) {
    headers.set('Accept', 'application/json');
  }
  if (options.body && !(options.body instanceof FormData) && typeof options.body === 'string') {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(url, { ...options, headers });

  if (!response.ok) {
    let errorDetails: unknown = null;
    try {
      errorDetails = await response.json();
    } catch {
      try {
        errorDetails = await response.text();
      } catch {
        errorDetails = null;
      }
    }
    throw new ApiError(
      response.status,
      `API request failed [${response.status} ${response.statusText}]: ${url}`,
      errorDetails
    );
  }

  // Handle empty or text bodies (e.g. export CSV)
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    return (await response.json()) as T;
  }
  return (await response.text()) as unknown as T;
}

/**
 * Health check endpoint: GET /health
 */
export async function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>(`${ROOT_BASE_URL}/health`);
}

/**
 * Graph payload endpoint: GET /api/v1/graph
 */
export async function getGraph(): Promise<GraphPayload> {
  return request<GraphPayload>(`${API_BASE_URL}/graph`);
}

/**
 * Edge details with evidence provenance: GET /api/v1/graph/edge/{id}
 */
export async function getEdgeDetails(relationshipId: string): Promise<EdgeDetails> {
  return request<EdgeDetails>(`${API_BASE_URL}/graph/edge/${encodeURIComponent(relationshipId)}`);
}

/**
 * Review action to confirm or reject an edge: PATCH /api/v1/graph/edge/{id}
 */
export async function updateEdgeStatus(
  relationshipId: string,
  newStatus: RelationshipStatus
): Promise<EdgeDetails> {
  return request<EdgeDetails>(`${API_BASE_URL}/graph/edge/${encodeURIComponent(relationshipId)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status: newStatus }),
  });
}

/**
 * Ingest payload endpoint: POST /api/v1/ingest
 */
export async function ingestPayload(payload: Record<string, unknown>): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>(`${API_BASE_URL}/ingest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

/**
 * Trigger batch correlation pass: POST /api/v1/correlate
 */
export async function triggerCorrelation(): Promise<CorrelationResult> {
  return request<CorrelationResult>(`${API_BASE_URL}/correlate`, {
    method: 'POST',
  });
}

/**
 * Search across handles, PGP fingerprints, or wallet addresses: GET /api/v1/entities/search?q={query}
 */
export async function searchEntities(query: string): Promise<EntitySearchResponse> {
  const url = `${API_BASE_URL}/entities/search?q=${encodeURIComponent(query.trim())}`;
  return request<EntitySearchResponse>(url);
}

/**
 * Actor dossier and profile lookup: GET /api/v1/entities/persona/{id}
 */
export async function getPersonaDossier(personaId: string): Promise<PersonaDossier> {
  return request<PersonaDossier>(`${API_BASE_URL}/entities/persona/${encodeURIComponent(personaId)}`);
}

/**
 * Raw immutable provenance artifact lookup: GET /api/v1/artifacts/{id}
 */
export async function getArtifact(artifactId: string): Promise<Artifact> {
  return request<Artifact>(`${API_BASE_URL}/artifacts/${encodeURIComponent(artifactId)}`);
}

/**
 * Export intelligence data as JSON or CSV: GET /api/v1/export?format=json|csv
 */
export async function exportIntelligence(format: 'json' | 'csv' = 'json'): Promise<unknown> {
  return request<unknown>(`${API_BASE_URL}/export?format=${encodeURIComponent(format)}`);
}

export const apiClient = {
  getHealth,
  getGraph,
  getEdgeDetails,
  updateEdgeStatus,
  ingestPayload,
  triggerCorrelation,
  searchEntities,
  getPersonaDossier,
  getArtifact,
  exportIntelligence,
};

export default apiClient;
