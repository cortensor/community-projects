export type KeyType = "rsa-2048";

export type AttestorKey = {
  id: string;
  type: KeyType;
  privateKeyPem: string;
  publicKeyPem: string;
};
