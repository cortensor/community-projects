import fetch from 'node-fetch';

const BASE = process.env.CORTENSOR_WEB2_URL || "";
const TASKS_PATH = process.env.CORTENSOR_WEB2_TASKS_PATH || "/sessions/{sessionId}/tasks";

function buildUrl(sessionId: number) {
  if (!BASE) throw new Error("CORTENSOR_WEB2_URL not configured");
  return `${BASE}${TASKS_PATH.replace("{sessionId}", String(sessionId))}`;
}

export async function submitTaskWeb2(sessionId: number, payload: unknown) {
  const url = buildUrl(sessionId);

  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: process.env.CORTENSOR_API_KEY ? `Bearer ${process.env.CORTENSOR_API_KEY}` : "",
    },
    body: JSON.stringify({ data: payload }),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Cortensor Web2 submission failed: ${res.status} ${res.statusText} - ${text}`);
  }

  return res.json();
}
