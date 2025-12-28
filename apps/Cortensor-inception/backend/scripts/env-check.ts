import { provider } from "../src/adapters/cortensor/client";

async function check() {
  const block = await provider.getBlockNumber();
  console.log("RPC OK. Block:", block);
}

check().catch((err) => {
  console.error(err);
  process.exit(1);
});
