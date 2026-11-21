/**
 * Runs the Python triage CLI behind the paid gateway and returns its report.
 *
 * Invocation (from the repo README quickstart):
 *   .venv/bin/issue-triage triage --repo openminion/openminion --issue 778
 *
 * The CLI prints a human-readable verdict and saves a pending snapshot JSON
 * under <repo-root>/.issue-triage/pending/<snapshot-id>.json
 * (src/issue_triage/cli.py `_save_snapshot`, SnapshotStore default root
 * ".issue-triage/pending" — relative to the process cwd, so we run the CLI
 * with cwd = repo root). The snapshot JSON is the structured report we
 * return; the raw CLI stdout is kept alongside it for audit.
 *
 * A triage run takes ~2 min (2 model calls paced >=45 s apart on the free
 * Pollinations tier). It never posts to GitHub: the snapshot stays pending
 * until a human runs `issue-triage approve --snapshot <id> --yes`.
 */
import { spawn } from "node:child_process";
import { promises as fs } from "node:fs";
import path from "node:path";
import { REPO_ROOT } from "./config";

export interface TriageReport {
  /** Parsed snapshot JSON (verdict + draft), when the CLI saved one. */
  report: Record<string, unknown> | null;
  /** Snapshot id, e.g. openminion-openminion-778-fbb60bfb. */
  snapshotId: string | null;
  /** Raw CLI stdout (human-readable verdict). */
  cliOutput: string;
}

const REPO_RE = /^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/;
const SNAPSHOT_RE = /\[snapshot saved:\s+([A-Za-z0-9_.-]+)\s+— pending approval\]/;

export async function runPythonTriage(
  repo: string,
  issue: number,
  opts: { triageBin: string; timeoutMs: number },
): Promise<TriageReport> {
  if (!REPO_RE.test(repo)) {
    throw new Error(`Invalid repo, expected owner/name, got ${JSON.stringify(repo)}`);
  }
  if (!Number.isInteger(issue) || issue <= 0) {
    throw new Error(`Invalid issue number, got ${JSON.stringify(issue)}`);
  }

  const { stdout, stderr, code } = await runCli(opts.triageBin, [
    "triage",
    "--repo",
    repo,
    "--issue",
    String(issue),
  ], opts.timeoutMs);

  if (code !== 0) {
    throw new Error(
      `issue-triage exited with code ${code}: ${(stderr || stdout).trim().slice(0, 2000)}`,
    );
  }

  const snapshotMatch = SNAPSHOT_RE.exec(stdout);
  const snapshotId = snapshotMatch ? snapshotMatch[1] : null;
  let report: Record<string, unknown> | null = null;
  if (snapshotId) {
    const snapshotPath = path.join(REPO_ROOT, ".issue-triage", "pending", `${snapshotId}.json`);
    try {
      report = JSON.parse(await fs.readFile(snapshotPath, "utf-8")) as Record<string, unknown>;
    } catch (err) {
      throw new Error(
        `issue-triage succeeded but snapshot ${snapshotId} could not be read ` +
          `at ${snapshotPath}: ${err instanceof Error ? err.message : String(err)}`,
      );
    }
  }
  return { report, snapshotId, cliOutput: stdout };
}

function runCli(
  bin: string,
  args: string[],
  timeoutMs: number,
): Promise<{ stdout: string; stderr: string; code: number | null }> {
  return new Promise((resolve, reject) => {
    const child = spawn(bin, args, { cwd: REPO_ROOT, timeout: timeoutMs });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (d: Buffer) => {
      stdout += d.toString("utf-8");
    });
    child.stderr.on("data", (d: Buffer) => {
      stderr += d.toString("utf-8");
    });
    child.on("error", reject);
    child.on("close", (code) => resolve({ stdout, stderr, code }));
  });
}
