// Minimal decision engine placeholder.
export function decideFromScores(scores: number[]) {
  const avg = scores.reduce((a, b) => a + b, 0) / Math.max(scores.length, 1);
  if (avg >= 0.85) return { decision: 'RELEASE', confidence: avg };
  if (avg < 0.5) return { decision: 'REJECT', confidence: avg };
  return { decision: 'ESCALATE', confidence: avg };
}
