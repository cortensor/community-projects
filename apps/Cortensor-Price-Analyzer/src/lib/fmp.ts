const DEFAULT_FMP_BASE_URL = 'https://financialmodelingprep.com/stable';

// Financial Modeling Prep now serves all public APIs under the /stable base URL.
export const FMP_BASE_URL = (process.env.FMP_BASE_URL ?? DEFAULT_FMP_BASE_URL).replace(/\/$/, '');
