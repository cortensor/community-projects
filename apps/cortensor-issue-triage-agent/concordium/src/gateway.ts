/**
 * x402 pay-per-triage gateway — Concordium testnet, 1 test CCD per report.
 *
 * Flow (x402 v2, `exact` scheme, sponsored V1 transfer):
 *   1. Buyer POSTs /triage without payment -> 402 + PAYMENT-REQUIRED header.
 *   2. Buyer retries with a signed payment (PAYMENT-SIGNATURE header).
 *   3. The self-hosted in-process facilitator verifies, co-signs as sponsor,
 *      submits to testnet and waits for finalization — BEFORE the handler
 *      runs. That ordering is the `upfront` payment flow, selected via
 *      `extra: { paymentFlow: "upfront" }` on the route (the Concordium
 *      server scheme declares supported flows ["authorization", "upfront"]
 *      with default "authorization"; core resolves the flow from
 *      requirements.extra.paymentFlow — see @x402/core server/paymentFlow.ts).
 *      The default "authorization" flow would run the handler after verify
 *      and settle only after a <400 response, which is NOT what we want:
 *      triage costs ~2 min of model calls and must not run unpaid.
 *   4. Only then does the /triage handler run the Python triage CLI and
 *      return the report. The middleware attaches the PAYMENT-RESPONSE
 *      header carrying the settlement tx hash.
 *
 * Verified API notes (@x402/* 2.31.0, @x402/concordium 2.31.0):
 * - `paymentMiddleware(routes, server)` — routes first, server second.
 *   Route keys may carry a verb: "POST /triage".
 * - Route `accepts` is ONE PaymentOption: { scheme, network, payTo,
 *   price: { amount, asset }, maxTimeoutSeconds?, extra? }. NOT the old
 *   v1 accepts-array / { facilitator, resourceServer } shape.
 * - Native CCD asset is the plain string "CCD" (6 decimals, microCCD
 *   amounts) — NOT the CAIP-19 id `ccd:.../slip44:919`. The client and
 *   facilitator both treat asset "CCD" (case-insensitive) as native, and
 *   PLT tokens by plain token id ("EURR", "USDR"). No `decimals` in
 *   `extra`: the client fetches token decimals from the chain.
 * - Network is the CAIP-2 id ccd:4221332d34e1694168c2a0c0b3fd0f27 (testnet).
 * - The server scheme injects the facilitator's fee-payer address into
 *   requirements.extra.feePayer during initialize(); the client needs it
 *   to name the sponsor. Do not set feePayer by hand.
 *
 * Testnet only. No mainnet code path exists in this service.
 */
import express, { NextFunction, Request, Response } from "express";
import { paymentMiddleware, x402ResourceServer } from "@x402/express";
import { CONCORDIUM_TESTNET_CAIP2 } from "@x402/concordium";
import { ExactConcordiumScheme } from "@x402/concordium/exact/server";
import { buildFacilitatorClient } from "./facilitator";
import { CCD_ASSET, PRICE_MICRO_CCD, TESTNET, loadConfig } from "./config";
import { runPythonTriage } from "./triage";

async function main(): Promise<void> {
  const config = loadConfig();

  const facilitatorClient = buildFacilitatorClient(
    config.facilitatorAddress,
    config.facilitatorPrivateKey,
  );
  const resourceServer = new x402ResourceServer(facilitatorClient);
  resourceServer.register(CONCORDIUM_TESTNET_CAIP2, new ExactConcordiumScheme());
  // Fetches the facilitator's supported kinds (incl. extra.feePayer) so the
  // server can build payment requirements. Idempotent; the middleware would
  // also do this lazily on the first protected request.
  await resourceServer.initialize();

  const app = express();
  app.use(express.json({ limit: "64kb" }));

  app.get("/health", (_req: Request, res: Response) => {
    res.json({
      ok: true,
      network: TESTNET,
      asset: CCD_ASSET,
      priceMicroCcd: PRICE_MICRO_CCD,
      payTo: config.serviceAddress,
      facilitator: config.facilitatorAddress,
    });
  });

  // The x402 gate. Everything below only runs for paid requests; unpaid
  // requests get 402 + PAYMENT-REQUIRED and never reach the handler.
  app.use(
    paymentMiddleware(
      {
        "POST /triage": {
          accepts: {
            scheme: "exact",
            network: CONCORDIUM_TESTNET_CAIP2,
            payTo: config.serviceAddress,
            price: { amount: PRICE_MICRO_CCD, asset: CCD_ASSET },
            maxTimeoutSeconds: 300,
            // Settle BEFORE the handler runs (see header comment).
            extra: { paymentFlow: "upfront" },
          },
          description: "Triage report for one GitHub issue",
          mimeType: "application/json",
        },
      },
      resourceServer,
    ),
  );

  app.post("/triage", async (req: Request, res: Response, next: NextFunction) => {
    try {
      const repo = typeof req.body?.repo === "string" ? req.body.repo : "";
      const issue = req.body?.issue;
      const issueNumber =
        typeof issue === "number" ? issue : Number.parseInt(String(issue ?? ""), 10);
      if (!repo || !Number.isInteger(issueNumber) || issueNumber <= 0) {
        res.status(400).json({
          error: "bad_request",
          message: 'Body must be JSON: { "repo": "owner/name", "issue": 778 }',
        });
        return;
      }
      // Runs ONLY after the facilitator settled the 1 test CCD payment
      // (upfront flow). ~2 min: 2 paced model calls on the free tier.
      const result = await runPythonTriage(repo, issueNumber, {
        triageBin: config.triageBin,
        timeoutMs: config.triageTimeoutMs,
      });
      res.json({
        repo,
        issue: issueNumber,
        priceMicroCcd: PRICE_MICRO_CCD,
        network: TESTNET,
        snapshotId: result.snapshotId,
        report: result.report,
        cliOutput: result.cliOutput,
      });
    } catch (err) {
      next(err);
    }
  });

  // Errors after payment was settled still surface; the payment itself is
  // not refunded by this demo gateway (settlement is final on-chain).
  app.use((err: unknown, _req: Request, res: Response, _next: NextFunction) => {
    console.error(err);
    res.status(500).json({
      error: "triage_failed",
      message: err instanceof Error ? err.message : String(err),
    });
  });

  app.listen(config.port, () => {
    console.log(`x402 triage gateway listening on :${config.port}`);
    console.log(`network: ${TESTNET} (Concordium testnet)`);
    console.log(`price: ${PRICE_MICRO_CCD} microCCD (1 test CCD) per report, asset ${CCD_ASSET}`);
    console.log(`payTo: ${config.serviceAddress}`);
    console.log(`facilitator (sponsor): ${config.facilitatorAddress}`);
  });
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
