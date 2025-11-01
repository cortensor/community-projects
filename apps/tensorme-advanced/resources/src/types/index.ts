export interface AssistantResponse {
  content: string;
  minerAddress: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  isError?: boolean;
  status?: 'sending' | 'submitted' | 'assigned' | 'ended' | 'error';
  clientReference?: string;
  timeout?: number;
  onTimeout?: () => void;
  responses?: AssistantResponse[];
  selectedResponseIndex?: number;
  isDone?: boolean;
  isTyping?: boolean;
  thinking?: string | null;
  isThinking?: boolean;
}

export interface SessionConfig {
  modelId: string;
  domainId?: string;
  personaId?: string;
  isMemoryEnabled: boolean;
  isResearchMode: boolean;
}

export interface ChatSession {
  id: string;
  name: string;
  messages: Message[];
  timestamp: number;
  owner?: string;
  isLoading?: boolean;
  loadingMessage?: string;
  lastTaskId?: number;
  lastSessionId?: number;
  historySummary?: string;
  hasMoreMessages?: boolean;
  totalMessageCount?: number;
  messagesOffset?: number;
  config: SessionConfig;
}

export interface ApiRequestBody {
  messages: Pick<Message, 'role' | 'content'>[];
  model: string;
}

export interface ChatCompletionResponse {
  choices: {
    message: {
      role: 'assistant';
      content: string;
    };
  }[];
}

export interface ApiErrorResponse {
  detail?: string | { msg: string; type: string }[];
  message?: string;
}


export interface CompletionRequestBody {
  prompt: string;
  stream?: boolean;
  timeout?: number;
}

export interface Usage {
  completion_tokens: number;
  prompt_tokens: number;
  total_tokens: number;
}

export interface TextCompletionChoice {
  finish_reason: string;
  index: number;
  logprobs: null;
  text: string;
}

export interface TextCompletionResponse {
  choices: TextCompletionChoice[];
  created: number;
  id: string;
  model: string;
  object: 'text_completion';
  usage: Usage;
}


export interface NodeStats {
  dedicated_count: number;
  ephemeral_count: number;
  total_count: number;
}

export interface InfoResponse {
  active_sessions: number;
  address: string;
  ip_address: string;
  name: string;
  node_stats: NodeStats;
  total_sessions: number;
  version: string;
}

export interface StatusResponse {
  active_sessions: number;
  connected_miners: number;
  cpu_usage: number;
  memory_usage: number;
  uptime: number;
}

export interface MinersResponse {
  nodes: Record<string, any>;
  stats: NodeStats;
}

export interface Session {
  active: boolean;
  created_at: number;
  id: string;
  miners_count: number;
  owner: string;
  updated_at: number;
}

export interface SessionsResponse {
  count: number;
  sessions: Session[];
}

export interface RawTask {
  id: bigint;
  sessionId: bigint;
  submitter: `0x${string}`;
  taskData: string;
  timestamp: bigint;
  isCompleted: boolean;
  responseData: string;
}

export interface FormattedTask {
  id: string;
  sessionId: string;
  submitter: `0x${string}`;
  taskData: Record<string, any> | { raw: string };
  timestamp: string;
  isCompleted: boolean;
  responseData: Record<string, any> | { raw: string } | null;
  results: {
    miner: `0x${string}`;
    result: string;
  }[];
}

export interface RawSession {
  id: bigint;
  sid: `0x${string}`;
  name: string;
  metadata: string;
  owner: `0x${string}`;
  state: number;
  createdAt: bigint;
  updatedAt: bigint;
  mode: bigint;
  redundant: bigint;
  minNumOfNodes: bigint;
  maxNumOfNodes: bigint;
  numOfValidatorNodes: bigint;
  ephemeralNodes: any[];
  dedicatedNodes: any[];
  routerMetadatas: any[];
  routerAddresses: any[];
}

export interface FormattedSession {
  id: string;
  sid: `0x${string}`;
  name: string;
  metadata: string;
  owner: `0x${string}`;
  state: number;
  createdAt: string;
  updatedAt: string;
  mode: number;
  redundant: number;
  minNumOfNodes: number;
  maxNumOfNodes: number;
  numOfValidatorNodes: number;
  ephemeralNodes: any[];
  dedicatedNodes: any[];
  routerMetadatas: any[];
  routerAddresses: any[];
}

export interface PersonaConfig {
  id: string;
  name: string;
  description: string;
}
