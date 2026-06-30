import axios from 'axios';
import { useCallback, useState } from 'react';
import type {
  CompanyLookupApiResponse,
  CompanyLookupAvailableDto,
  CompanyLookupOccupiedDto,
  CompanyLookupOtherAddressDto,
  CompanyLookupRequest,
  CompanyLookupValidationErrorDto,
  CompanyLookupInvalidBodyDto,
} from '../types';
import { lookupCompany } from '../api/companyApi';
import { getSingleResponse } from '../../../utils/api';

export type CompanyLookupSuccessDto =
  | CompanyLookupAvailableDto
  | CompanyLookupOccupiedDto
  | CompanyLookupOtherAddressDto;

interface UseCompanyLookupResult {
  isLoading: boolean;
  response?: CompanyLookupSuccessDto;
  fieldErrors: Record<string, string>;
  serverError?: string;
  search: (payload: CompanyLookupRequest) => Promise<void>;
}

export function useCompanyLookup(): UseCompanyLookupResult {
  const [isLoading, setIsLoading] = useState(false);
  const [response, setResponse] = useState<CompanyLookupSuccessDto | undefined>(undefined);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [serverError, setServerError] = useState<string | undefined>(undefined);

  const handleValidationErrors = (data: CompanyLookupValidationErrorDto) => {
    const nextFieldErrors: Record<string, string> = {};

    data.missing.forEach((field) => {
      nextFieldErrors[field] = 'This field is required.';
    });

    setFieldErrors(nextFieldErrors);
  };

  const search = useCallback(async (payload: CompanyLookupRequest) => {
    setIsLoading(true);
    setResponse(undefined);
    setFieldErrors({});
    setServerError(undefined);

    try {
      const result = await lookupCompany(payload);
      const firstResult = getSingleResponse(result);
      setResponse(firstResult);
    } catch (error) {
      if (axios.isAxiosError(error)) {
        if (error.response) {
          const data = error.response.data as CompanyLookupValidationErrorDto | CompanyLookupInvalidBodyDto;

          if (data.error === 'missing fields') {
            handleValidationErrors(data);
            return;
          }

          if (data.error === 'invalid or missing JSON body') {
            setServerError('The request body is invalid or missing. Please review the form values.');
            return;
          }

          setServerError('An unexpected server error occurred. Please try again later.');
          return;
        }

        if (error.code === 'ECONNABORTED') {
          setServerError('The request timed out. Please try again later.');
          return;
        }

        setServerError('Network error. Please verify your connection and try again.');
        return;
      }

      setServerError('An unexpected error occurred.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    isLoading,
    response,
    fieldErrors,
    serverError,
    search,
  };
}
