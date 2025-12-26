import { CLAIM_CHECK_DEFAULTS } from '@/config/constants';
import { LLM_PARAMETERS, TASK_FETCH_SETTINGS } from '@/config/app';
import { requestCortensorCompletion, waitForTaskResults, fetchTaskSnapshot } from '@/lib/cortensorClient';
import { buildDeepSeekPrompt, buildValidationPrompt } from '@/lib/prompt';
import { searchCitationsWithTavily, summarizeUrlWithTavily } from '@/lib/tavilyClient';
import type { ClaimCheckRequest, ClaimCheckResponse, Citation, MinerVote, Verdict } from '@/types/claimCheck';

const clampRange = (value: number, min: number, max: number) => Math.min(Math.max(value, min), max);
const clamp01 = (value: number) => Math.min(Math.max(value, 0), 1);
const isRecord = (value: unknown): value is Record<string, unknown> => typeof value === 'object' && value !== null;

const isValidHttpUrl = (value?: string | null) => {
  if (!value) return false;
  try {
    const url = new URL(value);
    return url.protocol === 'http:' || url.protocol === 'https:';
  } catch {
    return false;
  }
};

const VERDICT_SCORES: Record<Verdict, number> = {
  true: 1,
  uncertain: 0.5,
  false: 0,
};

const isVerdict = (value: unknown): value is Verdict =>
  typeof value === 'string' && ['true', 'false', 'uncertain'].includes(value.toLowerCase());

const toVerdict = (value: unknown): Verdict => (isVerdict(value) ? ((value as string).toLowerCase() as Verdict) : 'uncertain');

const truncate = (value: string, length = 320) => (value.length > length ? `${value.slice(0, length - 3)}...` : value);

const tryParseJson = (raw: string) => {
  try {
    return JSON.parse(raw);
  } catch {
    const start = raw.indexOf('{');
    const end = raw.lastIndexOf('}');
    if (start !== -1 && end !== -1 && end > start) {
      try {
        return JSON.parse(raw.slice(start, end + 1));
      } catch {
        return null;
      }
    }
    return null;
  }
};

const formatTavilyEvidence = (citations: Citation[]) => {
  if (!citations.length) return null;
  return citations
    .slice(0, 5)
    .map((citation) => {
      const description = citation.description ? truncate(citation.description, 220) : null;
      const link = citation.url ? ` (${citation.url})` : '';
      return `- ${citation.source}${link}${description ? ` — ${description}` : ''}`;
    })
    .join('\n');
};

const logInfo = (...args: unknown[]) => {
  if (process.env.NODE_ENV !== 'test') {
    // eslint-disable-next-line no-console
    console.info(...args);
  }
};

const normalizeCitations = (value: unknown): Citation[] => {
  if (!Array.isArray(value)) return [];
  return value
    .map((item, idx) => {
      if (!isRecord(item)) return null;
      const source = typeof item.source === 'string' && item.source.trim() ? item.source.trim() : `Source ${idx + 1}`;
      const url = typeof item.url === 'string' && item.url.trim() ? item.url.trim() : null;
      if (!isValidHttpUrl(url)) return null;
      const description = typeof item.description === 'string' && item.description.trim() ? item.description.trim() : null;
      return { source, url, description } satisfies Citation;
    })
    .filter(Boolean) as Citation[];
};

const fetchTavilyCitations = async (claim: string): Promise<Citation[]> => {
  if (!claim?.trim()) return [];
  const results = await searchCitationsWithTavily(claim);
  return results
    .map((item, idx) => {
      const url = typeof item.url === 'string' ? item.url.trim() : null;
      if (!isValidHttpUrl(url)) return null;
      const source = typeof item.source === 'string' && item.source.trim() ? item.source.trim() : `Tavily result ${idx + 1}`;
      const description = typeof item.description === 'string' && item.description.trim() ? truncate(item.description.trim(), 220) : null;
      return { source, url, description } satisfies Citation;
    })
    .filter(Boolean) as Citation[];
};

const dedupeCitations = (citations: Citation[]) => {
  const map = new Map<string, Citation>();
  citations.forEach((citation) => {
    const key = `${citation.source}::${citation.url ?? 'null'}`;
    if (!map.has(key)) {
      map.set(key, citation);
    }
  });
  return Array.from(map.values());
};

const getHostname = (value?: string | null) => {
  if (!value) return null;
  try {
    return new URL(value).hostname.toLowerCase();
  } catch {
    return null;
  }
};

const rankHostQuality = (hostname: string | null) => {
  if (!hostname) return -1;
  if (hostname.endsWith('.gov')) return 5;
  if (hostname.endsWith('.edu')) return 4;
  if (hostname.endsWith('.org')) return 3;
  const trustedNews = ['reuters.com', 'apnews.com', 'bbc.com', 'nytimes.com', 'washingtonpost.com', 'theguardian.com'];
  if (trustedNews.some((domain) => hostname === domain || hostname.endsWith(`.${domain}`))) {
    return 2.5;
  }
  return 1;
};

const curateCitations = (citations: Citation[], limit = 3, minQuality = 1.5) => {
  return citations
    .map((citation, idx) => {
      const hostname = getHostname(citation.url);
      const quality = rankHostQuality(hostname) + (citation.description ? 0.5 : 0);
      return { citation, quality, idx };
    })
    .filter((item) => item.quality >= minQuality)
    .sort((a, b) => {
      if (b.quality !== a.quality) return b.quality - a.quality;
      return a.idx - b.idx;
    })
    .slice(0, limit)
    .map((item) => item.citation);
};

const isValidationVerdict = (value: unknown): value is NonNullable<ClaimCheckResponse['validation']>['verdict'] =>
  typeof value === 'string' && ['normal', 'abnormal', 'inconclusive'].includes(value.toLowerCase());

interface MinerAssessment {
  minerId: string;
  verdict: Verdict;
  confidence: number;
  dispersion: number;
  reasoning: string;
  citations: Citation[];
  parsedOk: boolean;
}

const stripCodeFences = (value: string) => value.replace(/^```(?:json)?/i, '').replace(/```$/i, '');

const stripSentenceMarkers = (value: string) => value.replace(/<\uff5c[^>]+>$/gi, '').trim();

const sliceToJsonObject = (value: string) => {
  const start = value.indexOf('{');
  if (start === -1) return value.trim();
  let depth = 0;
  for (let idx = start; idx < value.length; idx += 1) {
    const char = value[idx];
    if (char === '{') depth += 1;
    if (char === '}') {
      depth -= 1;
      if (depth === 0) {
        return value.slice(start, idx + 1);
      }
    }
  }
  return value.slice(start).trim();
};

const extractVisibleJson = (raw: string) => {
  const trimmed = raw.trim();
  const closingTag = '</think>';
  const afterThink = trimmed.includes(closingTag) ? trimmed.split(closingTag).pop() ?? '' : trimmed;
  const cleaned = stripSentenceMarkers(stripCodeFences(afterThink.trim() || trimmed));
  return sliceToJsonObject(cleaned);
};

const parseMinerPayload = (raw: string, minerId: string, fallbackIndex: number): MinerAssessment => {
  const visiblePayload = extractVisibleJson(raw);
  const parsed = tryParseJson(visiblePayload);
  const fallbackReason = truncate(
    visiblePayload.trim() || 'Miner response could not be parsed into JSON. Returning uncertain verdict.',
    320,
  );

  if (!parsed || !isRecord(parsed)) {
    return {
      minerId: minerId || `miner_${fallbackIndex + 1}`,
      verdict: 'uncertain',
      confidence: 0.33,
      dispersion: 0.5,
      reasoning: fallbackReason,
      citations: [],
      parsedOk: false,
    };
  }

  const verdict = toVerdict(parsed.verdict);
  const confidence = clamp01(Number(parsed.confidence ?? 0.5));
  const dispersion = clamp01(Number(parsed.dispersion ?? 0.5));
  const reasoning =
    typeof parsed.reasoning === 'string' && parsed.reasoning.trim()
      ? parsed.reasoning.trim()
      : fallbackReason;
  const citations = normalizeCitations(parsed.citations);

  return {
    minerId: minerId || `miner_${fallbackIndex + 1}`,
    verdict,
    confidence: Number(confidence.toFixed(2)),
    dispersion: Number(dispersion.toFixed(2)),
    reasoning,
    citations,
    parsedOk: true,
  } satisfies MinerAssessment;
};

const parseValidationPayload = (raw: string, defaultNotes: string): NonNullable<ClaimCheckResponse['validation']> => {
  const visiblePayload = extractVisibleJson(raw);
  const parsed = tryParseJson(visiblePayload);
  const notes = truncate(visiblePayload.trim() || defaultNotes, 320);

  if (!parsed || !isRecord(parsed)) {
    return { verdict: 'inconclusive', score: 0, notes };
  }

  const verdict = isValidationVerdict(parsed.verdict)
    ? (parsed.verdict as NonNullable<ClaimCheckResponse['validation']>['verdict'])
    : 'inconclusive';
  const scoreRaw = Number((parsed as Record<string, unknown>).score);
  const score = Number.isFinite(scoreRaw) ? Math.min(Math.max(Math.round(scoreRaw), 0), 10) : 0;
  const validationNotes = typeof parsed.notes === 'string' && parsed.notes.trim() ? parsed.notes.trim() : notes;

  return { verdict, score, notes: validationNotes };
};

const computeDispersionFromAssessments = (assessments: MinerAssessment[]) => {
  if (assessments.length <= 1) {
    return assessments[0]?.dispersion ?? 0.5;
  }
  const scores = assessments.map((assessment) => VERDICT_SCORES[assessment.verdict]);
  return Math.max(...scores) - Math.min(...scores);
};

const assembleResponse = (assessments: MinerAssessment[], tavilyCitations: Citation[]): ClaimCheckResponse => {
  if (!assessments.length) {
    return {
      verdict: 'uncertain',
      confidence: 0.3,
      dispersion: 0.5,
      reasoning: 'No miner outputs were returned by Cortensor.',
      citations: curateCitations(dedupeCitations(tavilyCitations)),
      miner_votes: [
        {
          miner_id: 'miner_fallback',
          verdict: 'uncertain',
          confidence: 0.3,
          notes: 'Missing miner outputs',
        },
      ],
    } satisfies ClaimCheckResponse;
  }

  const sorted = assessments.slice().sort((a, b) => b.confidence - a.confidence);
  const primary = sorted[0];
  const combinedCitations = dedupeCitations([
    ...tavilyCitations,
    ...assessments.flatMap((item) => item.citations),
  ]);
  const dispersion = Number(clamp01(primary.dispersion ?? computeDispersionFromAssessments(assessments)).toFixed(2));

  return {
    verdict: primary.verdict,
    confidence: Number(primary.confidence.toFixed(2)),
    dispersion,
    reasoning: primary.reasoning,
    citations: curateCitations(combinedCitations),
    miner_votes: assessments.map((assessment) => ({
      miner_id: assessment.minerId,
      verdict: assessment.verdict,
      confidence: assessment.confidence,
      notes: assessment.reasoning,
      citations: assessment.citations,
    })),
  } satisfies ClaimCheckResponse;
};

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

const buildAssessments = (outputs: string[], addresses: string[]) => {
  const maxLength = Math.max(outputs.length, addresses.length);
  const list: MinerAssessment[] = [];
  for (let idx = 0; idx < maxLength; idx += 1) {
    const raw = outputs[idx];
    if (raw === undefined || raw === null || `${raw}`.trim() === '') {
      continue; // skip miners with no payload in final display
    }
    list.push(parseMinerPayload(raw, addresses[idx] ?? `miner_${idx + 1}`, idx));
  }
  return list;
};

const VALIDATION_TIMEOUT_MS = 75_000;

const runValidationAgent = async (params: {
  claim: string;
  contextText?: string | null;
  contextUrl?: string | null;
  assessment: ClaimCheckResponse;
  clientReference?: string | null;
}): Promise<NonNullable<ClaimCheckResponse['validation']> | null> => {
  const validationSession = LLM_PARAMETERS.validationSessionId;
  if (!Number.isFinite(validationSession) || validationSession <= 0) {
    return {
      verdict: 'inconclusive',
      score: 0,
      notes: 'Validation session is not configured. Set NEXT_PUBLIC_VALIDATION_SESSION_ID.',
    };
  }

  const { claim, contextText, contextUrl, assessment, clientReference } = params;
  const prompt = buildValidationPrompt({
    claim,
    contextText,
    contextUrl,
    agentOutput: JSON.stringify(assessment, null, 2),
  });

  const fallbackNotes = 'Validation agent could not evaluate the assessment payload.';

  try {
    logInfo('[Validation] start', { validationSession, claim: truncate(claim, 120) });
    const { taskId } = await requestCortensorCompletion(prompt, {
      sessionId: validationSession,
      clientReference: clientReference ?? undefined,
    });
    const taskOrTimeout = await Promise.race([
      waitForTaskResults(taskId, { maxAttempts: 6, delayMs: 1500, sessionId: validationSession }).then((t) => ({
        task: t,
        timedOut: false,
      })),
      sleep(VALIDATION_TIMEOUT_MS).then(() => ({ task: null, timedOut: true })),
    ]);

    if (taskOrTimeout.timedOut || !taskOrTimeout.task) {
      logInfo('[Validation] timeout', { taskId, validationSession });
      return {
        verdict: 'inconclusive',
        score: 0,
        notes: 'Validation agent did not finish within 75 seconds. Please check the validation dashboard.',
        task_id: taskId,
        session_id: validationSession,
        status: 'timeout',
      };
    }

    const task = taskOrTimeout.task;
    const raw = task.results?.data?.[0] ?? '';
    if (!raw) {
      logInfo('[Validation] empty response', { taskId, validationSession });
      return {
        verdict: 'inconclusive',
        score: 0,
        notes: 'Validation agent returned no content.',
        task_id: taskId,
        session_id: validationSession,
        status: 'error',
      };
    }
    const parsed = parseValidationPayload(raw, fallbackNotes);
    logInfo('[Validation] done', { taskId, validationSession, verdict: parsed.verdict, score: parsed.score });
    return { ...parsed, task_id: taskId, session_id: validationSession, status: 'ok' };
  } catch (error) {
    const message = error instanceof Error ? error.message : fallbackNotes;
    logInfo('[Validation] error', { validationSession, error: message });
    return {
      verdict: 'inconclusive',
      score: 0,
      notes: truncate(message, 240),
      task_id: undefined,
      session_id: validationSession,
      status: 'error',
    };
  }
};

export async function runClaimCheck(request: ClaimCheckRequest): Promise<ClaimCheckResponse> {
  const { claim, context_text, context_url, client_reference = null } = request;
  if (!claim?.trim()) {
    throw new Error('Claim must not be empty.');
  }

  const requestedMiners = request.num_miners ?? CLAIM_CHECK_DEFAULTS.NUM_MINERS;
  const numMiners = clampRange(
    Math.round(requestedMiners),
    CLAIM_CHECK_DEFAULTS.MIN_MINERS,
    CLAIM_CHECK_DEFAULTS.MAX_MINERS,
  );

  const tavilyCitations = await fetchTavilyCitations(claim);
  const tavilyEvidence = formatTavilyEvidence(tavilyCitations);

  let hydratedContext = context_text ?? undefined;

  if (!hydratedContext && context_url) {
    hydratedContext = (await summarizeUrlWithTavily(context_url)) ?? undefined;
  }

  const prompt = buildDeepSeekPrompt({
    claim,
    contextUrl: context_url ?? undefined,
    contextText: hydratedContext,
    tavilyEvidence: tavilyEvidence ?? undefined,
    numMiners,
  });

  logInfo('[ClaimCheck] start', {
    claim: truncate(claim, 120),
    numMiners,
    hasContextText: Boolean(hydratedContext),
    hasContextUrl: Boolean(context_url),
    tavilyCitations: tavilyCitations.length,
  });

  const { taskId } = await requestCortensorCompletion(prompt, {
    clientReference: client_reference ?? undefined,
  });
  logInfo('[ClaimCheck] task dispatched', { taskId, sessionId: LLM_PARAMETERS.sessionId, numMiners });

  let task = await waitForTaskResults(taskId, { maxAttempts: 10, delayMs: 2000 });

  const ensureMinerResults = async (currentTask: typeof task) => {
    let snapshot = currentTask;
    let attempts = 0;
    const required = Math.max(1, TASK_FETCH_SETTINGS.requiredMinerResults);

    const targetCount = () => {
      const reportedMiners = snapshot.results?.miners ?? [];
      const assignedMiners = snapshot.assigned_miners ?? [];
      const declared = Math.max(reportedMiners.length, assignedMiners.length);
      return Math.max(required, declared);
    };

    while ((snapshot.results?.data?.length ?? 0) < targetCount() && attempts < TASK_FETCH_SETTINGS.taskDetailsRetryAttempts) {
      attempts += 1;
      await sleep(TASK_FETCH_SETTINGS.taskDetailsRetryDelayMs);
      snapshot = await fetchTaskSnapshot(taskId, { sessionId: LLM_PARAMETERS.sessionId });
    }
    return snapshot;
  };

  task = await ensureMinerResults(task);

  const minerOutputs = task.results?.data ?? [];
  const minerAddresses = (() => {
    const reported = task.results?.miners ?? [];
    const assigned = task.assigned_miners ?? [];
    return reported.length >= assigned.length ? reported : assigned;
  })();
  logInfo('[ClaimCheck] task completed', {
    taskId,
    minersReturned: minerOutputs.length,
    minersAssigned: minerAddresses.length,
  });

  const assessmentsInitial = buildAssessments(minerOutputs, minerAddresses);
  const assembledInitial = assembleResponse(assessmentsInitial, tavilyCitations);
  const hasParsableMiner = assessmentsInitial.some((assessment) => assessment.parsedOk);

  const validation = hasParsableMiner
    ? await runValidationAgent({
        claim,
        contextUrl: context_url,
        contextText: hydratedContext,
        assessment: assembledInitial,
        clientReference: client_reference,
      })
    : null;

  // Refresh task details after validation to capture late miner results
  const finalSnapshot = await fetchTaskSnapshot(taskId, { sessionId: LLM_PARAMETERS.sessionId });
  const finalOutputs = finalSnapshot.results?.data ?? minerOutputs;
  const finalAddresses = (() => {
    const reported = finalSnapshot.results?.miners ?? [];
    const assigned = finalSnapshot.assigned_miners ?? minerAddresses;
    const resolved = reported.length >= assigned.length ? reported : assigned;
    return resolved.length ? resolved : minerAddresses;
  })();
  const assessmentsFinal = buildAssessments(finalOutputs, finalAddresses);

  const assembledFinal = assessmentsFinal.length
    ? assembleResponse(assessmentsFinal, tavilyCitations)
    : assembledInitial;

  const finalResponse = validation ? { ...assembledFinal, validation } : assembledFinal;
  return { ...finalResponse, task_id: taskId } satisfies ClaimCheckResponse;
}
