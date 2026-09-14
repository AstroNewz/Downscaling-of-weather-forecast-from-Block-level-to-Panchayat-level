export type AdvisoryPriority = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFORMATIONAL';
export type AdvisoryStatus = 'ACTIVE' | 'DRAFT' | 'EXPIRED' | 'SUPPRESSED' | 'INSUFFICIENT_DATA' | 'EXPERT_REVIEW_REQUIRED';

export interface AdvisoryAction {
  action_category?: string;
  action_text?: string;
  timing?: string;
  urgency?: string;
  conditions?: Record<string, any>;
}

export interface AdvisoryResult {
  id?: number | null;
  panchayat_id: number;
  panchayat_name: string;
  block_id: number;
  block_name?: string | null;
  crop_id: number;
  crop_name: string;
  stage_name?: string | null;
  risk_log_id?: number | null;
  crop_context_id?: number | null;
  panchayat_weather_id?: number | null;
  advisory_type: string;
  advisory_category: string;
  priority: AdvisoryPriority;
  priority_rank: number;
  priority_reason?: string | null;
  title: string;
  message: string;
  action?: AdvisoryAction | null;
  rationale?: string | null;
  severity: string;
  confidence: string;
  confidence_reason?: string | null;
  valid_from: string;
  valid_until: string;
  forecast_date: string;
  issue_time: string;
  source_model: string;
  weather_model_version?: string | null;
  rule_version: string;
  advisory_rule_version: string;
  rule_source: string;
  language: string;
  status: AdvisoryStatus;
  is_expert_review_required: boolean;
  is_cropland_eligible: boolean;
  evidence?: Record<string, any> | null;
  provenance?: Record<string, any> | null;
  created_at?: string | null;
}

export interface PanchayatAdvisoryProfile {
  panchayat_id: number;
  panchayat_name: string;
  lgd_code: string;
  block_id: number;
  block_name?: string | null;
  forecast_date: string;
  crop_advisories: Record<string, AdvisoryResult[]>;
  total_active_advisories: number;
  highest_priority: string;
  expert_review_required: boolean;
}

export interface AdvisorySubsystemStatus {
  total_advisories: number;
  active_advisories: number;
  draft_advisories: number;
  expired_advisories: number;
  suppressed_advisories: number;
  insufficient_data_advisories: number;
  expert_review_required_advisories: number;
  advisories_by_priority: Record<string, number>;
  advisories_by_type: Record<string, number>;
  advisories_by_crop: Record<string, number>;
  advisories_by_panchayat: number;
  active_rule_version: string;
}
