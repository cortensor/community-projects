export interface Policy {
  minValidators: number;
  minAgreement: number; // 0..1
  timeoutMs: number;
  checks: Array<{ name: string; params?: Record<string, any> }>;
}
