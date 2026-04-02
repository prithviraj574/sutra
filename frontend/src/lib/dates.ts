const TZ_SUFFIX_PATTERN = /(Z|[+-]\d{2}:\d{2})$/i;

export function parseApiDate(dateString: string): Date {
  if (TZ_SUFFIX_PATTERN.test(dateString)) {
    return new Date(dateString);
  }
  return new Date(`${dateString}Z`);
}
