// src/trust/agreement/normalize.ts

export function normalizeOutput(output: unknown): string {
  if (output === null || output === undefined) {
    return "null"
  }

  if (typeof output === "string") {
    return output.trim().toLowerCase()
  }

  if (typeof output === "number" || typeof output === "boolean") {
    return String(output)
  }

  // Canonical JSON (stable ordering)
  if (typeof output === "object") {
    return JSON.stringify(sortObject(output))
  }

  return String(output)
}

function sortObject(obj: any): any {
  if (Array.isArray(obj)) {
    return obj.map(sortObject)
  }

  if (obj !== null && typeof obj === "object") {
    return Object.keys(obj)
      .sort()
      .reduce((acc: any, key) => {
        acc[key] = sortObject(obj[key])
        return acc
      }, {})
  }

  return obj
}
