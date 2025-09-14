import { createPublicClient, http, type Abi, type PublicClient } from 'viem';
import { config } from '@/lib/config';
import SessionQueueV2ABI from '@/abi/SessionQueueV2.json';
import { safeJsonParse } from '@/lib/utils';
import { FormattedTask, RawTask } from '@/types';

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


export async function getTaskResult(
  sessionId: string,
  taskId: string,
  client?: PublicClient
): Promise<[`0x${string}`[], string[]]> {
  const publicClient = client || getInternalClient();

  try {
    const [miners, results] = await publicClient.readContract({
      address: config.contracts.sessionQueueV2.address,
      abi: SessionQueueV2ABI as Abi,
      functionName: 'getTaskResults',
      args: [BigInt(sessionId), BigInt(taskId)],
    }) as [any[], string[]];
    return [miners, results];
  } catch (error) {
    return [[], []];
  }
}

export async function getSessionHistory(
  sessionId: string,
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

    return Promise.all(rawTasks.map(task => formatTask(task, publicClient)));
  } catch (error) {
    console.error(`[QueueService] Error fetching history for session ${sessionId}:`, error);
    throw new Error('Failed to retrieve task history.');
  }
}