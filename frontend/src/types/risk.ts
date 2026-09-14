export type RiskSeverity = 'NONE' | 'LOW' | 'MODERATE' | 'HIGH' | 'EXTREME';
export type RiskStatus = 'DETECTED' | 'NOT_DETECTED' | 'INSUFFICIENT_DATA' | 'INVALID';

export interface RiskEvidence {
  observed_value?: number | null;
  threshold_value?: number | null;
  unit?: string;
  crop_name: string;
  stage_name?: string | null;
  condition_description: string;
  metrics?: Record<string, any>;
}

export interface RiskResult {
  id?: number | null;
  panchayat_id: number;
  panchayat_name: string;
  block_id: number;
  block_name?: string | null;
  crop_id: number;
  crop_name: string;
  stage_name?: string | null;
  risk_type: string;
  risk_category: string;
  status: RiskStatus;
  severity: RiskSeverity;
  risk_score?: number | null;
  observed_value?: number | null;
  threshold_value?: number | null;
  unit?: string | null;
  duration_hours?: number | null;
  confidence: string;
  rule_version: string;
  rule_source: string;
  evidence: RiskEvidence;
  provenance?: Record<string, any>;
  evaluation_date: string;
  created_at?: string;
}

export interface PanchayatRiskProfile {
  panchayat_id: number;
  panchayat_name: string;
  lgd_code: string;
  block_id: number;
  block_name?: string | null;
  evaluation_date: string;
  crop_risks: Record<string, RiskResult[]>;
  detected_risks_count: number;
  highest_severity: RiskSeverity;
}

export interface RiskSubsystemStatus {
  total_risk_records: number;
  detected_risks: number;
  not_detected_evaluations: number;
  insufficient_data_evaluations: number;
  risk_counts_by_type: Record<string, number>;
  risk_counts_by_severity: Record<string, number>;
  panchayats_evaluated: number;
  crops_evaluated: number;
  active_rule_version: string;
}
