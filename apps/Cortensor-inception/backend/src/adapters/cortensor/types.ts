export type TrustedInferenceClaim = {
  kind: "TrustedInferenceClaim";

  source: "cortensor";
  miner: string;
  output: string;

  authenticated: true;

  provenance: {
    sessionId: number;
    taskId: number;
    network: "cortensor";
  };

  receivedAt: number;
};
