// lib/parseJsonRequest.js
// Safe JSON parser for serverless endpoints.
// - reads raw body from req stream
// - enforces content-type application/json
// - enforces maxSize (bytes)
// - returns parsed object or throws { code, message }

export async function parseJsonRequest(req, { maxSize = 200 * 1024 } = {}) {
  return new Promise((resolve, reject) => {
    const ct = (req.headers["content-type"] || "").toLowerCase();
    if (!ct.includes("application/json")) {
      return reject({ code: 400, message: "Content-Type must be application/json" });
    }

    let received = 0;
    const chunks = [];

    // If body was already parsed by some middleware, don't try to read stream.
    // But in dev-server the getter may throw when accessed; so we avoid req.body.
    req.on("data", (chunk) => {
      received += chunk.length;
      if (received > maxSize) {
        // prevent further reading
        reject({ code: 413, message: "Payload too large" });
        req.destroy(); // stop reading
        return;
      }
      chunks.push(chunk);
    });

    req.on("end", () => {
      try {
        const raw = Buffer.concat(chunks).toString("utf8").trim();
        if (!raw) return resolve({}); // empty body -> empty object
        let parsed;
        try {
          parsed = JSON.parse(raw);
        } catch (err) {
          return reject({ code: 400, message: "Invalid JSON" });
        }
        return resolve(parsed);
      } catch (err) {
        return reject({ code: 400, message: "Invalid request body" });
      }
    });

    req.on("error", (err) => {
      return reject({ code: 400, message: "Error reading request body" });
    });
  });
}
