import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { db } from "../src/db/prisma";
import { createSession } from "../src/core/session/session.service";
import { generateEvidence } from "../src/core/evidence/evidence.service";

describe("session and evidence services", () => {
  let session: any;

  beforeAll(async () => {
    // cleanup any existing test artifacts
    await db.evidence.deleteMany({});
    await db.session.deleteMany({});
  });

  it("creates a session and persists it", async () => {
    session = await createSession({ task: { prompt: "t1" }, policy: { minValidators: 1, minAgreement: 0.6 } } as any);
    expect(session.id).toBeTruthy();
    expect(typeof session.taskHash).toBe("string");
  });

  it("generates evidence and persists it", async () => {
    const validation = { agreementScore: 0, policyScore: 1 };
    const decision = { decision: "ESCALATE", confidence: 0.2, explanation: "No inference" };
    const ev = await generateEvidence(session, validation, decision as any);
    expect(ev.hash).toBeTruthy();
    const found = await db.evidence.findUnique({ where: { sessionId: session.id } });
    expect(found).not.toBeNull();
  });

  afterAll(async () => {
    await db.evidence.deleteMany({});
    await db.session.deleteMany({});
    await db.$disconnect();
  });
});
