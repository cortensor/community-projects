import fs from "fs";
import path from "path";
import type { NextApiRequest, NextApiResponse } from "next";

function latestBundleIn(dir: string) {
  if (!fs.existsSync(dir)) return null;
  const files = fs.readdirSync(dir).filter((f) => f.startsWith("blended-") && f.endsWith(".json"));
  if (files.length === 0) return null;
  const withStats = files.map((f) => ({ f, m: fs.statSync(path.join(dir, f)).mtimeMs }));
  withStats.sort((a, b) => b.m - a.m);
  return path.join(dir, withStats[0].f);
}

export default function handler(req: NextApiRequest, res: NextApiResponse) {
  try {
    const base = path.join(process.cwd(), "../backend", "out-merged");
    const latest = latestBundleIn(base);
    if (!latest) return res.status(404).json({ error: "no blended bundles found" });
    const raw = fs.readFileSync(latest, "utf8");
    const json = JSON.parse(raw);
    return res.json({ path: latest, bundle: json });
  } catch (err: any) {
    console.error(err);
    return res.status(500).json({ error: err.message || String(err) });
  }
}
