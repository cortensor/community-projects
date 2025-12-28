import crypto from "crypto";
import type { AttestorKey } from "./keys";

export type Attestation = {
  signer: string;
  keyType: string;
  signature: string;
};

export function signBundle(hash: string, key: AttestorKey): Attestation {
  if (key.type !== "rsa-2048") {
    throw new Error("Unsupported key type");
  }

  const sign = crypto.createSign("RSA-SHA256");
  sign.update(hash);
  sign.end();

  return {
    signer: key.id,
    keyType: key.type,
    signature: sign.sign(key.privateKeyPem, "hex"),
  };
}
