import type { CompanyLookupRequest, CompanyLookupApiResponse } from '../types';
import { apiClient } from '../../../api/client';

export async function lookupCompany(
  payload: CompanyLookupRequest,
): Promise<CompanyLookupApiResponse> {
  const { data } = await apiClient.post<CompanyLookupApiResponse>(
    '/api/reps/company-lookup',
    payload,
  );

  return data;
}
