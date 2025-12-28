import { submitInference } from "../src/adapters/cortensor/tasks";

const sessionId = Number(process.argv[2] || process.env.SESSION_ID || 141);
const prompt = process.argv[3] || process.env.PROMPT || "Summarize why trust in AI should be earned.";

async function run() {
  console.log(`Submitting task to session ${sessionId}`);
  await submitInference(sessionId, {
    type: "chat",
    message: prompt,
  });

  console.log("Task submitted");
}

run().catch((err) => {
  console.error(err);
  process.exit(1);
});
