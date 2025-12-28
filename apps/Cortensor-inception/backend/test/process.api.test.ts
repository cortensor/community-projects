import request from "supertest";
import app from "../src/server";
import { describe, it, expect, vi } from "vitest";

describe("POST /api/claims/process", () => {
  it("returns 400 for missing body", async () => {
    const res = await request(app).post("/api/claims/process").send({});
    expect(res.status).toBe(400);
    expect(res.body).toHaveProperty("error");
  });

  it("accepts long and arbitrary text and returns blended envelope", async () => {
    const longText = "A".repeat(5000) + " with unicode 👍 and JSON {\"foo\": 1}";
    const res = await request(app).post("/api/claims/process").send({ text: longText, sessionId: 1, miners: 2 });
    expect(res.status).toBe(200);
    expect(res.body).toHaveProperty("blended");
    expect(res.body).toHaveProperty("llm");
    expect(res.body).toHaveProperty("sim");
    expect(Array.isArray(res.body.steps)).toBe(true);
  });

  it("accepts request when sessionId is missing by using default session", async () => {
    const res = await request(app).post("/api/claims/process").send({ text: "hello" });
    expect(res.status).toBe(200);
    expect(res.body).toHaveProperty("blended");
    expect(Array.isArray(res.body.steps)).toBe(true);
  });

  it("handles upstream LLM provider errors gracefully and falls back", async () => {
    // force generateLLMOutputs to throw the specific provider error we saw in UI
    const llm = await import("../src/adapters/llm/client");
    const spy = vi.spyOn(llm, "generateLLMOutputs").mockImplementation(() => {
      throw new Error("The string did not match the expected pattern.");
    });

    const res = await request(app).post("/api/claims/process").send({ text: "some input that triggers provider validation", sessionId: 1, miners: 2 });
    expect(res.status).toBe(200);
    // We should still return a structured response with steps and llmError recorded
    expect(Array.isArray(res.body.steps)).toBe(true);
    expect(res.body).toHaveProperty("llmError");
    expect(res.body.llmError).toContain("The string did not match the expected pattern");
    // blended fallback should still exist
    expect(res.body).toHaveProperty("blended");

    spy.mockRestore();
  });
});