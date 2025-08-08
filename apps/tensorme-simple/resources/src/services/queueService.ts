import { createPublicClient, http, type Abi, type PublicClient } from 'viem';
import { config } from '@/lib/config';
import SessionQueueV2ABI from '@/abi/SessionQueueV2.json';
import { safeJsonParse } from '@/lib/utils';
import { FormattedTask, RawTask } from '@/types';

// This internal client is now a fallback for when the service is used on the server.
const getInternalClient = () => {
  return createPublicClient({
    chain: config.chain,
    transport: http(config.rpc.http),
  });
};

async function formatTask(task: RawTask, client: PublicClient): Promise<FormattedTask> {
  let results: FormattedTask['results'] = [];

  if (task.isCompleted) {
    try {
      const [miners, rawResults] = await client.readContract({
        address: config.contracts.sessionQueueV2.address,
        abi: SessionQueueV2ABI as Abi,
        functionName: 'getTaskResults',
        args: [task.sessionId, task.id],
      }) as [`0x${string}`[], string[]];
      results = miners.map((miner, index) => ({ miner, result: rawResults[index] }));
    } catch (error) {
      console.error(`[QueueService] Failed to get results for task ${task.id.toString()}:`, error);
    }
  }

  return {
    id: task.id.toString(),
    sessionId: task.sessionId.toString(),
    submitter: task.submitter,
    taskData: safeJsonParse(task.taskData),
    timestamp: new Date(Number(task.timestamp) * 1000).toISOString(),
    isCompleted: task.isCompleted,
    responseData: task.isCompleted ? safeJsonParse(task.responseData) : null,
    results,
  };
}


/**
 * Universal function to get task results. It uses the provided client if available,
 * otherwise it creates its own (for server-side use).
 * @param sessionId The session ID.
 * @param taskId The task ID.
 * @param client An optional viem PublicClient instance.
 * @returns An array of miners and results.
 */
export async function getTaskResult(
  sessionId: string,
  taskId: string,
  // Accept an optional client as a parameter
  client?: PublicClient
): Promise<[`0x${string}`[], string[]]> {
  // Use the provided client, or create a new one as a fallback.
  const publicClient = client || getInternalClient();

  try {
    const [miners, results] = await publicClient.readContract({
      address: config.contracts.sessionQueueV2.address,
      abi: SessionQueueV2ABI as Abi,
      functionName: 'getTaskResults',
      args: [BigInt(sessionId), BigInt(taskId)],
    }) as [`0x${string}`[], string[]];
    return [miners, results];
  } catch (error) {
    return [[], []];
  }
}

// Example of refactoring getSessionHistory as well
export async function getSessionHistory(
  sessionId: string,
  // Accept an optional client as a parameter
  client?: PublicClient
): Promise<FormattedTask[]> {
  const publicClient = client || getInternalClient();
  try {
    const rawTasks = await publicClient.readContract({
      address: config.contracts.sessionQueueV2.address,
      abi: SessionQueueV2ABI as Abi,
      functionName: 'getTasksBySessionId',
      args: [BigInt(sessionId)],
    }) as RawTask[];

    if (!rawTasks?.length) return [];

    // Pass the client to formatTask
    return Promise.all(rawTasks.map(task => formatTask(task, publicClient)));
  } catch (error) {
    console.error(`[QueueService] Error fetching history for session ${sessionId}:`, error);
    throw new Error('Failed to retrieve task history.');
  }
}