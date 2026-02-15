import "dotenv/config";
import { SessionV2, SessionQueueV2, provider } from "../src/adapters/cortensor/client";

function listContractFunctions(name: string, contract: any) {
  console.log(`\n-- ${name} --`);
  if (!contract) {
    console.log(`${name} is not configured or is a stub`);
    return;
  }

  if (contract.interface && contract.interface.functions) {
    const fns = Object.keys(contract.interface.functions).sort();
    console.log(`${name} functions (${fns.length}):`);
    for (const f of fns) console.log(`  - ${f}`);
  } else {
    console.log(`${name} has no ABI interface available; ABI mismatch or stub detected.`);
  }

  // quick checks
  if (contract && typeof (contract as any).submit === "function") {
    console.log(`${name}.submit -> available`);
  } else {
    console.log(`${name}.submit -> MISSING`);
  }
}

console.log("RPC configured:", !!process.env.CORTENSOR_RPC);

async function checkProvider() {
  if (!process.env.CORTENSOR_RPC) {
    console.log("Provider available: false (CORTENSOR_RPC not configured)");
    return;
  }

  console.log("Checking provider responsiveness (5s timeout)...");

  const check = async () => {
    try {
      const bn = await (provider as any).getBlockNumber();
      console.log("Provider responsive. Block number:", bn);
      return;
    } catch (err: any) {
      console.warn("Provider check failed:", (err && err.message) || err);
    }
  };

  const timeout = new Promise((_, reject) => setTimeout(() => reject(new Error("provider timeout")), 5000));

  try {
    await Promise.race([check(), timeout]);
  } catch (err: any) {
    console.warn("Provider not responding within timeout. Continuing with ABI checks; this may be normal if RPC is slow or ws endpoint is not reachable.");
  }
}

async function main() {
  await checkProvider();

  listContractFunctions("SessionV2", SessionV2);
  listContractFunctions("SessionQueueV2", SessionQueueV2);

  console.log("\nGuidance:");
  console.log("- If SessionV2.submit is MISSING, verify the SessionV2 ABI JSON in src/adapters/cortensor/abi and the SESSION_V2_ADDRESS in your .env.");
  console.log("- Use 'npm run e2e:print-signer' to check the signer address and owned sessions once env is set.");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
