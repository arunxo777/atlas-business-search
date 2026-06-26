import { useEffect, useRef, useState, useCallback } from "react";
import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export type VerificationStatus =
  | "highly_verified"
  | "verified"
  | "unverified"
  | "conflicted";

export type JobStatus =
  | "queued"
  | "searching"
  | "scraping"
  | "enriching"
  | "deduplicating"
  | "complete"
  | "failed";

export interface BusinessRecord {
  id: string;
  job_id: string;
  business_name: string;
  address: string | null;
  phone: string[];
  email: string[];
  website: string | null;
  working_hours: Record<string, string> | null;
  rating: number | null;
  review_count: number | null;
  services: string[];
  specialties: string[];
  license_information: string | null;
  certifications: string[];
  awards: string[];
  social_profiles: Record<string, string>;
  image_urls: string[];
  source_urls: Record<string, string[]>;
  verification_status: VerificationStatus;
  verification_details: Record<string, unknown>;
  source_reliability_score: number;
  rank_score: number;
  raw_sources: string[];
  discovered_at: string;
  last_updated: string;
}

export interface ResearchJob {
  id: string;
  query: string;
  category: string;
  location: string;
  status: JobStatus;
  progress_pct: number;
  businesses_found: number;
  businesses_verified: number;
  duplicates_removed: number;
  sources_searched: number;
  duration_seconds: number | null;
  llm_provider: string;
  created_at: string;
  completed_at: string | null;
  error: string | null;
  research_report?: ResearchReport;
}

export interface ResearchReport {
  search_summary: Record<string, unknown>;
  data_quality_summary: Record<string, number>;
  source_recommendations?: Record<string, string>;
  business_count: number;
  top_businesses: BusinessRecord[];
}

export interface ResearchRequest {
  query: string;
  max_results?: number;
  llm_provider?: string | null;
}

export interface ResearchResponse {
  job_id: string;
  status: string;
  cached?: boolean;
}

export interface PaginatedResults {
  items: BusinessRecord[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface LLMStatus {
  provider: string;
  model: string;
  latency_ms: number | null;
  available_providers: string[];
}

export interface HealthResponse {
  status: string;
  db: string;
  llm: string;
}

export interface ProgressEvent {
  phase: string;
  progress_pct: number;
  message: string;
  sources_found?: number;
  removed?: number;
}

const api = axios.create({
  baseURL: `${API_URL}/api`,
  headers: { "Content-Type": "application/json" },
  timeout: 8000,
});

export async function startResearch(
  request: ResearchRequest
): Promise<ResearchResponse> {
  const { data } = await api.post<ResearchResponse>("/research", request);
  return data;
}

export async function getJob(jobId: string): Promise<ResearchJob> {
  const { data } = await api.get<ResearchJob>(`/research/${jobId}`);
  return data;
}

export async function getResults(
  jobId: string,
  params?: {
    page?: number;
    page_size?: number;
    search?: string;
    sort_by?: string;
    sort_order?: string;
    verification_status?: string;
  }
): Promise<PaginatedResults> {
  const { data } = await api.get<PaginatedResults>(`/results/${jobId}`, {
    params,
  });
  return data;
}

export function getExportUrl(
  jobId: string,
  format: "json" | "csv" | "xlsx"
): string {
  return `${API_URL}/api/results/${jobId}/export?format=${format}`;
}

export async function getLLMStatus(): Promise<LLMStatus> {
  const { data } = await api.get<LLMStatus>("/llm/status");
  return data;
}

export async function getHealth(): Promise<HealthResponse> {
  const { data } = await api.get<HealthResponse>("/health");
  return data;
}

export interface SSEHandlers {
  onProgress?: (data: ProgressEvent) => void;
  onBusiness?: (business: BusinessRecord) => void;
  onSummary?: (job: ResearchJob) => void;
  onError?: (message: string) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
}

export function useSSE(jobId: string | null, handlers: SSEHandlers) {
  const [connected, setConnected] = useState(false);
  const handlersRef = useRef(handlers);
  handlersRef.current = handlers;

  const connect = useCallback(() => {
    if (!jobId) return () => undefined;

    const url = `${API_URL}/api/research/${jobId}/stream`;
    const source = new EventSource(url);

    source.onopen = () => {
      setConnected(true);
      handlersRef.current.onConnect?.();
    };

    source.addEventListener("progress", (e: MessageEvent) => {
      const data = JSON.parse(e.data) as ProgressEvent;
      handlersRef.current.onProgress?.(data);
    });

    source.addEventListener("business", (e: MessageEvent) => {
      const data = JSON.parse(e.data) as BusinessRecord;
      handlersRef.current.onBusiness?.(data);
    });

    source.addEventListener("summary", (e: MessageEvent) => {
      const data = JSON.parse(e.data) as ResearchJob;
      handlersRef.current.onSummary?.(data);
      source.close();
      setConnected(false);
      handlersRef.current.onDisconnect?.();
    });

    source.addEventListener("error", (e: MessageEvent) => {
      if (e.data) {
        const data = JSON.parse(e.data) as { message: string };
        handlersRef.current.onError?.(data.message);
      }
    });

    source.onerror = () => {
      setConnected(false);
      handlersRef.current.onDisconnect?.();
    };

    return () => {
      source.close();
      setConnected(false);
    };
  }, [jobId]);

  useEffect(() => {
    const cleanup = connect();
    return cleanup;
  }, [connect]);

  return { connected };
}
