import { SessionV2, signer } from "./client";

export async function createCortensorSession() {
  const tx = await SessionV2.create(
    "INCEPTION::TRUSTED-CLAIMS",
    "Decentralized inference ingress",
    await signer.getAddress(),
    1, 3, 1, 0,
    0, // Ephemeral
    false,
    0,
    0,
    300,
    5
  );

  await tx.wait();
}
