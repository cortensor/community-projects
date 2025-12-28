import { db } from "../../db/prisma";
import { sha256 } from "../../utils/hash";
import type { ValidateRequest } from "../../contracts/validate.request";

export async function createSession(input: ValidateRequest) {
  const taskHash = sha256(input.task.prompt + JSON.stringify(input.policy));

  const now = Date.now();

  const session = await db.session.create({
    data: {
      taskHash,
      // Store policy as a JSON string for SQLite compatibility
      policy: JSON.stringify(input.policy),
      createdAt: BigInt(now),
    },
  });

  return session;
}
