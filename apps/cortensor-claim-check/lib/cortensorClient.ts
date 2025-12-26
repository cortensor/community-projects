import { CORTENSOR_ROUTER, LLM_PARAMETERS } from '@/config/app';

interface CortensorChoice {
  message?: { content?: string };
  text?: string;
}

interface CortensorCompletionResponse {
  id?: string;
  task_id?: number | string;
  choices?: CortensorChoice[];
  output?: string;
  text?: string;
  error?: { message?: string };
}

export interface CortensorTaskResponse {
  assigned_miners?: string[];
  created_at?: number;
  finished_at?: number;
  results?: {
    data?: string[];
    miners?: string[];
  };
  status?: number;
}

const completionsBase = CORTENSOR_ROUTER.completionsUrl.replace(/\/$/, '');
const completionsEndpointForSession = (sessionId: number) =>
  (/\/\d+$/.test(completionsBase) ? completionsBase : `${completionsBase}/${sessionId}`);

const headers = () => {
  if (!CORTENSOR_ROUTER.apiKey) {
    throw new Error('Missing CORTENSOR_API_KEY environment variable.');
  }

  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${CORTENSOR_ROUTER.apiKey}`,
  } satisfies HeadersInit;
};

const normalizeContent = (payload: CortensorCompletionResponse) => {
  const choice = payload.choices?.[0];
  return choice?.message?.content ?? choice?.text ?? payload.output ?? payload.text ?? '';
};

export async function requestCortensorCompletion(
  prompt: string,
  options?: { sessionId?: number; promptType?: number; clientReference?: string },
): Promise<{
  content: string;
  raw: CortensorCompletionResponse;
  taskId: number;
}> {
  const targetSessionId = options?.sessionId ?? LLM_PARAMETERS.sessionId;
  const body = {
    prompt,
    prompt_type: options?.promptType ?? LLM_PARAMETERS.promptType,
    prompt_template: '',
    stream: false,
    timeout: LLM_PARAMETERS.timeoutSeconds,
    precommit_timeout: 90,
    client_reference: options?.clientReference ?? 'claimcheck-oracle',
    max_tokens: LLM_PARAMETERS.maxTokens,
    temperature: 0.7,
    top_p: 0.95,
    top_k: 40,
    presence_penalty: 0,
    frequency_penalty: 0,
  };

  const response = await fetch(completionsEndpointForSession(targetSessionId), {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify(body),
    cache: 'no-store',
  });

  const json = (await response.json()) as CortensorCompletionResponse;

  if (!response.ok) {
    const message = json.error?.message ?? `Cortensor responded with status ${response.status}.`;
    throw new Error(message);
  }

  const content = normalizeContent(json).trim();
  const taskIdValue = json.task_id;
  const taskId = typeof taskIdValue === 'number' ? taskIdValue : Number(taskIdValue);

  if (!Number.isFinite(taskId)) {
    throw new Error('Cortensor completion did not return a task_id.');
  }

  if (!content) {
    throw new Error('Cortensor completion returned empty content.');
  }

  return { content, raw: json, taskId };
}

const taskEndpointBaseForSession = (sessionId: number) => `${CORTENSOR_ROUTER.baseUrl}/api/v1/tasks/${sessionId}`;

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

async function fetchTaskOnce(taskId: number | string, sessionId: number): Promise<CortensorTaskResponse> {
  const response = await fetch(`${taskEndpointBaseForSession(sessionId)}/${taskId}`, {
    method: 'GET',
    headers: headers(),
    cache: 'no-store',
  });

  if (!response.ok) {
    const message = `Failed to fetch task ${taskId}: ${response.statusText}`;
    throw new Error(message);
  }

  return (await response.json()) as CortensorTaskResponse;
}

export async function fetchTaskSnapshot(
  taskId: number | string,
  options?: { sessionId?: number },
): Promise<CortensorTaskResponse> {
  const sessionId = options?.sessionId ?? LLM_PARAMETERS.sessionId;
  return fetchTaskOnce(taskId, sessionId);
}

export async function waitForTaskResults(
  taskId: number | string,
  options?: { maxAttempts?: number; delayMs?: number; sessionId?: number },
) {
  const { maxAttempts = 8, delayMs = 1500, sessionId = LLM_PARAMETERS.sessionId } = options ?? {};
  let attempt = 0;
  let lastError: Error | undefined;

  while (attempt < maxAttempts) {
    attempt += 1;
    try {
      const task = await fetchTaskOnce(taskId, sessionId);
      const outputs = task.results?.data ?? [];
      const minerCount = (task.results?.miners ?? task.assigned_miners ?? []).length;
      const isComplete =
        outputs.length > 0 &&
        (minerCount === 0
          ? task.status === 4 || Boolean(task.finished_at)
          : outputs.length >= minerCount);

      if (isComplete) {
        return task;
      }
      lastError = undefined;
    } catch (error) {
      lastError = error instanceof Error ? error : new Error('Unknown error polling Cortensor task.');
    }

    await sleep(delayMs);
  }

  if (lastError) {
    throw lastError;
  }

  throw new Error(`Timed out waiting for Cortensor task ${taskId} to finish.`);
}
