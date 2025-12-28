export function assertImmutable(existingHash?: string, newHash?: string) {
  if (existingHash && existingHash !== newHash) {
    throw new Error("Evidence immutability violation");
  }
}
