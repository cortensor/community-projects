import { sha256 } from "../../utils/hash";
import { db } from "../../db/prisma";

export async function generateEvidence(session: any, validation: any, decision: any) {
  const payload = {
    sessionId: session.id,
    validation,
    decision,
    timestamp: Date.now(),
  };

  const hash = sha256(JSON.stringify(payload));

  const evidence = await db.evidence.create({
    data: {
      sessionId: session.id,
      hash,
      cid: null,
      createdAt: BigInt(Date.now()),
    },
  });

  return {
    hash: evidence.hash,
    cid: evidence.cid,
  };
}
