'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import type { ClaimCheckResponse, Verdict, Citation } from '@/types/claimCheck';

const verdictPalette: Record<Verdict, string> = {
  true: '#0f8b0d',
  false: '#c43b1d',
  uncertain: '#b37a00',
};

const validationPalette: Record<NonNullable<ClaimCheckResponse['validation']>['verdict'], string> = {
  normal: '#0f8b0d',
  abnormal: '#c43b1d',
  inconclusive: '#b37a00',
};

const verdictLabel: Record<Verdict, string> = {
  true: 'TRUE',
  false: 'FALSE',
  uncertain: 'UNCERTAIN',
};

const validationLabel: Record<NonNullable<ClaimCheckResponse['validation']>['verdict'], string> = {
  normal: 'VALIDATION NORMAL',
  abnormal: 'VALIDATION ABNORMAL',
  inconclusive: 'VALIDATION INCONCLUSIVE',
};

type ClaimFormState = {
  claim: string;
  context_url: string;
  context_text: string;
};

type HistoryItem = {
  claim: string;
  verdict: Verdict;
  confidence: number;
  timestamp: number;
};

const initialForm: ClaimFormState = {
  claim: '',
  context_url: '',
  context_text: '',
};

type LoadingStatus = 'pending' | 'active' | 'done' | 'error';

type LoadingStep = {
  id: string;
  label: string;
  percent: number;
  status: LoadingStatus;
};

const DETAIL_BUFFER_DURATION_MS = 5_000;
const DETAIL_BUFFER_SECONDS = DETAIL_BUFFER_DURATION_MS / 1000;
const CLIENT_REF_PREFIX = process.env.NEXT_PUBLIC_CLIENT_REF_PREFIX || 'user-claimcheck';

const BASE_LOADING_STEPS: Array<Omit<LoadingStep, 'status'>> = [
  { id: 'queue', label: 'ClaimCheck: submitting task to Cortensor router', percent: 5 },
  { id: 'dispatch', label: 'ClaimCheck: task dispatched to miners', percent: 20 },
  { id: 'collect', label: 'ClaimCheck: awaiting miner outputs', percent: 45 },
  { id: 'analysis', label: 'ClaimCheck: miner outputs received', percent: 60 },
  { id: 'metrics', label: 'ClaimCheck: assembling verdict & citations', percent: 75 },
  { id: 'finalize', label: 'Validation: starting validation task', percent: 86 },
  { id: 'validation', label: 'Validation: running check (may take longer)', percent: 95 },
  { id: 'detail-buffer', label: 'Holding 5s for miner detail sync', percent: 99 },
];

const LOADING_STATUS_COPY: Record<LoadingStatus, string> = {
  pending: 'Queued',
  active: 'In progress',
  done: 'Complete',
  error: 'Needs attention',
};

const setStepState = (
  steps: Array<Omit<LoadingStep, 'status'>> | LoadingStep[],
  activeIndex: number,
  status: LoadingStatus = 'active',
): LoadingStep[] =>
  steps.map((step, idx) => {
    const baseStep = { ...step, status: 'pending' as LoadingStatus };
    if (idx < activeIndex) return { ...baseStep, status: 'done' };
    if (idx === activeIndex) return { ...baseStep, status };
    return baseStep;
  });

const getOrdinal = (value: number) => {
  const remainder100 = value % 100;
  if (remainder100 >= 11 && remainder100 <= 13) {
    return `${value}th`;
  }
  const remainder10 = value % 10;
  if (remainder10 === 1) return `${value}st`;
  if (remainder10 === 2) return `${value}nd`;
  if (remainder10 === 3) return `${value}rd`;
  return `${value}th`;
};

const formatMinerOrder = (index: number) => getOrdinal(index + 1);
const getHostname = (value?: string | null) => {
  if (!value) return null;
  try {
    const hostname = new URL(value).hostname.replace(/^www\./i, '');
    return hostname || null;
  } catch {
    return null;
  }
};

const formatCitationLabel = (citation: Citation) => citation.source?.trim() || 'Citation';
const HISTORY_KEY = 'claimcheck_history';
const truncateClaim = (value: string, length = 80) => (value.length > length ? `${value.slice(0, length - 3)}...` : value);
const isValidHttpUrl = (value?: string | null) => {
  if (!value) return false;
  try {
    const url = new URL(value);
    return url.protocol === 'http:' || url.protocol === 'https:';
  } catch {
    return false;
  }
};

const formatMinerId = (value?: string | null) => {
  if (!value) return 'unknown';
  const trimmed = value.trim();
  if (trimmed.length <= 10) return trimmed;
  return `${trimmed.slice(0, 6)}...${trimmed.slice(-4)}`;
};

export default function ClaimCheckPage() {
  const [form, setForm] = useState(initialForm);
  const [result, setResult] = useState<ClaimCheckResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [loadingSteps, setLoadingSteps] = useState<LoadingStep[]>(
    BASE_LOADING_STEPS.map((step, idx) => ({ ...step, status: idx === 0 ? 'active' : 'pending' })),
  );
  const loadingTimersRef = useRef<Array<ReturnType<typeof setTimeout>>>([]);
  const [expandedMiners, setExpandedMiners] = useState<Record<string, boolean>>({});
  const detailHoldTimersRef = useRef<{
    countdown?: ReturnType<typeof setInterval>;
    gate?: ReturnType<typeof setTimeout>;
    release?: () => void;
  }>({});
  const [detailHoldRemaining, setDetailHoldRemaining] = useState(0);
  const [isDetailHoldActive, setIsDetailHoldActive] = useState(false);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [theme, setTheme] = useState<'light' | 'dark'>('light');
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [userId, setUserId] = useState<string | null>(null);
  const [clientReference, setClientReference] = useState<string | null>(null);

  const verdictColor = useMemo(() => (result ? verdictPalette[result.verdict] : '#1f2933'), [result]);
  const dashboardUrl = useMemo(() => {
    if (!result?.task_id) return null;
    const sessionId = process.env.NEXT_PUBLIC_SESSION_ID;
    if (!sessionId) return null;
    return `https://dashboard-testnet0.cortensor.network/session/${sessionId}/${result.task_id}`;
  }, [result?.task_id]);

  const displayUserId = useMemo(() => {
    if (!clientReference) return null;
    return clientReference.replace(/^user-/, '');
  }, [clientReference]);

  const validationDashboardUrl = useMemo(() => {
    if (!result?.validation?.task_id) return null;
    const validationSession = process.env.NEXT_PUBLIC_VALIDATION_SESSION_ID ?? process.env.NEXT_PUBLIC_SESSION_ID;
    if (!validationSession) return null;
    return `https://dashboard-testnet0.cortensor.network/session/${validationSession}/${result.validation.task_id}`;
  }, [result?.validation?.task_id]);

  const headerChips = useMemo(() => {
    const chips: Array<{ label: string; value: string }> = [];
    if (displayUserId) chips.push({ label: 'UserID', value: displayUserId });
    if (process.env.NEXT_PUBLIC_SESSION_ID) {
      chips.push({ label: 'Session', value: String(process.env.NEXT_PUBLIC_SESSION_ID) });
    }
    if (result?.task_id) chips.push({ label: 'Task', value: String(result.task_id) });
    if (result?.validation?.task_id && (process.env.NEXT_PUBLIC_VALIDATION_SESSION_ID || process.env.NEXT_PUBLIC_SESSION_ID)) {
      chips.push({ label: 'Validation', value: `${process.env.NEXT_PUBLIC_VALIDATION_SESSION_ID ?? process.env.NEXT_PUBLIC_SESSION_ID}/${result.validation.task_id}` });
    }
    return chips;
  }, [displayUserId, result?.task_id, result?.validation?.task_id]);

  const activeStep = useMemo(() => {
    const total = loadingSteps.length;
    const idx = Math.min(currentStepIndex, total - 1);
    return loadingSteps[idx];
  }, [currentStepIndex, loadingSteps]);

  const ribbon = useMemo(() => {
    if (isLoading) return { text: 'Running claim & validation', tone: 'info' } as const;
    if (error) return { text: 'Needs attention', tone: 'error' } as const;
    if (result?.validation?.status === 'timeout') return { text: 'Validation timed out', tone: 'warn' } as const;
    if (result?.validation?.status === 'error') return { text: 'Validation error', tone: 'warn' } as const;
    if (result) return { text: 'Complete', tone: 'success' } as const;
    return null;
  }, [isLoading, error, result]);

  const clearLoadingTimers = () => {
    loadingTimersRef.current.forEach(clearTimeout);
    loadingTimersRef.current = [];
  };

  const clearDetailHoldTimers = () => {
    if (detailHoldTimersRef.current.countdown) {
      clearInterval(detailHoldTimersRef.current.countdown);
    }
    if (detailHoldTimersRef.current.gate) {
      clearTimeout(detailHoldTimersRef.current.gate);
    }
    detailHoldTimersRef.current.release = undefined;
    detailHoldTimersRef.current = {};
  };

  const resetDetailHoldState = () => {
    clearDetailHoldTimers();
    setIsDetailHoldActive(false);
    setDetailHoldRemaining(0);
  };

  const resetLoadingState = () => {
    clearLoadingTimers();
    resetDetailHoldState();
    setLoadingSteps(setStepState(BASE_LOADING_STEPS, 0));
    setCurrentStepIndex(0);
  };

  const setActiveStep = (index: number, status: LoadingStatus = 'active') => {
    setCurrentStepIndex(index);
    setLoadingSteps((prev) => setStepState(prev, index, status));
  };

  const markValidationReady = () => {
    setCurrentStepIndex(6);
    setLoadingSteps((prev) => setStepState(prev, 6, 'done'));
  };

  const scheduleFallbackProgression = () => {
    const timers: Array<ReturnType<typeof setTimeout>> = [];
    const steps = [
      { idx: 2, delay: 8000 }, // awaiting miner outputs
      { idx: 3, delay: 16000 }, // miner outputs received
      { idx: 4, delay: 24000 }, // assembling verdict
      { idx: 5, delay: 32000 }, // validation starting
      { idx: 6, delay: 40000 }, // validation running
    ];

    steps.forEach(({ idx, delay }) => {
      const t = setTimeout(() => {
        setLoadingSteps((prev) => {
          const currentActive = prev.findIndex((step) => step.status === 'active');
          const currentIndex = currentActive === -1 ? currentStepIndex : currentActive;
          if (currentIndex >= idx) return prev;
          return setStepState(prev, idx, idx === 6 ? 'active' : 'active');
        });
        setCurrentStepIndex((prev) => (prev >= idx ? prev : idx));
      }, delay);
      timers.push(t);
    });

    loadingTimersRef.current.push(...timers);
  };

  const rampToValidationDone = () => {
    clearLoadingTimers();
    const timers: Array<ReturnType<typeof setTimeout>> = [];
    const schedule = [
      { idx: 2, delay: 0 },
      { idx: 3, delay: 350 },
      { idx: 4, delay: 700 },
      { idx: 5, delay: 1050 },
      { idx: 6, delay: 1400 },
    ];
    schedule.forEach(({ idx, delay }) => {
      const t = setTimeout(() => setActiveStep(idx, idx === 6 ? 'done' : 'active'), delay);
      timers.push(t);
    });
    loadingTimersRef.current = timers;
  };

  const activateDetailHoldStep = () => {
    setCurrentStepIndex(BASE_LOADING_STEPS.length - 1);
    setLoadingSteps((prev) =>
      prev.map((step, idx) => {
        if (idx < prev.length - 1) {
          return { ...step, status: 'done' };
        }
        return { ...step, status: 'active' };
      }),
    );
  };

  const holdForMinerDetails = () =>
    new Promise<void>((resolve) => {
      activateDetailHoldStep();
      resetDetailHoldState();
      setIsDetailHoldActive(true);
      setDetailHoldRemaining(DETAIL_BUFFER_SECONDS);
      detailHoldTimersRef.current.release = () => {
        clearDetailHoldTimers();
        setIsDetailHoldActive(false);
        setDetailHoldRemaining(0);
        resolve();
      };

      detailHoldTimersRef.current.countdown = setInterval(() => {
        setDetailHoldRemaining((prev) => {
          if (prev <= 1) {
            if (detailHoldTimersRef.current.countdown) {
              clearInterval(detailHoldTimersRef.current.countdown);
              detailHoldTimersRef.current.countdown = undefined;
            }
            return 0;
          }
          return prev - 1;
        });
      }, 1000);

      detailHoldTimersRef.current.gate = setTimeout(() => {
        detailHoldTimersRef.current.release?.();
      }, DETAIL_BUFFER_DURATION_MS);
    });

  const completeLoadingSteps = (status: LoadingStatus = 'done') => {
    clearLoadingTimers();
    clearDetailHoldTimers();
    setIsDetailHoldActive(false);
    setDetailHoldRemaining(0);
    setCurrentStepIndex(BASE_LOADING_STEPS.length - 1);
    setLoadingSteps((prev) =>
      prev.map((step, idx) => {
        if (status === 'error' && idx === prev.length - 1) {
          return { ...step, status: 'error' };
        }
        return { ...step, status: 'done' };
      }),
    );
  };

  useEffect(() => () => {
    clearLoadingTimers();
    clearDetailHoldTimers();
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    if (theme === 'dark') {
      root.classList.add('theme-dark');
    } else {
      root.classList.remove('theme-dark');
    }
  }, [theme]);

  useEffect(() => {
    const key = 'claimcheck_user_id';
    const generateUserId = () => {
      if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
        return (crypto.randomUUID() as string).replace(/-/g, '').slice(-10);
      }
      return Math.random().toString(36).slice(2, 10);
    };

    try {
      const existing = localStorage.getItem(key);
      const id = existing && existing.trim() ? existing.trim() : generateUserId();
      localStorage.setItem(key, id);
      setUserId(id);
      setClientReference(`${CLIENT_REF_PREFIX}-${id}`);
    } catch {
      const id = generateUserId();
      setUserId(id);
      setClientReference(`${CLIENT_REF_PREFIX}-${id}`);
    }
  }, []);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(HISTORY_KEY);
      if (stored) {
        const parsed = JSON.parse(stored) as HistoryItem[];
        if (Array.isArray(parsed)) {
          setHistory(parsed.slice(0, 12));
        }
      }
    } catch {
      setHistory([]);
    }
  }, []);

  const persistHistory = (items: HistoryItem[]) => {
    try {
      localStorage.setItem(HISTORY_KEY, JSON.stringify(items));
    } catch {
      // ignore storage errors
    }
  };

  const addHistoryItem = (item: HistoryItem) => {
    setHistory((prev) => {
      const next = [item, ...prev].slice(0, 12);
      persistHistory(next);
      return next;
    });
  };

  const clearHistory = () => {
    setHistory([]);
    try {
      localStorage.removeItem(HISTORY_KEY);
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    if (!result?.miner_votes?.length) {
      setExpandedMiners({});
      return;
    }

    setExpandedMiners(
      result.miner_votes.reduce((acc, vote, idx) => {
        acc[vote.miner_id] = idx === 0;
        return acc;
      }, {} as Record<string, boolean>),
    );
  }, [result]);

  const handleChange = (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value } as ClaimFormState));
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsLoading(true);
    setError(null);
    setResult(null);
    resetLoadingState();
    const dispatchTimer = setTimeout(() => {
      setActiveStep(1);
    }, 600);
    loadingTimersRef.current = [dispatchTimer];
    scheduleFallbackProgression();

    try {
      const response = await fetch('/api/claim-check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          claim: form.claim,
          context_url: form.context_url || null,
          context_text: form.context_text || null,
          client_reference: clientReference ?? `${CLIENT_REF_PREFIX}-${userId ?? 'anon'}`,
        }),
      });

      const json = await response.json();

      if (!response.ok) {
        throw new Error(json.error || 'Failed to check claim.');
      }

      const hydratedResult = json as ClaimCheckResponse;
      rampToValidationDone();
      await holdForMinerDetails();
      setResult(hydratedResult);
      addHistoryItem({
        claim: form.claim,
        verdict: hydratedResult.verdict,
        confidence: hydratedResult.confidence,
        timestamp: Date.now(),
      });
      completeLoadingSteps('done');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unexpected error.');
      completeLoadingSteps('error');
    } finally {
      setIsLoading(false);
    }
  };

  const renderStatus = () => {
    if (isLoading) return <p className="status">Checking claim...</p>;
    if (error) return <p className="status status-error">{error}</p>;
    return null;
  };

  const formatPercent = (value?: number) => (value === undefined ? '—' : `${Math.round(value * 100)}%`);

  const citations: ClaimCheckResponse['citations'] = result?.citations ?? [];
  const minerVotes: NonNullable<ClaimCheckResponse['miner_votes']> = result?.miner_votes ?? [];
  const validation = result?.validation ?? null;

  const toggleMinerVisibility = (minerId: string) => {
    setExpandedMiners((prev) => ({ ...prev, [minerId]: !prev[minerId] }));
  };

  const buildMinerHeading = (index: number) => `Result from miner ${formatMinerOrder(index)}`;

  const formatStepStatusText = (step: LoadingStep) => {
    if (step.id === 'detail-buffer' && isDetailHoldActive && detailHoldRemaining > 0) {
      return `${detailHoldRemaining}s remaining`;
    }
    return LOADING_STATUS_COPY[step.status];
  };

  const formatStepLabel = (step: LoadingStep) => {
    if (step.id === 'detail-buffer' && detailHoldRemaining > 0) {
      return `Holding ${detailHoldRemaining}s for miner detail sync`;
    }
    if (step.id === 'analysis' && step.status === 'done') {
      return 'ClaimCheck: miner outputs received';
    }
    if (step.id === 'metrics' && step.status === 'done') {
      return 'ClaimCheck: assembling verdict & citations';
    }
    if (step.id === 'finalize' && step.status === 'done') {
      return 'Validation: starting validation task';
    }
    return step.label;
  };

  const renderLoadingChat = () => {
    const totalSteps = loadingSteps.length;
    const safeIndex = Math.min(currentStepIndex, totalSteps - 1);
    const activeStep = loadingSteps[safeIndex];
    const stepsToDisplay = loadingSteps
      .map((step, idx) => ({ ...step, order: idx }))
      .filter((step) => step.order <= safeIndex && step.order >= Math.max(0, safeIndex - 2));

    return (
      <div className="loading-chat" aria-live="polite">
        <div className="loading-progress">
          <div className="loading-progress-fill" style={{ width: `${activeStep?.percent ?? 0}%` }} />
        </div>
        <div className="loading-feed">
          {stepsToDisplay.map((step) => (
            <div key={step.id} className={`loading-feed-item ${step.status}`}>
              <div className="loading-feed-meta">
                <span className="loading-feed-step">Step {step.order + 1} of {totalSteps}</span>
                <span className="loading-feed-status">
                  {step.status === 'active' && <span className="pulse-dot" aria-hidden />}
                  {formatStepStatusText(step)}
                </span>
              </div>
              <p className="loading-feed-label">{formatStepLabel(step)}</p>
            </div>
          ))}
          {isDetailHoldActive && (
            <button className="partial-button" type="button" onClick={() => detailHoldTimersRef.current.release?.()}>
              View partial results now
            </button>
          )}
        </div>
      </div>
    );
  };

  const renderSkeletons = () => (
    <div className="skeleton-grid" aria-hidden="true">
      <div className="skeleton-card">
        <div className="skeleton-line wide" />
        <div className="skeleton-line" />
        <div className="skeleton-line short" />
      </div>
      <div className="skeleton-card">
        <div className="skeleton-line wide" />
        <div className="skeleton-line" />
        <div className="skeleton-line short" />
      </div>
    </div>
  );

  const renderMinerDetails = () => {
    if (!minerVotes.length) {
      return null;
    }

    const expandAll = () => {
      setExpandedMiners(
        minerVotes.reduce((acc, vote) => {
          acc[vote.miner_id] = true;
          return acc;
        }, {} as Record<string, boolean>),
      );
    };

    const collapseAll = () => {
      setExpandedMiners({});
    };

    return (
      <section className="detail-block">
        <div className="detail-block-header">
          <h3>Miner task detail</h3>
          <div className="miner-controls">
            <p className="muted">{"Trace each miner's reasoning trail and the citations they surfaced."}</p>
            <div className="miner-actions">
              <span className="muted">{minerVotes.length} miner{minerVotes.length === 1 ? '' : 's'}</span>
              <button type="button" className="ghost-btn" onClick={expandAll}>Expand all</button>
              <button type="button" className="ghost-btn" onClick={collapseAll}>Collapse all</button>
            </div>
          </div>
        </div>
        <ul className="miner-votes">
          {minerVotes.map((vote, idx) => {
            const expanded = expandedMiners[vote.miner_id];
            return (
              <li key={vote.miner_id} className={`miner-vote ${expanded ? 'expanded' : ''}`}>
                <div className="miner-vote-header">
                  <div className="miner-vote-top">
                    <p className="miner-heading">{buildMinerHeading(idx)}</p>
                    <span className="chip chip-id" title={vote.miner_id}>{formatMinerId(vote.miner_id)}</span>
                  </div>
                  <div className="miner-vote-meta">
                    <span className="verdict-pill" style={{ backgroundColor: verdictPalette[vote.verdict] }}>
                      {verdictLabel[vote.verdict]}
                    </span>
                    <span className="confidence-pill">{formatPercent(vote.confidence)}</span>
                    <button type="button" onClick={() => toggleMinerVisibility(vote.miner_id)} className="ghost-btn">
                      {expanded ? 'Hide' : 'Show'}
                    </button>
                  </div>
                </div>
                {expanded && (
                  <div className="miner-vote-body">
                    <p>{vote.notes ?? 'This miner did not return additional reasoning.'}</p>
                    {vote.citations && vote.citations.length > 0 ? (
                      <ul className="miner-citations">
                        {vote.citations.map((citation, citationIdx) => (
                          <li key={`${vote.miner_id}-citation-${citationIdx}`}>
                            <div className="citation-entry">
                              {isValidHttpUrl(citation.url) ? (
                                <a href={citation.url ?? undefined} target="_blank" rel="noreferrer">
                                  {formatCitationLabel(citation)}
                                </a>
                              ) : (
                                <span>{formatCitationLabel(citation)} (no valid link)</span>
                              )}
                              {citation.description?.trim() ? (
                                <p className="citation-description">{citation.description.trim()}</p>
                              ) : null}
                            </div>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="muted">No citations were shared by this miner.</p>
                    )}
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      </section>
    );
  };

  return (
    <main className="page">
      <section className="panel form-panel">
        <div>
          <p className="eyebrow">ClaimCheck API sandbox</p>
          <h1>ClaimCheck Oracle</h1>
          <p className="lede">
            Run a claim through the Cortensor router and see how miners vote—confidence, dispersion, and citations in one
            view.
          </p>
          <p className="info-note">Runs two tasks (claim + validation). Validation may take a bit longer under load.</p>
        </div>

        <form className="claim-form" onSubmit={handleSubmit}>
          <label>
            Claim
            <textarea
              name="claim"
              required
              value={form.claim}
              onChange={handleChange}
              placeholder="e.g., The Eiffel Tower is taller than 350 meters."
            />
          </label>

          <label>
            Context URL (optional)
            <input
              type="url"
              name="context_url"
              value={form.context_url}
              onChange={handleChange}
              placeholder="https://"
            />
          </label>

          <label>
            Context Text (optional)
            <textarea
              name="context_text"
              value={form.context_text}
              onChange={handleChange}
              placeholder="Paste supporting or refuting evidence here."
              rows={4}
            />
          </label>

          <button type="submit" disabled={isLoading}>
            {isLoading ? 'Running...' : 'Run claim check'}
          </button>
        </form>

        {renderStatus()}

        <div className="history-block">
          <div className="history-header">
            <h3>History</h3>
            <button type="button" className="history-clear" onClick={clearHistory} disabled={!history.length}>
              Clear
            </button>
          </div>
          {history.length === 0 ? (
            <p className="muted">No history yet. Run a check to populate this list.</p>
          ) : (
            <ul className="history-list">
              {history.map((item) => (
                <li key={`${item.timestamp}-${item.claim.slice(0, 8)}`}>
                  <div className="history-main">
                    <span className="history-claim">{truncateClaim(item.claim)}</span>
                    <span className="verdict-pill" style={{ backgroundColor: verdictPalette[item.verdict] }}>
                      {verdictLabel[item.verdict]}
                    </span>
                    <button
                      type="button"
                      className="ghost-btn"
                      onClick={() => setForm((prev) => ({ ...prev, claim: item.claim }))}
                    >
                      Rerun
                    </button>
                  </div>
                  <div className="history-meta">
                    <span className="confidence-pill">{formatPercent(item.confidence)}</span>
                    <span className="history-time">{new Date(item.timestamp).toLocaleString()}</span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>

      <section className="panel results-panel">
        <header className="results-header">
          <div className="results-header-copy">
            <p className="eyebrow">Aggregate verdict</p>
            <h2 className={result ? '' : 'awaiting-heading'} style={result ? { color: verdictColor } : undefined}>
              {result ? verdictLabel[result.verdict] : 'Awaiting input'}
            </h2>
            {ribbon && <span className={`status-ribbon ${ribbon.tone}`}>{ribbon.text}</span>}
            {result && <p className="summary">{result.reasoning}</p>}
            {dashboardUrl && result?.task_id && (
              <a className="dashboard-link" href={dashboardUrl} target="_blank" rel="noreferrer">
                Open Cortensor dashboard (S{process.env.NEXT_PUBLIC_SESSION_ID} · T{result.task_id})
              </a>
            )}
            {headerChips.length > 0 && (
              <div className="chip-row">
                {headerChips.map((chip) => (
                  <span key={`${chip.label}-${chip.value}`} className="chip">
                    <span className="chip-label">{chip.label}</span>
                    <span className="chip-value">{chip.value}</span>
                  </span>
                ))}
              </div>
            )}
            {!result && isLoading && renderLoadingChat()}
          </div>
          <button
            className={`theme-toggle theme-icon ${theme === 'light' ? 'icon-moon' : 'icon-sun'}`}
            type="button"
            aria-label={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
            onClick={() => setTheme((prev) => (prev === 'light' ? 'dark' : 'light'))}
          >
            <span className="visually-hidden">Toggle theme</span>
          </button>
        </header>

        {isLoading && (
          <div className="sticky-bar">
            <div className="sticky-left">
              <span className="pulse-dot" aria-hidden />
              <span className="sticky-text">{formatStepLabel(activeStep)}</span>
            </div>
            <div className="sticky-progress">
              <div className="sticky-progress-fill" style={{ width: `${activeStep?.percent ?? 0}%` }} />
            </div>
            {isDetailHoldActive && (
              <button type="button" className="ghost-btn" onClick={() => detailHoldTimersRef.current.release?.()}>
                View partial results
              </button>
            )}
          </div>
        )}

        <div className="metrics-grid">
          <article>
            <span>Confidence</span>
            <strong>{result ? formatPercent(result.confidence) : '—'}</strong>
          </article>
          <article>
            <span>Dispersion</span>
            <strong>{result ? result.dispersion.toFixed(2) : '—'}</strong>
          </article>
        </div>

        {isLoading && !result && renderSkeletons()}

        {result && (
          <div className="details">
            {validation && (
              <section className="detail-block">
                <h3>Validation check</h3>
                <div className="validation-row">
                  <span className="verdict-pill" style={{ backgroundColor: validationPalette[validation.verdict] }}>
                    {validationLabel[validation.verdict]}
                  </span>
                  <span className="score-pill">Score {validation.score}/10</span>
                  <p>{validation.notes}</p>
                </div>
                <div className="validation-meta">
                  {validation.session_id && (
                    <span className="muted">Session {validation.session_id}</span>
                  )}
                  {validation.task_id && (
                    <span className="muted">Task {validation.task_id}</span>
                  )}
                  {validationDashboardUrl && (
                    <a className="dashboard-link" href={validationDashboardUrl} target="_blank" rel="noreferrer">
                      Open validation dashboard
                    </a>
                  )}
                  {validation.status && validation.status !== 'ok' && (
                    <div className={`inline-alert ${validation.status === 'timeout' ? 'warn' : 'error'}`}>
                      <span>
                        {validation.status === 'timeout'
                          ? 'Validation timed out; dashboard may have the latest state.'
                          : 'Validation encountered an error; please review the dashboard.'}
                      </span>
                      {validationDashboardUrl && (
                        <a className="alert-link" href={validationDashboardUrl} target="_blank" rel="noreferrer">
                          Open dashboard
                        </a>
                      )}
                    </div>
                  )}
                </div>
              </section>
            )}
            <section className="detail-block">
              <h3>Citations</h3>
              {citations.length === 0 ? (
                <p className="muted">No citations reported.</p>
              ) : (
                <ul className="citation-list">
                  {citations.map((citation, idx) => (
                    <li key={`${citation.source}-${idx}`}>
                      <div className="citation-entry">
                        {isValidHttpUrl(citation.url) ? (
                          <a
                            className={citation.description ? 'tooltip' : undefined}
                            data-tip={citation.description ?? undefined}
                            href={citation.url ?? undefined}
                            target="_blank"
                            rel="noreferrer"
                          >
                            {formatCitationLabel(citation)}
                          </a>
                        ) : (
                          <span>{formatCitationLabel(citation)} (no valid link)</span>
                        )}
                        {citation.description?.trim() ? (
                          <p className="citation-description">{citation.description.trim()}</p>
                        ) : null}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </section>
            {renderMinerDetails()}
          </div>
        )}
      </section>
    </main>
  );
}
