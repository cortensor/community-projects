export type RetentionPolicy = {
  minimumYears: number;
  legalHold: boolean;
};

export const DEFAULT_RETENTION: RetentionPolicy = {
  minimumYears: 7,
  legalHold: false,
};
