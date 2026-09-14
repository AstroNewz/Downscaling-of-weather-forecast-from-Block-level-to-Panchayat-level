export interface ModelSummary {
  model_name: string;
  version: string;
  algorithm: string;
  is_active: boolean;
  registered_at?: string;
  artifact_path?: string;
}

export interface ModelMetricsSummary {
  model_version: string;
  dataset_version: string;
  train_mae: number;
  val_mae: number;
  test_mae: number;
  test_rmse: number;
  test_r2: number;
  baseline_coarse_mae: number;
  improvement_over_baseline_pct: number;
}

export interface FeatureImportanceItem {
  feature_name: string;
  importance: number;
  rank: number;
}
