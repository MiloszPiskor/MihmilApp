export function getSingleResponse<T>(response: readonly T[]): T {
  if (!Array.isArray(response) || response.length === 0) {
    throw new Error('Unexpected API response format. Expected a non-empty array.');
  }

  return response[0];
}
