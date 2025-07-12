import {
  createPublicClient, createWalletClient, http,
  decodeEventLog, type Abi,
  ContractFunctionRevertedError,
  BaseError,
  keccak256,
  encodeEventTopics,
} from 'viem';
import { config } from '@/lib/config';
import { FormattedSession, Message } from '@/types';
import SessionV2ABI from '@/abi/SessionV2.json';
import SessionQueueV2ABI from '@/abi/SessionQueueV2.json';
import { privateKeyToAccount } from 'viem/accounts';
import { sseManager } from '@/lib/sse';
import { cleanBotResponse } from '@/lib/utils';
import { getTaskResult } from './queueService';

function buildSystemPrompt(messages: Message[], persona?: string): string {
  const currentDate = new Date().toLocaleDateString('en-US', {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
  });

  const personaInstruction = persona || 'a world-class AI assistant named Cortensor. Your persona is helpful, professional, and slightly witty.';

  // Separate the last user message from the rest of the history.
  const historyMessages = messages.slice(0, -1);
  const currentUserMessage = messages[messages.length - 1];

  const formattedHistory = historyMessages
    .filter((msg) => !msg.isError)
    .map((msg) => {
      // Simple formatting for the history part of the prompt
      return msg.role === 'user' ? `User: ${msg.content}` : `Assistant: ${msg.content}`;
    }).join('\n');

  // This is the new, improved prompt structure
  return `You are ${personaInstruction} The current date is ${currentDate}. Provide accurate, concise, and well-formatted answers using Markdown for formatting. You must not repeat the user's question or include any XML tags in your response.

CRITICAL: Pay close attention to the user's most recent message. If the user changes the topic, you MUST adapt your response to the new topic. DO NOT repeat answers from earlier in the conversation. Your primary goal is to address the user's latest query.

Conversation History:
${formattedHistory}

Current User Message: ${currentUserMessage.content}

Respond directly to the current message above.
Assistant:`;
}

/**
 * Safely extracts the revert reason from a Viem contract error.
 * @param error The error object from a catch block.
 * @returns The specific reason string if it's a contract revert, otherwise null.
 */
function getContractRevertReason(error: any): string | null {
  if (error instanceof BaseError) {
    const revertError = error.walk((err: any) => err instanceof ContractFunctionRevertedError);
    if (revertError instanceof ContractFunctionRevertedError) {
      return revertError.reason || 'Transaction reverted without a reason.';
    }
  }
  return null;
}


interface TaskInfo {
  userId: string;
  chatId: string;
  taskId: bigint;
  sessionId: bigint;
  ackedCount?: number;
  precommitCount?: number;
  commitCount?: number;
  clientReference: string;
  session: FormattedSession;
}

class TaskService {
  private publicClient;
  private walletClient;
  private account;
  public isListenerActive = false;
  private sessionV2Listener: (() => void) | null = null;
  private sessionQueueV2Listener: (() => void) | null = null;

  // Maps taskId (as a string) -> { userId, clientReference }
  private taskContextMap = new Map<string, TaskInfo>();
  // Maps taskId (as a string) -> promise resolver
  private pendingResolvers = new Map<string, (response: string) => void>();
  // Maps clientReference -> temporary resolver before taskId is known
  private tempResolverMap = new Map<string, (response: string) => void>();


  constructor() {
    this.account = privateKeyToAccount(config.privateKey);
    const httpTransport = http(config.rpc.http);
    this.publicClient = createPublicClient({ chain: config.chain, transport: httpTransport });
    this.walletClient = createWalletClient({ account: this.account, chain: config.chain, transport: httpTransport });
  }

  public ensureListenersReady(): void {
    if (this.isListenerActive) return;
    this.isListenerActive = true;

    this.sessionV2Listener = this.publicClient.watchContractEvent({
      address: config.contracts.sessionV2.address,
      abi: SessionV2ABI as Abi,
      eventName: 'TaskSubmitted',
      onLogs: (logs) => this.handleTaskSubmitted(logs),
      onError: (error) => console.error('[TaskService] SessionV2 Listener Error:', error.message),
    });

    this.sessionQueueV2Listener = this.publicClient.watchContractEvent({
      address: config.contracts.sessionQueueV2.address,
      abi: SessionQueueV2ABI as Abi,
      eventName: 'allEvents',
      onLogs: (logs) => this.handleTaskStatusUpdate(logs),
      onError: (error) => console.error('[TaskService] SessionQueueV2 Listener Error:', error.message),
    });
  }

  public async processChatTask(session: FormattedSession, messages: Message[], persona?: string, clientReference?: string, userId?: string, chatId?: string): Promise<string> {
    this.ensureListenersReady();
    const finalPrompt = buildSystemPrompt(messages, persona);

    const taskPromise = new Promise<string>((resolve, reject) => {
      const resolver = (response: string) => resolve(response);
      // Temporarily associate the resolver and userId with the clientReference
      (resolver as any).userId = userId;
      (resolver as any).chatId = chatId;
      (resolver as any).session = session;
      this.tempResolverMap.set(clientReference || '', resolver);

      // Handle submission failure
      (resolver as any).reject = (err: Error) => reject(err);
    });

    await this.submitTaskToContract(session.id, finalPrompt, clientReference || '');

    return taskPromise;
  }

  private handleTaskSubmitted(logs: any[]): void {
    for (const log of logs) {
      try {
        const { args } = decodeEventLog({ abi: SessionV2ABI as Abi, data: log.data, topics: log.topics });
        const { taskId, clientReference, sessionId } = args as unknown as { taskId: bigint, clientReference: string, sessionId: bigint };
        const contextKey = [sessionId.toString(), taskId.toString()].join('-');

        const resolver = this.tempResolverMap.get(clientReference);
        if (resolver) {
          const userId = (resolver as any).userId;
          const chatId = (resolver as any).chatId;
          const session = (resolver as any).session;
          this.taskContextMap.set(contextKey, { userId, clientReference, chatId, taskId, sessionId, session });
          this.pendingResolvers.set(contextKey, resolver);
          this.tempResolverMap.delete(clientReference);

          const emitter = sseManager.getEmitter(userId);
          emitter.emit('statusUpdate', { clientReference, status: 'submitted', chatId, sessionId, taskId });
        }
      } catch (e) {
        console.error("handleTaskSubmitted", e);
      }
    }
  }

  private handleTaskStatusUpdate(logs: any[]): void {
    for (const log of logs) {
      try {
        const { eventName, args } = decodeEventLog({ abi: SessionQueueV2ABI as Abi, data: log.data, topics: log.topics });
        const { sessionId, taskId } = args as unknown as { sessionId: bigint, taskId: bigint };
        const contextKey = [sessionId.toString(), taskId.toString()].join('-');

        const context = this.taskContextMap.get(contextKey);
        if (!context) continue;

        const { userId, clientReference, chatId } = context;
        const emitter = sseManager.getEmitter(userId);

        if (eventName == 'TaskAssigned') {
          emitter.emit('statusUpdate', {
            clientReference,
            status: 'assigned',
            chatId,
            sessionId: sessionId.toString(),
            taskId: taskId.toString(),
          });
        } else if (eventName == 'TaskAcked') {
          let ackedCount = (context.ackedCount || 0) + 1;
          this.taskContextMap.set(contextKey, { ...context, ackedCount });
          emitter.emit('statusUpdate', {
            clientReference,
            status: 'acked',
            chatId,
            sessionId: sessionId.toString(),
            taskId: taskId.toString(),
            ackedCount, 
            expectedAckedCount: context.session.redundant
          });
        } else if (eventName == 'TaskPrecommitted') {
          let precommitCount = (context.precommitCount || 0) + 1;
          this.taskContextMap.set(contextKey, { ...context, precommitCount });
          emitter.emit('statusUpdate', {
            clientReference,
            status: 'precommitted',
            chatId,
            sessionId: sessionId.toString(),
            taskId: taskId.toString(),
            precommitCount, 
            expectedPrecommitCount: context.session.redundant
          });
        } else if (eventName == 'TaskAllPrecommitted') {
          emitter.emit('statusUpdate', { 
            clientReference,
            status: 'all_precommitted',
            chatId,
            sessionId: sessionId.toString(),
            taskId: taskId.toString(),
          });
        } else if (eventName == 'TaskCommitted') {
          let commitCount = (context.commitCount || 0) + 1;
          this.taskContextMap.set(contextKey, { ...context, commitCount });
          emitter.emit('statusUpdate', {
            clientReference,
            status: 'committed',
            chatId,
            sessionId: sessionId.toString(),
            taskId: taskId.toString(),
            commitCount, 
            expectedCommitCount: context.session.redundant
          });
        } else if (eventName == 'TaskAllCommitted') {
          emitter.emit('statusUpdate', {
            clientReference,
            status: 'all_committed',
            chatId,
            sessionId: sessionId.toString(),
            taskId: taskId.toString(),
          });
        } else if (eventName == 'TaskEnded') {
          this.handleTaskEnded(contextKey);
        }
      } catch (e) {
        console.error("handleTaskStatusUpdate", e);
      }
    }
  }

  private async handleTaskEnded(contextKey: string): Promise<void> {
    const context = this.taskContextMap.get(contextKey);
    if (!context) return;

    const { userId, clientReference, chatId } = context;
    const emitter = sseManager.getEmitter(userId);

    const [miners, results] = await getTaskResult(
      context.sessionId.toString(),
      context.taskId.toString(),
    );

    const content = results?.[0] || "Task completed, but no results were returned.";
    emitter.emit('statusUpdate', {
      clientReference,
      status: 'ended',
      chatId,
      content: cleanBotResponse(content),
      multipleResults: results.map((result, index) => [cleanBotResponse(result), miners[index]].join('---single-content-separator---')).join('---newline-content-separator---'),
      selectedResponseIndex: 0,
      sessionId: context.sessionId.toString(),
      taskId: context.taskId.toString(),
    });
    this.taskContextMap.delete(contextKey);
  }

  private async submitTaskToContract(sessionId: string, promptWithContext: string, clientReference: string): Promise<void> {
    try {
      const contractArgs = [
        BigInt(sessionId), 0, promptWithContext, 1, "",
        [4096, 70, 100, 40, 100, 0, 0],
        clientReference
      ] as const;

      const estimatedGas = await this.publicClient.estimateContractGas({
        account: this.account,
        address: config.contracts.sessionV2.address,
        abi: SessionV2ABI as Abi,
        functionName: 'submit',
        args: contractArgs,
      });

      // Add a 20% buffer to the estimate for safety
      const gasWithBuffer = (estimatedGas * BigInt(120)) / BigInt(100);

      const { request } = await this.publicClient.simulateContract({
        account: this.account,
        address: config.contracts.sessionV2.address,
        abi: SessionV2ABI as Abi,
        functionName: 'submit',
        args: contractArgs,
        gas: gasWithBuffer,
      });

      await this.walletClient.writeContract(request);
    } catch (error) {
      const resolver = this.tempResolverMap.get(clientReference);
      const revertReason = getContractRevertReason(error);

      if (resolver && revertReason) {
        (resolver as any).reject(new Error(revertReason));
        this.tempResolverMap.delete(clientReference);
      } else {
        console.error('Failed to submit task due to a non-contract error.', error);
        throw error;
      }
    }
  }
}

const taskService = new TaskService();
export default taskService;