export type LeadGrade = "A" | "B" | "C";
export type ReviewStatus = "approved" | "rejected" | "needs_review";

export interface AccountSummary {
  id: string;
  display_name: string;
  normalized_domain: string;
  website_url: string | null;
  country: string | null;
  company_type: string | null;
  grade: LeadGrade | null;
  score: number;
  review_status: ReviewStatus;
  enrichment_mode: string;
  is_demo: boolean;
  created_at: string;
}

export interface AccountFilters {
  page: number;
  page_size: number;
  search?: string;
  country?: string;
  icp?: string;
  grade?: LeadGrade;
  review_status?: ReviewStatus;
  sort?: "created_desc" | "score_desc" | "score_asc" | "name_asc";
}

export interface AccountListResponse {
  items: AccountSummary[];
  total: number;
  page: number;
  page_size: number;
}

export interface DashboardData {
  accounts_total: number;
  grades: Record<LeadGrade, number>;
  reviews: Partial<Record<ReviewStatus, number>>;
  active_tasks: number;
  budget_usage: { pages: number; domains: number; ai_calls: number };
  recent_accounts?: AccountSummary[];
}

export interface ApiErrorEnvelope {
  error: {
    code: string;
    message: string;
    details?: unknown;
    request_id: string;
  };
}

export type SearchTaskStatus =
  | "queued"
  | "running"
  | "completed"
  | "partially_completed"
  | "cancelled"
  | "failed";

export interface SearchTaskSummary {
  id: string;
  query: string;
  status: SearchTaskStatus;
  progress: Record<string, number>;
  budget_usage: Record<string, number>;
  failure_summary: string | null;
  created_at: string;
  accounts?: Array<{ id: string; display_name: string; grade: LeadGrade | null }>;
}

export interface SearchTaskCreate {
  query: string;
  countries: string[];
  icp_ids: string[];
  seed_urls: string[];
  max_results: number;
  max_pages_per_domain: number;
}

export interface Evidence {
  id: string;
  signal_type: string;
  excerpt: string;
  source_url: string;
  confidence: number;
}

export interface ScoreContribution {
  rule_id: string;
  dimension: string;
  points: number;
  excerpt: string | null;
  source_url: string | null;
}

export interface ProductMatch {
  family_id: string;
  recommended_products: string[];
  reason: string;
  confidence: number;
  evidence_ids: string[];
}

export interface ReviewDecision {
  id: string;
  status: ReviewStatus;
  note: string | null;
  actor: string;
  created_at: string;
}

export interface AccountDetailData extends AccountSummary {
  industry: string | null;
  description: string | null;
  scale_signals: string[];
  contact_routes: Array<{ type: string; value: string }>;
  confidence: number;
  calculation_version: string | null;
  evidence: Evidence[];
  score_breakdown: ScoreContribution[];
  product_matches: ProductMatch[];
  review_history: ReviewDecision[];
}
