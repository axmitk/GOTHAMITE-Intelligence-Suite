export interface Entity {
  id: string;
  kind: string;
  label: string;
  summary: string;
  source: string;
  confidence: number;
  first_seen: string;
  last_seen: string;
  attributes: Record<string, string | number>;
  provenance: Provenance;
  dataset_record?: DatasetRecord | null;
}
export type Provenance = "synthetic" | "dataset_derived" | "reference_derived";
export interface DatasetRecord {
  provenance_class: Provenance;
  dataset: string;
  dataset_name: string;
  dataset_version: string;
  license: string;
  source_url: string;
  doi: string | null;
  source_record_id: string;
  transformation_version: string;
  imported_at: string;
  details: Record<string, unknown>;
}
export interface Evidence {
  id: string;
  title: string;
  kind: string;
  source: string;
  observed_at: string;
  content: string;
  content_hash: string;
  confidence: number;
  provenance: Provenance;
  dataset_record?: DatasetRecord | null;
}
export interface Relationship {
  id: string;
  source_id: string;
  target_id: string;
  relation: string;
  evidence_id: string;
  confidence: number;
}
export interface GraphData {
  root: string;
  nodes: Entity[];
  edges: Relationship[];
  truncated: boolean;
  depth: number;
  limit: number;
}
export interface RiskFactor {
  label: string;
  points: number;
  evidence_ids: string[];
  reason: string;
  dimension?: string;
}
export interface Risk {
  score: number;
  level: string;
  factors: RiskFactor[];
  method: string;
  as_of: string;
  limitation: string;
}
export interface Finding {
  id: string;
  title: string;
  interpretation: string;
  evidence_ids: string[];
  confidence: string;
  reasoning: string[];
  next_step: string;
}
export interface Analysis {
  provider: string;
  generated: boolean;
  summary: string;
  findings: Finding[];
  uncertainties: string[];
}
export interface NistMapping {
  function: string;
  category: string;
  title: string;
  activity: string;
  status: string;
  basis: string;
  evidence_ids: string[];
  actions: { rule: string; title: string; category: string; status: string }[];
}
export interface Action {
  id: string;
  rule: string;
  title: string;
  priority: string;
  nist: string;
  reason: string;
  effect: string;
  evidence_ids: string[];
  simulated: boolean;
  status: string;
  decision_note: string;
}
export interface Note {
  id: string;
  kind: string;
  text: string;
  author: string;
  created_at: string;
}
export interface Audit {
  id: string;
  actor: string;
  action: string;
  detail: string;
  created_at: string;
}
export interface CaseData {
  id: string;
  title: string;
  summary: string;
  status: string;
  severity: string;
  analyst: string;
  created_at: string;
  updated_at: string;
  version: number;
  entities: Entity[];
  evidence: Evidence[];
  risk: Risk;
  analysis: Analysis;
  notes: Note[];
  actions: Action[];
  nist: NistMapping[];
  audit: Audit[];
  states: string[];
  advance: { next: string | null; ready: boolean; requirement: string };
}
export interface CaseSummary {
  id: string;
  title: string;
  status: string;
  severity: string;
  analyst: string;
  updated_at: string;
  risk: Risk;
  evidence_count: number;
  asset_count: number;
}
export interface DashboardData {
  snapshot: string;
  mode: string;
  indicators: number;
  relationships: number;
  evidence_count: number;
  active_cases: number;
  critical_cases: number;
  cases: CaseSummary[];
  sources: { name: string; count: number; mode: string }[];
  activity: { time: string; count: number }[];
  recent: Evidence[];
  provenance?: {
    indicators: Record<string, number>;
    evidence: Record<string, number>;
    relationships: Record<string, number>;
  };
}
export interface SearchResult {
  query: string;
  total: number;
  page: number;
  limit: number;
  results: Entity[];
}
export interface Profile {
  entity: Entity;
  evidence: Evidence[];
  neighbors: Entity[];
  relationships: Relationship[];
  related_cases: Entity[];
  next_step: string;
}
