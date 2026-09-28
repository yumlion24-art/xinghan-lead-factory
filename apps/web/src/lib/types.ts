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

