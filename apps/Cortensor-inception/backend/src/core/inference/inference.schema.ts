import { z } from "zod";

export const ProofOfInferenceSchema = z.object({
  proofType: z.literal("CORTENSOR_POI"),
  proofPayload: z.any(),
  proofHash: z.string().min(64),
});

export const InferenceResultSchema = z.object({
  nodeId: z.string().min(1),
  output: z.string().min(1),
  poi: ProofOfInferenceSchema,
  latencyMs: z.number().int().nonnegative(),
  receivedAt: z.number().int(),
});
