/**
 * TypeScript API and Data Model Types for GOTHAMITE
 * Strictly conforms to DATA_MODEL.md §2 and ARCHITECTURE.md §4.
 * No `any` types used for core domain entities.
 */

export type SourceType = 'forum' | 'marketplace';
export type ReliabilityLevel = 'high' | 'medium' | 'low';
export type SourceStatus = 'up' | 'down';

export interface Source {
  source_id: string;
  type: SourceType;
  reliability: ReliabilityLevel;
  last_scan: string | null;
  status: SourceStatus;
}

export interface Artifact {
  artifact_id: string;
  source_id: string;
  url: string;
  raw_content: string;
  content_hash: string;
  collected_at: string | null;
  relay_path: string[];
}

export interface Persona {
  persona_id: string;
  handle: string;
  source_id: string;
  first_seen: string | null;
  last_seen: string | null;
  post_count: number;
}

export type IdentifierType = 'pgp_fingerprint' | 'wallet' | 'handle' | 'contact';

export interface Identifier {
  identifier_id: string;
  type: IdentifierType;
  value: string;
  persona_id: string;
  artifact_id: string;
  observed_at: string | null;
}

export type RelationshipType = 'same_actor_suspected' | 'transacted_with' | 'trusts';
export type RelationshipStatus = 'proposed' | 'confirmed' | 'rejected';

export interface Relationship {
  relationship_id: string;
  from_persona_id: string;
  to_persona_id: string;
  type: RelationshipType;
  score: number;
  status: RelationshipStatus;
  created_at: string | null;
}

export type EvidenceSignalType =
  | 'shared_pgp'
  | 'shared_wallet'
  | 'handle_similarity'
  | 'temporal_succession'
  | 'activity_overlap_conflict'
  | 'lexical_similarity';

export type EvidenceDirection = 'supporting' | 'contradicting';

export interface Evidence {
  evidence_id: string;
  relationship_id?: string;
  signal_type: EvidenceSignalType;
  direction: EvidenceDirection;
  weight: number;
  artifact_id: string;
  note: string;
}

// Graph API payloads
export interface GraphNode {
  id: string;
  handle: string;
  source_id: string;
  first_seen: string | null;
  last_seen: string | null;
  post_count: number;
}

export interface GraphEdge {
  id: string;
  from_node: string;
  to_node: string;
  from_handle: string;
  to_handle: string;
  type: RelationshipType;
  score: number;
  status: RelationshipStatus;
  evidence_count: number;
}

export interface GraphPayload {
  nodes: GraphNode[];
  edges: GraphEdge[];
  node_count: number;
  edge_count: number;
}

export interface EdgePersonaSummary {
  persona_id: string;
  handle: string;
  source_id: string;
}

export interface EdgeDetails {
  relationship_id: string;
  type: RelationshipType;
  score: number;
  status: RelationshipStatus;
  created_at: string | null;
  from_persona: EdgePersonaSummary;
  to_persona: EdgePersonaSummary;
  evidence: Evidence[];
}

export interface EntitySearchMatch {
  persona_id: string;
  handle: string;
  source_id: string;
  match_reason: string;
  matched_term: string;
  first_seen: string | null;
  last_seen: string | null;
}

export interface EntitySearchResponse {
  query: string;
  count: number;
  results: EntitySearchMatch[];
}

export interface DossierIdentifier {
  identifier_id: string;
  type: IdentifierType;
  value: string;
  observed_at: string | null;
  artifact_id: string;
}

export interface DossierLink {
  relationship_id: string;
  direction: 'outgoing' | 'incoming';
  target_persona_id: string;
  target_handle: string;
  target_source: string;
  type: RelationshipType;
  score: number;
  status: RelationshipStatus;
}

export interface DossierTimelineItem {
  artifact_id: string;
  url: string;
  collected_at: string | null;
  snippet: string;
}

export interface PersonaDossier {
  persona_id: string;
  handle: string;
  source_id: string;
  source_type: string;
  first_seen: string | null;
  last_seen: string | null;
  post_count: number;
  identifiers: DossierIdentifier[];
  correlated_links: DossierLink[];
  timeline: DossierTimelineItem[];
}

export interface CorrelationResult {
  status: string;
  evaluated_pairs: number;
  relationships_created: number;
  relationships_updated: number;
  rejected_skipped: number;
  active_relationships: number;
  execution_time_seconds: number;
  edges: Array<{
    relationship_id: string;
    from: string;
    to: string;
    type: string;
    score: number;
    status: string;
  }>;
}

export interface HealthResponse {
  status: string;
  service: string;
}
