/**
 * Test buyer for the x402 triage gateway.
 *
 * Flow: POST /triage -> 402 -> @x402/fetch auto-builds the signed Concordium
 * payment (V1 sponsored transfer, facilitator as sponsor) and retries ->
 * gateway settles on testnet, runs triage, returns the report with a
 * PAYMENT-RESPONSE header carrying the settlement tx hash.
 *
 * Verified against @x402/concordium 2.31.0:
 * - Client signer: { accountAddress: AccountAddress.fromBase58(...),
 *   signer: buildBasicAccountSigner(hexKey) } — src/exact/client/scheme.ts
 *   docstring. The client fetches the sender nonce from the testnet gRPC
 *   node, builds the CCD transfer (amount in microCCD), names the sponsor
 *   from requirements.extra.feePayer, and signs as sender.
 * - Client registered on the specific testnet network (as in the repo's own
 *   integration test), NOT the "ccd:*" wildcard from the research sketch.
 * - wrapFetchWithPayment(fetch, client) from @x402/fetch.
 *
 * Needs a funded TESTNET payer account (in-wallet faucet, 2,000 test CCD):
 *   CCD_PAYER_ADDRESS, CCD_PAYER_PRIVATE_KEY (env only, never in a file).
 * The payer pays 1 test CCD to SERVICE_CCD_ADDRESS; the facilitator pays
 * the ~0.01 CCD network fee from its own test CCD.
 *
 * Usage:
 *   CCD_PAYER_ADDRESS=... CCD_PAYER_PRIVATE_KEY=... npm run test-buyer
 *   # or: REPO=owner/repo ISSUE=123 GATEWAY_URL=http://localhost:4021 npm run test-buyer
 */
import { x402Client } from "@x402/core/client";
import { wrapFetchWithPayment } from "@x402/fetch";
import { ExactConcordiumScheme } from "@x402/concordium/exact/client";
import { CONCORDIUM_TESTNET_CAIP2, getExplorerTxUrl } from "@x402/concordium";
import { AccountAddress, buildBasicAccountSigner } from "@concordium/web-sdk";

const GATEWAY_URL = process.env.GATEWAY_URL ?? "http://localhost:4021";
const REPO = process.env.REPO ?? "openminion/openminion";
const ISSUE = Number(process.env.ISSUE ?? "778");

const payerAddress = process.env.CCD_PAYER_ADDRESS ?? "";
const payerKey = process.env.CCD_PAYER_PRIVATE_KEY ?? "";
if (!payerAddress || !payerKey) {
  throw new Error(
    "CCD_PAYER_ADDRESS and CCD_PAYER_PRIVATE_KEY must be set in env " +
      "(testnet payer account, funded from the in-wallet faucet).",
  );
}
if (!Number.isInteger(ISSUE) || ISSUE <= 0) {
  throw new Error(`ISSUE must be a positive integer, got ${process.env.ISSUE}`);
}

async function main(): Promise<void> {
  const signer = {
    accountAddress: AccountAddress.fromBase58(payerAddress),
    signer: buildBasicAccountSigner(payerKey),
  };
  const client = new x402Client().register(
    CONCORDIUM_TESTNET_CAIP2,
    new ExactConcordiumScheme(signer),
  );
  const fetchWithPayment = wrapFetchWithPayment(fetch, client);

  console.log(`POST ${GATEWAY_URL}/triage  repo=${REPO} issue=${ISSUE}`);
  console.log(`payer: ${payerAddress}`);
  const res = await fetchWithPayment(`${GATEWAY_URL}/triage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repo: REPO, issue: ISSUE }),
  });

  const paymentResponse = res.headers.get("PAYMENT-RESPONSE");
  console.log(`HTTP ${res.status}`);
  console.log(`PAYMENT-RESPONSE: ${paymentResponse ?? "(absent)"}`);

  let txHash: string | null = null;
  if (paymentResponse) {
    try {
      const parsed = JSON.parse(
        Buffer.from(paymentResponse, "base64").toString("utf-8"),
      ) as { transaction?: string; network?: string; payer?: string };
      txHash = parsed.transaction ?? null;
      console.log(`settled tx: ${txHash ?? "(no transaction field)"}`);
      console.log(`payer: ${parsed.payer ?? "(unknown)"}`);
    } catch {
      console.log("(PAYMENT-RESPONSE is not base64 JSON; raw value printed above)");
    }
  }
  if (txHash) {
    console.log(`CCDExplorer (testnet): ${getExplorerTxUrl(CONCORDIUM_TESTNET_CAIP2, txHash)}`);
  } else {
    console.log("No tx hash — payment did not settle (see HTTP status / body).");
  }

  const body = await res.text();
  console.log("--- report ---");
  console.log(body.slice(0, 8000));
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
