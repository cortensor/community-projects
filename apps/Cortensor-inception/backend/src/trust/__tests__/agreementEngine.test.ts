// src/trust/__tests__/agreementEngine.test.ts

import { test, expect } from "vitest";
import { runAgreementEngine } from "../agreement/agreementEngine"

test("full agreement → RELEASE", () => {
  const result = runAgreementEngine([
    { inferenceId: "1", modelId: "a", output: "yes", confidence: 0.9 },
    { inferenceId: "2", modelId: "b", output: "yes", confidence: 0.8 },
    { inferenceId: "3", modelId: "c", output: "yes", confidence: 0.95 }
  ])

  expect(result.decision).toBe("RELEASE")
})

test("partial agreement → ESCALATE", () => {
  const result = runAgreementEngine([
    { inferenceId: "1", modelId: "a", output: "yes", confidence: 0.6 },
    { inferenceId: "2", modelId: "b", output: "yes", confidence: 0.5 },
    { inferenceId: "3", modelId: "c", output: "no", confidence: 0.9 }
  ])

  expect(result.decision).toBe("ESCALATE")
})

test("total disagreement → BLOCK", () => {
  const result = runAgreementEngine([
    { inferenceId: "1", modelId: "a", output: "a" },
    { inferenceId: "2", modelId: "b", output: "b" },
    { inferenceId: "3", modelId: "c", output: "c" }
  ])

  expect(result.decision).toBe("BLOCK")
})

test("no inference → BLOCK", () => {
  const result = runAgreementEngine([])
  expect(result.decision).toBe("BLOCK")
})
