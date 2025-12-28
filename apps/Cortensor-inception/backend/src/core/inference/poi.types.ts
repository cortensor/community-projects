export interface ProofOfInference {
  proofType: "CORTENSOR_POI";
  proofPayload: unknown; // opaque, validated externally
  proofHash: string; // sha256 of proofPayload
}
