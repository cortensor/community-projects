import fs from "fs";
import path from "path";
import { blendBundles } from "../src/utils/blend";
import type { EvidenceBundle } from "../src/phases/phase3_4/schema";

function latestBundleIn(dir: string) {
  if (!fs.existsSync(dir)) throw new Error(`dir not found: ${dir}`);
  const files = fs.readdirSync(dir).filter((f) => f.startsWith("bundle") && f.endsWith(".json"));
  if (files.length === 0) throw new Error(`no bundle files in ${dir}`);
  const withStats = files.map((f) => ({ f, m: fs.statSync(path.join(dir, f)).mtimeMs }));
  withStats.sort((a, b) => b.m - a.m);
  return path.join(dir, withStats[0].f);
}

async function run() {
  const simDir = process.argv[2] || process.env.SIM_DIR || "./out-variants";
  const llmDir = process.argv[3] || process.env.LLM_DIR || "./out-llm";
  const outDir = process.argv[4] || process.env.OUT_DIR || "./out-merged";

  const simPath = latestBundleIn(simDir);
  const llmPath = latestBundleIn(llmDir);

  const a: EvidenceBundle = JSON.parse(fs.readFileSync(simPath, "utf8"));
  const b: EvidenceBundle = JSON.parse(fs.readFileSync(llmPath, "utf8"));

  const blended = blendBundles(simPath, a, llmPath, b);

  fs.mkdirSync(outDir, { recursive: true });
  const outPath = path.join(outDir, `blended-${Date.now()}.json`);
  fs.writeFileSync(outPath, JSON.stringify(blended, null, 2));

  console.log("Blended result written to:", outPath);
  console.log(`- sources: ${simPath}, ${llmPath}`);
  console.log(`- blended.decision: ${blended.blended.decision}`);
  console.log(`- diffs: ${blended.blended.diffs.join(", ") || "none"}`);
}

run().catch((err) => {
  console.error(err);
  process.exit(1);
});
