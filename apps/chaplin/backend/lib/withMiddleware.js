// lib/withMiddleware.js
import { parseJsonRequest } from "./parseJsonRequest.js";

/**
 * withMiddleware(handler, options)
 * - handler: async function(req, res) { ... } expects req.body already parsed if options.parseJson true
 * - options:
 *    - allowedMethods: ['POST','GET'] default: null (no method check)
 *    - requireJson: boolean default false (checks Content-Type header)
 *    - parseJson: boolean default false (use parseJsonRequest and set req.body)
 *    - maxBodyBytes: number default 200*1024
 *    - rateLimit: { windowMs, max } or null
 *    - requireAuth: boolean default false (placeholder, call options.authFn if provided)
 *    - authFn: async (req) => { user object or throw on unauthorized } optional
 *
 * Returns a function (req, res) suitable for Vercel serverless export default.
 */

const defaultOptions = {
  allowedMethods: null,
  requireJson: false,
  parseJson: false,
  maxBodyBytes: 200 * 1024,
  rateLimit: null,
  requireAuth: false,
  authFn: null,
  // simple error mapper hook (optional)
  mapError: null
};

// Simple in-memory rate limiter (dev only). Use redis in prod.
const rateStore = new Map();
function checkRateLimit(ip, windowMs, max) {
  const now = Date.now();
  const entry = rateStore.get(ip) || { start: now, count: 0 };
  if (now - entry.start > windowMs) {
    entry.start = now;
    entry.count = 1;
    rateStore.set(ip, entry);
    return { ok: true };
  }
  entry.count += 1;
  rateStore.set(ip, entry);
  if (entry.count > max) {
    return { ok: false, retryAfterMs: windowMs - (now - entry.start) };
  }
  return { ok: true };
}

export function withMiddleware(handler, opts = {}) {
  const o = { ...defaultOptions, ...opts };

  return async function wrappedHandler(req, res) {
    try {
      // Method check
      if (o.allowedMethods && Array.isArray(o.allowedMethods)) {
        const method = (req.method || "GET").toUpperCase();
        if (!o.allowedMethods.map(m => m.toUpperCase()).includes(method)) {
          res.statusCode = 405;
          res.setHeader("Content-Type", "application/json");
          res.end(JSON.stringify({ error: "Method not allowed" }));
          return;
        }
      }

      // Rate-limit (optional)
      if (o.rateLimit && o.rateLimit.max && o.rateLimit.windowMs) {
        // get IP (try common headers)
        const xf = req.headers["x-forwarded-for"];
        const ip = xf ? String(xf).split(",")[0].trim() : (req.headers["x-real-ip"] || req.socket.remoteAddress || "unknown");
        const r = checkRateLimit(ip, o.rateLimit.windowMs, o.rateLimit.max);
        if (!r.ok) {
          res.statusCode = 429;
          res.setHeader("Content-Type", "application/json");
          res.end(JSON.stringify({ error: "Too many requests", retryAfterMs: r.retryAfterMs }));
          return;
        }
      }

      // Require JSON header
      if (o.requireJson) {
        const ct = (req.headers["content-type"] || "").toLowerCase();
        if (!ct.includes("application/json")) {
          res.statusCode = 400;
          res.setHeader("Content-Type", "application/json");
          res.end(JSON.stringify({ error: "Content-Type must be application/json" }));
          return;
        }
      }

      // Auth hook (optional)
      if (o.requireAuth) {
        if (typeof o.authFn !== "function") {
          res.statusCode = 500;
          res.setHeader("Content-Type", "application/json");
          res.end(JSON.stringify({ error: "Auth required but no authFn provided" }));
          return;
        }
        try {
          const user = await o.authFn(req);
          // attach user to request for downstream
          req.user = user;
        } catch (err) {
          res.statusCode = 401;
          res.setHeader("Content-Type", "application/json");
          res.end(JSON.stringify({ error: "Unauthorized", detail: err.message || String(err) }));
          return;
        }
      }

      // Parse JSON body if requested (and attach to req.body)
      if (o.parseJson) {
        try {
          const parsed = await parseJsonRequest(req, { maxSize: o.maxBodyBytes });
          req.body = parsed;
        } catch (err) {
          const code = err?.code || 400;
          res.statusCode = code;
          res.setHeader("Content-Type", "application/json");
          res.end(JSON.stringify({ error: err.message || "Invalid request" }));
          return;
        }
      }

      // call handler
      await handler(req, res);
    } catch (err) {
      // Allow custom mapping
      if (typeof o.mapError === "function") {
        try {
          const mapped = o.mapError(err);
          res.statusCode = mapped.status || 500;
          res.setHeader("Content-Type", "application/json");
          res.end(JSON.stringify(mapped.body || { error: "Internal error" }));
          return;
        } catch (mapErr) {
          // fallback
        }
      }
      // default error response
      console.error("Unhandled error in middleware wrapper:", err);
      if (!res.headersSent) {
        res.statusCode = 500;
        res.setHeader("Content-Type", "application/json");
        res.end(JSON.stringify({ error: "Internal server error", detail: String(err) }));
      } else {
        try { res.end(); } catch (e) {}
      }
    }
  };
}