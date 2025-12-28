const ethers = require("ethers");
import SessionV2ABI from "./abi/SessionV2.json";
import SessionQueueV2ABI from "./abi/SessionQueueV2.json";

const RPC = process.env.CORTENSOR_RPC || "";
const PRIVATE_KEY = process.env.CORTENSOR_PRIVATE_KEY || "";
const SESSION_V2 = process.env.SESSION_V2_ADDRESS || "";
const QUEUE_V2 = process.env.SESSION_QUEUE_V2_ADDRESS || "";

// Provide graceful stubs when env is not configured so unit tests and local
// executions that don't use the on-chain client don't crash at import-time.
export const provider = RPC
  ? new ethers.providers.WebSocketProvider(RPC.replace("https", "wss"))
  : ({
      getBlockNumber: async () => 0,
      on: () => {},
      off: () => {},
      addListener: () => {},
    } as any);

export const signer = PRIVATE_KEY ? new ethers.Wallet(PRIVATE_KEY, provider) : ({} as any);

export const SessionV2 = SESSION_V2 ? new ethers.Contract(SESSION_V2, SessionV2ABI, signer) : ({} as any);

export const SessionQueueV2 = QUEUE_V2 ? new ethers.Contract(QUEUE_V2, SessionQueueV2ABI, provider) : ({} as any);
