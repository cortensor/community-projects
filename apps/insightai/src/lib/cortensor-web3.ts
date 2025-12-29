import { ethers } from "ethers";

// Cortensor Contract Addresses (Arbitrum Sepolia - Testnet0)
// Properly checksummed EIP-55 addresses
const SESSION_V2_ADDRESS = "0x2e9cC638CF07efdeC82b4beF932Ca4a8Dcd55015";
const SESSION_QUEUE_V2_ADDRESS = "0x9a90B957E106894d598bF3ad912F3b604C085235";

// Arbitrum Sepolia RPC
const RPC_URL = "https://sepolia-rollup.arbitrum.io/rpc";

// Minimal ABI for SessionV2 (read-only functions we need)
const SESSION_V2_ABI = [
    "function getSession(uint256 sessionId) external view returns (tuple(uint256 id, string name, string metadata, address owner, address variableAddress, uint256 minNumOfNodes, uint256 maxNumOfNodes, uint256 redundant, uint256 numOfValidatorNodes, uint256 mode, bool reserveEphemeralNodes, uint256 sla, uint256 modelIdentifier, uint256 reservePeriod, uint256 maxTaskExecutionCount, bool active, uint256 createdAt, uint256 updatedAt))",
    "function getSessionsByAddress(address userAddr) external view returns (tuple(uint256 id, string name, string metadata, address owner, address variableAddress, uint256 minNumOfNodes, uint256 maxNumOfNodes, uint256 redundant, uint256 numOfValidatorNodes, uint256 mode, bool reserveEphemeralNodes, uint256 sla, uint256 modelIdentifier, uint256 reservePeriod, uint256 maxTaskExecutionCount, bool active, uint256 createdAt, uint256 updatedAt)[])",
    "function getEphemeralNodes(uint256 sessionId) external view returns (address[])",
];

// Minimal ABI for SessionQueueV2 (task submission and retrieval)
const SESSION_QUEUE_V2_ABI = [
    "function submit(uint256 sessionId, string memory taskData) external returns (uint256)",
    "function getTasksBySessionId(uint256 sessionId) external view returns (tuple(uint256 id, uint256 sessionId, uint256 globalId, string taskData, address[] assignedMiners, uint256 status, uint256 createdAt, uint256 endedAt)[])",
    "function getTaskResults(uint256 sessionId, uint256 taskId) external view returns (tuple(address miner, string result, uint256 timestamp)[])",
    "event TaskQueued(uint256 indexed sessionId, uint256 indexed taskId, uint256 globalId, string taskData)",
    "event TaskEnded(uint256 indexed sessionId, uint256 indexed taskId, address[] miners)",
];

// Provider singleton
let provider: ethers.JsonRpcProvider | null = null;

function getProvider(): ethers.JsonRpcProvider {
    if (!provider) {
        provider = new ethers.JsonRpcProvider(RPC_URL);
    }
    return provider;
}

// Get Session contract (read-only)
function getSessionContract(): ethers.Contract {
    return new ethers.Contract(SESSION_V2_ADDRESS, SESSION_V2_ABI, getProvider());
}

// Get SessionQueue contract (read-only for now)
function getSessionQueueContract(): ethers.Contract {
    return new ethers.Contract(SESSION_QUEUE_V2_ADDRESS, SESSION_QUEUE_V2_ABI, getProvider());
}

// Get session details
export async function getSession(sessionId: number): Promise<{
    id: number;
    name: string;
    metadata: string;
    owner: string;
    active: boolean;
    modelIdentifier: number;
    minNumOfNodes: number;
    maxNumOfNodes: number;
}> {
    const contract = getSessionContract();
    const session = await contract.getSession(sessionId);
    return {
        id: Number(session.id),
        name: session.name,
        metadata: session.metadata,
        owner: session.owner,
        active: session.active,
        modelIdentifier: Number(session.modelIdentifier),
        minNumOfNodes: Number(session.minNumOfNodes),
        maxNumOfNodes: Number(session.maxNumOfNodes),
    };
}

// Get tasks for a session
export async function getTasksBySessionId(sessionId: number): Promise<{
    id: number;
    taskData: string;
    status: number;
    createdAt: number;
}[]> {
    const contract = getSessionQueueContract();
    const tasks = await contract.getTasksBySessionId(sessionId);
    return tasks.map((task: {
        id: bigint;
        taskData: string;
        status: bigint;
        createdAt: bigint;
    }) => ({
        id: Number(task.id),
        taskData: task.taskData,
        status: Number(task.status),
        createdAt: Number(task.createdAt),
    }));
}

// Get task results
export async function getTaskResults(sessionId: number, taskId: number): Promise<{
    miner: string;
    result: string;
    timestamp: number;
}[]> {
    const contract = getSessionQueueContract();
    const results = await contract.getTaskResults(sessionId, taskId);
    return results.map((r: { miner: string; result: string; timestamp: bigint }) => ({
        miner: r.miner,
        result: r.result,
        timestamp: Number(r.timestamp),
    }));
}

// Submit task to session (requires wallet with private key)
export async function submitTask(
    sessionId: number,
    taskData: string,
    privateKey: string
): Promise<{ taskId: number; txHash: string }> {
    const wallet = new ethers.Wallet(privateKey, getProvider());
    const contract = new ethers.Contract(SESSION_QUEUE_V2_ADDRESS, SESSION_QUEUE_V2_ABI, wallet);

    const tx = await contract.submit(sessionId, taskData);
    const receipt = await tx.wait();

    // Parse TaskQueued event to get taskId
    const taskQueuedEvent = receipt.logs.find((log: ethers.Log) => {
        try {
            const parsed = contract.interface.parseLog({
                topics: log.topics as string[],
                data: log.data,
            });
            return parsed?.name === "TaskQueued";
        } catch {
            return false;
        }
    });

    let taskId = 0;
    if (taskQueuedEvent) {
        const parsed = contract.interface.parseLog({
            topics: taskQueuedEvent.topics as string[],
            data: taskQueuedEvent.data,
        });
        taskId = Number(parsed?.args?.taskId || 0);
    }

    return {
        taskId,
        txHash: receipt.hash,
    };
}

// Wait for task result with polling
export async function waitForTaskResult(
    sessionId: number,
    taskId: number,
    timeoutMs: number = 60000,
    pollIntervalMs: number = 3000
): Promise<string | null> {
    const startTime = Date.now();

    while (Date.now() - startTime < timeoutMs) {
        try {
            const results = await getTaskResults(sessionId, taskId);
            if (results.length > 0) {
                // Return first result
                return results[0].result;
            }
        } catch (error) {
            console.error("Error polling task results:", error);
        }

        // Wait before next poll
        await new Promise(resolve => setTimeout(resolve, pollIntervalMs));
    }

    return null; // Timeout
}

// High-level function: Submit task and wait for result
export async function executeTask(
    sessionId: number,
    prompt: string,
    privateKey: string,
    timeoutMs: number = 60000
): Promise<{
    success: boolean;
    result: string | null;
    taskId: number;
    txHash: string;
}> {
    try {
        // Submit task
        const { taskId, txHash } = await submitTask(sessionId, prompt, privateKey);

        // Wait for result
        const result = await waitForTaskResult(sessionId, taskId, timeoutMs);

        return {
            success: result !== null,
            result,
            taskId,
            txHash,
        };
    } catch (error) {
        console.error("Error executing task:", error);
        return {
            success: false,
            result: null,
            taskId: 0,
            txHash: "",
        };
    }
}

// Verify session exists and is active
export async function verifySession(sessionId: number): Promise<{
    valid: boolean;
    name?: string;
    model?: number;
    error?: string;
}> {
    try {
        const session = await getSession(sessionId);
        if (!session.active) {
            return { valid: false, error: "Session is not active" };
        }
        return {
            valid: true,
            name: session.name,
            model: session.modelIdentifier,
        };
    } catch (error) {
        return { valid: false, error: `Failed to get session: ${error}` };
    }
}
