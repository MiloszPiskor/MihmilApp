export interface CompanyLookupRequest {
  nip: string;
  street: string;
  building_nr: string;
  postal_code: string;
  city: string;
}

export interface CompanyLookupAvailableDto {
  status: 'AVAILABLE';
  message: string;
}

export interface CompanyLookupOccupiedDto {
  status: 'OCCUPIED';
  company_name: string;
  street: string;
  building_nr: string;
  postal_code: string;
  city: string;
  assigned_rep_name: string;
  assigned_rep_reference: string;
}

export interface CompanyLookupOtherAddressDto {
  status: 'OCCUPIED_OTHER_ADDRESS';
  occupied_addresses: Array<{
    company_name: string;
    street: string;
    building_nr: string;
    postal_code: string;
    city: string;
    assigned_rep_name?: string;
  }>;
}

export interface CompanyLookupValidationErrorDto {
  error: 'missing fields';
  missing: Array<'nip' | 'street' | 'building_nr' | 'postal_code' | 'city'>;
}

export interface CompanyLookupInvalidBodyDto {
  error: 'invalid or missing JSON body';
}

export type CompanyLookupSuccessDto =
  | CompanyLookupAvailableDto
  | CompanyLookupOccupiedDto
  | CompanyLookupOtherAddressDto;

export type CompanyLookupErrorDto =
  | CompanyLookupValidationErrorDto
  | CompanyLookupInvalidBodyDto;

export type CompanyLookupApiResponse = Array<CompanyLookupSuccessDto>;
