import { test, expect } from "vitest";
import fs from "fs";
import path from "path";
import { blendBundles } from "../blend";

test("blends two sample bundles and produces ESCALATE for conflicting decisions", () => {
  const aPath = path.join(__dirname, "../../../out-variants/bundle-unanimous-1766846962910.json");
  const bPath = path.join(__dirname, "../../../out-llm/bundle-llm-1766846981811.json");

  const aRaw = fs.readFileSync(aPath, "utf8");
  const bRaw = fs.readFileSync(bPath, "utf8");

  const a = JSON.parse(aRaw);
  const b = JSON.parse(bRaw);

  const blended = blendBundles(aPath, a, bPath, b);

  expect(blended.blended.diffs).toContain("decision");
  expect(blended.blended.decision).toBe("ESCALATE");
  expect(blended.sources.length).toBe(2);
  expect(typeof blended.createdAt).toBe("number");
});
