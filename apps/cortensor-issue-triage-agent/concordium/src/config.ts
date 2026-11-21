/**
 * Gateway configuration, read from process env only.
 *
 * No key is ever read from a file and no default key exists: the gateway
 * refuses to start unless the three required testnet values are present.
 * Testnet only — the network constant below is Concordium testnet and there
 * is no mainnet code path.
 */
import path from "node:path";

/** Concordium testnet CAIP-2 id (verified against @x402/concordium constants). */
export const TESTNET = "ccd:4221332d34e1694168c2a0c0b3fd0f27" as const;

/** Native CCD asset id in x402/Concordium: plain "CCD", NOT a CAIP-19 id. */
export const CCD_ASSET = "CCD" as const;

/** Price per triage report: 1 test CCD = 1,000,000 microCCD (6 decimals). */
export const PRICE_MICRO_CCD = "1000000" as const;

/** Repo root = the issue-triage repo that contains this concordium/ dir. */
export const REPO_ROOT = path.resolve(__dirname, "..", "..");

/** Base58check shape for a Concordium account address (45-55 chars). */
const ADDRESS_RE = /^[123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz]{45,55}$/;

function required(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing required env var ${name} — see concordium/.env.example`);
  }
  return value;
}

function requiredAddress(name: string): string {
  const value = required(name);
  if (!ADDRESS_RE.test(value)) {
    throw new Error(`Env var ${name} does not look like a Concordium base58 account address`);
  }
  return value;
}

export interface GatewayConfig {
  /** Payee account (base58 testnet address): receives 1 test CCD per report. */
  serviceAddress: string;
  /** Facilitator/sponsor account (base58 testnet address): pays the tx fee. */
  facilitatorAddress: string;
  /** Hex Ed25519 private key of the facilitator/sponsor account. Env only. */
  facilitatorPrivateKey: string;
  port: number;
  /** Python triage CLI entry point. */
  triageBin: string;
  /** Triage run timeout in ms. */
  triageTimeoutMs: number;
}

export function loadConfig(): GatewayConfig {
  const serviceAddress = requiredAddress("SERVICE_CCD_ADDRESS");
  const facilitatorAddress = requiredAddress("CCD_FACILITATOR_ADDRESS");
  const facilitatorPrivateKey = required("CCD_FACILITATOR_PRIVATE_KEY");
  if (!/^[0-9a-fA-F]{64}$/.test(facilitatorPrivateKey)) {
    throw new Error(
      "CCD_FACILITATOR_PRIVATE_KEY must be a 64-hex-char Ed25519 private key " +
        "(as exported for buildBasicAccountSigner)",
    );
  }
  const port = Number(process.env.PORT ?? "4021");
  if (!Number.isInteger(port) || port <= 0 || port > 65535) {
    throw new Error(`PORT must be a valid port number, got ${process.env.PORT}`);
  }
  return {
    serviceAddress,
    facilitatorAddress,
    facilitatorPrivateKey,
    port,
    triageBin:
      process.env.ISSUE_TRIAGE_BIN ?? path.join(REPO_ROOT, ".venv", "bin", "issue-triage"),
    triageTimeoutMs: Number(process.env.TRIAGE_TIMEOUT_MS ?? "600000"),
  };
}
