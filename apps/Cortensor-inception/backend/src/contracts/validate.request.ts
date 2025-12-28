import { z } from "zod";

export const PolicyCheckSchema = z.object({
  name: z.string(),
  params: z.record(z.any()).optional(),
});

export const PolicySchema = z.object({
  minValidators: z.number().int().min(1),
  minAgreement: z.number().min(0).max(1),
  timeoutMs: z.number().int().positive(),
  checks: z.array(PolicyCheckSchema).min(0),
});

export const ValidateRequestSchema = z.object({
  task: z.object({
    prompt: z.string(),
    metadata: z.record(z.any()).optional(),
  }),
  policy: PolicySchema,
  meta: z.object({
    caller: z.string(),
    purpose: z.string(),
  }),
});

export type ValidateRequest = z.infer<typeof ValidateRequestSchema>;
