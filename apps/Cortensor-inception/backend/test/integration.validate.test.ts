import request from "supertest";
import { describe, it, expect, beforeAll, afterAll } from "vitest";
import app from "../src/server";
import { db } from "../src/db/prisma";

describe("POST /validate integration", () => {
  beforeAll(async () => {
    await db.evidence.deleteMany({});
    await db.session.deleteMany({});
  });

  it("returns 400 on invalid schema", async () => {
    const res = await request(app).post("/validate").send({ bad: "payload" });
    expect(res.status).toBe(400);
  });

  it("returns 400 when required policy fields are missing", async () => {
    const res = await request(app)
      .post("/validate")
      .send({ task: { prompt: "p" }, policy: { minValidators: 1, minAgreement: 0.6 }, meta: { caller: "x", purpose: "y" } });

    // missing timeoutMs and checks -> schema rejected
    expect(res.status).toBe(400);
  });

  it("returns 400 when meta fields are missing", async () => {
    const res = await request(app)
      .post("/validate")
      .send({ task: { prompt: "p" }, policy: { minValidators: 1, minAgreement: 0.6, timeoutMs: 1000, checks: [] } });

    expect(res.status).toBe(400);
  });

  it("returns ESCALATE for valid policy (Phase 2)", async () => {
    const res = await request(app)
      .post("/validate")
      .send({ task: { prompt: "p" }, policy: { minValidators: 1, minAgreement: 0.6, timeoutMs: 1000, checks: [] }, meta: { caller: "tester", purpose: "integration-test" } });

    expect(res.status).toBe(200);
    expect(res.body.decision).toBe("ESCALATE");
    expect(res.body.evidence.hash).toBeTruthy();
  });

  it("returns 400 when minValidators is invalid", async () => {
    const res = await request(app)
      .post("/validate")
      .send({ task: { prompt: "p" }, policy: { minValidators: 0, minAgreement: 0.6, timeoutMs: 1000, checks: [] }, meta: { caller: "x", purpose: "y" } });

    expect(res.status).toBe(400);
  });


  afterAll(async () => {
    await db.evidence.deleteMany({});
    await db.session.deleteMany({});
    await db.$disconnect();
  });
});
