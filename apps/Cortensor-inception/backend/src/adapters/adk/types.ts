export type TreasuryPosition = {
  token: string;
  usdValue: number;
};

export type TreasurySnapshot = {
  totalUsdValue: number;
  positions: TreasuryPosition[];
};

export type RiskResult = {
  level: "LOW" | "MEDIUM" | "HIGH";
  score: number; // 0-100
  issues: string[];
};
