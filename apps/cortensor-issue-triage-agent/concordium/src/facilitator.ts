/**
 * Self-hosted Concordium facilitator (in-process).
 *
 * Verified against @x402/concordium 2.31.0
 * (x402-upstream/typescript/packages/mechanisms/concordium):
 *
 * - Facilitator signer: `toConcordiumFacilitatorSigner(address, hexKey,
 *   { host, port, useTls, network })` — src/signer.ts. The key is a
 *   hex-encoded Ed25519 private key from env, never from a file.
 * - Facilitator scheme: `new ExactConcordiumScheme({ signer,
 *   requireFinalization: true, finalizationTimeoutMs })` —
 *   src/exact/facilitator/scheme.ts. It verifies the 9 rules, adds the
 *   sponsor signature, submits the tx and waits for finalization.
 * - The scheme is registered on an `x402Facilitator` from
 *   `@x402/core/facilitator`, which is then wrapped in a `FacilitatorClient`
 *   for the resource server. The wrapper exists because
 *   `x402Facilitator.getSupported()` returns a plain object while the
 *   `FacilitatorClient` interface requires a Promise — the same wrapper the
 *   repo's own integration test uses
 *   (test/integrations/exact-concordium.test.ts, ConcordiumFacilitatorClient).
 *
 * There is no public hosted Concordium facilitator, so this in-process one
 * is the deployment model: the service provider runs both the facilitator
 * (sponsoring gas) and the server (receiving payment).
 */
import { x402Facilitator } from "@x402/core/facilitator";
import type { FacilitatorClient } from "@x402/core/server";
import type {
  PaymentPayload,
  PaymentRequirements,
  SettleResponse,
  SupportedResponse,
  VerifyResponse,
} from "@x402/core/types";
import {
  CONCORDIUM_TESTNET_CAIP2,
  getConcordiumGrpcUrl,
  parseGrpcUrl,
  toConcordiumFacilitatorSigner,
} from "@x402/concordium";
import { ExactConcordiumScheme } from "@x402/concordium/exact/facilitator";
import { TESTNET } from "./config";

/** Thin adapter: x402Facilitator -> FacilitatorClient (see header note). */
class InProcessFacilitatorClient implements FacilitatorClient {
  constructor(private readonly facilitator: x402Facilitator) {}

  verify(
    paymentPayload: PaymentPayload,
    paymentRequirements: PaymentRequirements,
  ): Promise<VerifyResponse> {
    return this.facilitator.verify(paymentPayload, paymentRequirements);
  }

  settle(
    paymentPayload: PaymentPayload,
    paymentRequirements: PaymentRequirements,
  ): Promise<SettleResponse> {
    return this.facilitator.settle(paymentPayload, paymentRequirements);
  }

  getSupported(): Promise<SupportedResponse> {
    return Promise.resolve(
      this.facilitator.getSupported() as unknown as SupportedResponse,
    );
  }
}

/**
 * Build the self-hosted testnet facilitator client.
 *
 * @param facilitatorAddress - Sponsor account (base58 testnet address).
 * @param facilitatorPrivateKey - Hex Ed25519 key of the sponsor account.
 */
export function buildFacilitatorClient(
  facilitatorAddress: string,
  facilitatorPrivateKey: string,
): FacilitatorClient {
  const [host, port] = parseGrpcUrl(getConcordiumGrpcUrl(CONCORDIUM_TESTNET_CAIP2));
  const signer = toConcordiumFacilitatorSigner(facilitatorAddress, facilitatorPrivateKey, {
    host,
    port,
    useTls: true,
    network: TESTNET,
  });
  const scheme = new ExactConcordiumScheme({
    signer,
    requireFinalization: true,
    finalizationTimeoutMs: 90_000,
  });
  const facilitator = new x402Facilitator().register(CONCORDIUM_TESTNET_CAIP2, scheme);
  return new InProcessFacilitatorClient(facilitator);
}
