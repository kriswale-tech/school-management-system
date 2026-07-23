export type QueryParamValue = string | number | boolean | null | undefined;

export const getQueryUrl = <T extends Record<string, QueryParamValue>>(
  url: string,
  params: T,
): string => {
  const searchParams = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === null || value === undefined || value === "") continue;
    searchParams.set(key, String(value));
  }
  const queryString = searchParams.toString();
  if (!queryString) return url;
  const separator = url.includes("?") ? "&" : "?";
  return `${url}${separator}${queryString}`;
};