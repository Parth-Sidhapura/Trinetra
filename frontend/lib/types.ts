export interface Case {
  id: string; title: string; status: string; bnss_stage: string;
  data_classification: string; created_at: string;
  counts?: { evidence: number; entities: number; relationships: number };
}
export interface EvidenceRow {
  id: string; filename: string; sequence_number: number; sha256: string;
  chain_hash: string; size_bytes: number; scan_result: string;
  processing_status: string; uploaded_at: string; uploaded_by: string;
}
export interface Candidate {
  id: string; resolution_confidence: number; method: string; reasoning: string;
  status: string;
  a: { observation_id: string; raw_text: string; normalized_value: string;
       entity_type: string; extraction_method: string; page?: number } | null;
  b: { observation_id: string; raw_text: string; normalized_value: string;
       entity_type: string; extraction_method: string; page?: number } | null;
}
export interface GraphData {
  nodes: { data: any }[]; edges: { data: any }[];
  graph_version: number; layer: string;
  counts: { nodes: number; edges: number };
}
export interface Anomaly {
  id: string; kind: string; title: string; description: string;
  anomaly_confidence: number; source_precision: string;
  entities: { id: string; name: string }[];
  window_start?: string; window_end?: string; details: any;
  detector: { name: string; version: string }; disclaimer: string;
}
export interface Lead {
  id: string; source: { id: string; name: string };
  target: { id: string; name: string };
  link_prediction_score: number; method: string; status: string; evidence: string;
}
export interface Priority {
  entity_id: string; investigative_priority: number;
  components: Record<string, number>; graph_version: number;
  label: string; disclaimer: string;
}
