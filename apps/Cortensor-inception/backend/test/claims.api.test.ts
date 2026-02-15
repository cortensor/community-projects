import request from "supertest";
import { describe, it, expect } from "vitest";
import app from "../src/server";

describe("/api/claims endpoints", () => {
  it("returns 400 when submit body missing", async () => {
    const res = await request(app).post("/api/claims/submit").send({});
    expect(res.status).toBe(400);
  });

  it("returns 400 when audit verify missing fields", async () => {
    const res = await request(app).post("/api/claims/audit/verify").send({});
    expect(res.status).toBe(400);
  });
});
