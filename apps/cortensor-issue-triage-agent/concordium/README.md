# x402 pay-per-triage gateway — Concordium testnet

A small Node.js/TypeScript Express gateway that puts the Python
**Trusted Issue Triage Agent** behind an x402 payment: **1 test CCD per
triage report**, `exact` scheme, Concordium testnet only. No mainnet, no
real money, no payments of any kind outside testnet.

Upstream research + verification notes: the parent project docs verify
every import path and payload field below against the real
`@x402/concordium` 2.31.0 package source (cloned at
`~/workspace/hackathon-tracker/concordium-build/x402-upstream/`).

## How it works

```
buyer --POST /triage--> gateway --402 + PAYMENT-REQUIRED--> buyer
buyer --signed V1 sponsored tx--> gateway -> facilitator verifies,
  co-signs as sponsor, submits to testnet, waits for finalization
  (upfront flow: settlement happens BEFORE the handler runs)
gateway -> .venv/bin/issue-triage triage --repo o/r --issue N (~2 min)
gateway --report + PAYMENT-RESPONSE (tx hash)--> buyer
```

- **Price:** `1000000` microCCD = 1 test CCD, asset `"CCD"`, network
  `ccd:4221332d34e1694168c2a0c0b3fd0f27` (Concordium testnet).
- **Facilitator:** self-hosted, in-process, from `@x402/concordium`
  (`toConcordiumFacilitatorSigner` + `ExactConcordiumScheme` facilitator).
  There is no public hosted Concordium facilitator; the service provider
  runs both the facilitator (sponsoring the ~0.01 CCD network fee) and the
  server (receiving payment). That is the documented model.
- **Handler runs only after settlement:** the route uses the `upfront`
  payment flow (`extra: { paymentFlow: "upfront" }`). The default
  `authorization` flow would run the handler after verify and settle only
  after a successful response — wrong here, since triage costs ~2 min of
  model calls and must not run unpaid.
- **Report:** the Python CLI's pending snapshot JSON
  (`.issue-triage/pending/<id>.json`) plus its printed verdict. The
  snapshot stays **pending** — nothing is ever posted to GitHub without a
  human running `issue-triage approve --snapshot <id> --yes`.

## Corrections to the research sketch (verified against package source)

1. **Asset is plain `"CCD"`, not `ccd:.../slip44:919`.** The research
   sketch guessed a CAIP-19 asset id. The real package uses `"CCD"` for
   native CCD (6 decimals) and plain PLT token ids (`"EURR"`, `"USDR"`)
   for tokens — see `src/constants.ts` (`CCD_ASSET_IDENTIFIER = "CCD"`),
   `src/exact/client/scheme.ts` (`isNativeCcd` check) and
   `src/exact/facilitator/scheme.ts` (`checkAssetType`). No `decimals`
   in `extra`: the client fetches token decimals from the chain.
2. **`paymentMiddleware(routes, server)` — routes first.** The sketch
   used the old v1 shape (`{ "POST /triage": { accepts: [...],
   facilitator, resourceServer } }`). v2.31 takes
   `(routes: RoutesConfig, server: x402ResourceServer)` and each route's
   `accepts` is a single `PaymentOption`
   (`{ scheme, network, payTo, price: { amount, asset },
   maxTimeoutSeconds, extra }`). Route keys may carry a verb
   (`"POST /triage"`).
3. **Facilitator bootstrap is `toConcordiumFacilitatorSigner` +
   `x402Facilitator`, not `HTTPFacilitatorClient({ url })`.** The
   facilitator is in-process; `HTTPFacilitatorClient` is only for talking
   to a *separate* facilitator HTTP service. The resource server needs a
   small `FacilitatorClient` wrapper because `x402Facilitator.getSupported()`
   returns a plain object while the interface requires a Promise — the same
   wrapper the repo's own integration test uses.
4. **CCDExplorer testnet URL pattern confirmed:**
   `https://ccdexplorer.io/testnet/transaction/<tx-hash>` (from the
   package's `getExplorerTxUrl`).
5. **Buyer registers on the specific testnet network**, not `"ccd:*"`.

## What you need before running (Allen)

Three funded **testnet** accounts. Funding path: Concordium Wallet for
Web (Chrome extension) → testnet → create identity with "Concordium
testnet IP" (no real ID) → create account → Activity → **Request CCD**
(2,000 test CCD per account, once per account, only before the account
has incoming transactions). There is **no verified public web faucet**
that funds an arbitrary address — the example-dApp faucet needs an X
post + CAPTCHA and has no hosted instance URL; do not rely on one.

| Account | Env var | Funded with | Purpose |
|---|---|---|---|
| Service (payee) | `SERVICE_CCD_ADDRESS` | — (receives) | Receives 1 test CCD per report |
| Facilitator (sponsor) | `CCD_FACILITATOR_ADDRESS` + `CCD_FACILITATOR_PRIVATE_KEY` | test CCD for fees (~0.01 CCD/settle) | Co-signs + pays network fee |
| Payer (demo buyer) | `CCD_PAYER_ADDRESS` + `CCD_PAYER_PRIVATE_KEY` (buyer only) | test CCD (1 per report) | Pays for the demo triage |

Keys live **only in server env at runtime**, never in files, chat, or
memory. The gateway refuses to start without the three gateway vars.

## Run the gateway

```bash
cd concordium
npm install
cp .env.example .env   # fill in the three gateway vars (testnet only)
npm run build          # tsc; or npm run typecheck for --noEmit
npm start              # listens on :4021 (PORT)
# dev (no build): npm run dev
```

Check it answers unauthenticated health (no payment needed):

```bash
curl localhost:4021/health
```

Check the 402 (no payment yet — expect HTTP 402 + PAYMENT-REQUIRED):

```bash
curl -i -X POST localhost:4021/triage \
  -H 'Content-Type: application/json' \
  -d '{"repo":"openminion/openminion","issue":778}'
```

## Run the test buyer (paid end-to-end)

```bash
cd concordium
CCD_PAYER_ADDRESS=<testnet payer address> \
CCD_PAYER_PRIVATE_KEY=<testnet payer hex key> \
  npm run test-buyer
# options: REPO=openminion/openminion ISSUE=778 GATEWAY_URL=http://localhost:4021
```

It prints the `PAYMENT-RESPONSE` header, the settlement tx hash, and the
CCDExplorer testnet link, then the triage report. A paid run takes
~2 min for triage plus ~10 s for testnet finalization.

## Files

| Path | What it is |
|---|---|
| `src/gateway.ts` | Express app + `paymentMiddleware` (`POST /triage`, upfront flow) |
| `src/facilitator.ts` | Self-hosted in-process facilitator (signer + scheme + wrapper) |
| `src/config.ts` | Env-only config; testnet constants; refuses to start without keys |
| `src/triage.ts` | Spawns `.venv/bin/issue-triage`, returns the snapshot JSON |
| `scripts/test-buyer.ts` | `@x402/fetch` buyer; prints the settled tx hash |
| `package.json` / `tsconfig.json` | Pinned to the verified `@x402/*` 2.31.0 |
| `.env.example` | Placeholders only — never a real key |

## Status / blockers

- **Not yet run end-to-end:** the repo's Concordium e2e testnet tests and
  any paid triage need the three funded testnet accounts above, which do
  not exist yet (see table). The e2e suite requires
  `CONCORDIUM_CLIENT_PRIVATE_KEY`, `CONCORDIUM_CLIENT_ADDRESS`,
  `CONCORDIUM_FACILITATOR_PRIVATE_KEY`, `CONCORDIUM_FACILITATOR_ADDRESS`,
  `CONCORDIUM_PAY_TO_ADDRESS` and throws at import without them.
- TypeScript compiles clean (`npm run build`); the Python test suite is
  unaffected (see run report in the handoff).
