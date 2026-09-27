import { apiClient } from './client';
import {
  ProviderInfo,
  ProviderHealth,
  NationalValidationSummary,
  PromotionEvaluationSummary,
  BlockAggregationPayload,
} from '../types';

export const getProviders = async (): Promise<ProviderInfo[]> => {
  const resp = await apiClient<ProviderInfo[]>('/system/providers', undefined, []);
  return resp || [];
};

export const getProviderHealth = async (providerCode: string): Promise<ProviderHealth> => {
  const resp = await apiClient<ProviderHealth>(`/system/providers/${providerCode}/health`);
  return resp;
};

export const getNationalValidationSummary = async (): Promise<NationalValidationSummary> => {
  const resp = await apiClient<NationalValidationSummary>('/research/national-validation');
  return resp;
};

export const getPromotionEvaluation = async (): Promise<PromotionEvaluationSummary> => {
  const resp = await apiClient<PromotionEvaluationSummary>('/research/promotion-evaluation');
  return resp;
};

export const getBlockAggregation = async (
  blockId: number = 1,
  date?: string
): Promise<BlockAggregationPayload> => {
  const query = date ? `?date=${encodeURIComponent(date)}` : '';
  const resp = await apiClient<BlockAggregationPayload>(`/panchayat/block/${blockId}${query}`);
  return resp;
};
