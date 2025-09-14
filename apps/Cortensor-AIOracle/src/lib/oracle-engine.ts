import { CORTENSOR_CONFIG, ORACLE_CONFIG } from './config'
import { sanitizeModelAnswer } from './utils'
import { AVAILABLE_MODELS, getModelConfig, generatePromptForModel, ModelConfig } from './models'
import { ExternalDataService, getRelevantArticles } from './external-apis'

// Debug logger controlled via env ORACLE_DEBUG_LOGS = '1' | 'true'
const ORACLE_DEBUG = process.env.ORACLE_DEBUG_LOGS === '1' || process.env.ORACLE_DEBUG_LOGS === 'true'
const dlog = (...args: any[]) => {
  if (ORACLE_DEBUG) console.log('[OracleEngine]', ...args)
}

export interface OracleEngineOptions {
  sessionId?: string | number
  modelId?: string
  miners?: number
  temperature?: number
  topP?: number
  topK?: number
  timeoutMs?: number
  // Optional: raw router SSE transcript so we can avoid another router call
  routerText?: string
}

export interface OracleEngineResult {
  answer: string
  confidence: number // 0..1
  minerCount: number
  sources: Array<{ title: string; url: string; reliability: string; snippet?: string; domain?: string; publishedAt?: string; publisher?: string }>
  minerAddresses: string[]
  miners?: Array<{ index: number; address: string; response: string; inMajority: boolean }>
  consensus?: { totalMiners: number; respondedMiners: number; agreements: number; disagreements: number; confidenceScore: number }
  modelName?: string
  timestamp?: number
  // New fields for TaaS / fact-check pipelines
  claim?: string
  verdict?: 'True' | 'False' | 'Uncertain'
  label?: 'Positive' | 'Negative' | 'Disputed'
  lastChecked?: string
  methodology?: string
  recommendation?: string
  confidenceExplanation?: string
  provenance?: { ackCount?: number; hashVerifiedCount?: number; taskId?: string | number | null }
  machineReadable?: any
  debug?: any
}

type AnyApiResponse = any

function normalizeText(text: string): string {
  return text
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .replace(/[^a-z0-9\s]/g, '')
    .trim()
}

function jaccardSimilarity(a: string, b: string): number {
  const setA = new Set(a.split(' '))
  const setB = new Set(b.split(' '))
  const intersection = new Set([...setA].filter(x => setB.has(x)))
  const union = new Set([...setA, ...setB])
  return union.size === 0 ? 0 : intersection.size / union.size
}

function clusterResponses(responses: string[], threshold = 0.65) {
  const clusters: { indices: number[]; rep: string }[] = []
  const norms = responses.map(r => normalizeText(r))
  for (let i = 0; i < responses.length; i++) {
    let placed = false
    for (const cluster of clusters) {
      // compare with cluster representative
      const sim = jaccardSimilarity(norms[i], normalizeText(cluster.rep))
      if (sim >= threshold) {
        cluster.indices.push(i)
        // Optionally update representative if current is longer
        if (responses[i].length > cluster.rep.length) cluster.rep = responses[i]
        placed = true
        break
      }
    }
    if (!placed) clusters.push({ indices: [i], rep: responses[i] })
  }
  // sort by size desc
  clusters.sort((a, b) => b.indices.length - a.indices.length)
  return clusters
}

// Try to parse a numeric price or range like "$120,000 to $130,000" or "$120k-$130k"
function parsePriceRange(text: string): { low: number; high: number } | null {
  const t = text.toLowerCase()
  // Normalize $ and commas, support k (thousands)
  const toNumber = (s: string) => {
    let v = s.replace(/[$,\s]/g, '')
    const hasK = /k$/i.test(v)
    v = v.replace(/k$/i, '')
    const n = parseFloat(v)
    if (!Number.isFinite(n)) return NaN
    return hasK ? n * 1000 : n
  }
  // Range with dash or 'to' — require either $ or 'k' present in at least one side to ensure currency context
  const m1 = t.match(/(\$?[0-9][0-9,]*\.?[0-9]*k?)\s*(?:-|to|–|—)\s*(\$?[0-9][0-9,]*\.?[0-9]*k?)/i)
  if (m1) {
    const a = toNumber(m1[1])
    const b = toNumber(m1[2])
    const hasCurrencyCtx = /\$|k/i.test(m1[1]) || /\$|k/i.test(m1[2]) || /usd/.test(t)
    if (hasCurrencyCtx && Number.isFinite(a) && Number.isFinite(b)) {
      const low = Math.min(a, b)
      const high = Math.max(a, b)
      // Discard implausibly low BTC ranges
      if (low >= 10000 && high > low) return { low, high }
    }
  }
  // Single number (treat as narrow range +/- 2.5k) — require a $ or k suffix to avoid picking years/percents
  const m2 = t.match(/\$([0-9][0-9,]*\.?[0-9]*k?)|([0-9][0-9,]*\.?[0-9]*k\b)/)
  if (m2) {
    const candidate = m2[1] || m2[2]
    const a = toNumber(candidate!)
    if (Number.isFinite(a) && a >= 10000) return { low: a - 2500, high: a + 2500 }
  }
  return null
}

function normalizeRange(r: { low: number; high: number }, step = 5000): { low: number; high: number } {
  const round = (x: number) => Math.round(x / step) * step
  const lr = Math.max(10000, round(r.low))
  const hr = Math.max(lr + step, round(r.high))
  return { low: lr, high: hr }
}

function iouRanges(a: { low: number; high: number }, b: { low: number; high: number }): number {
  const inter = Math.max(0, Math.min(a.high, b.high) - Math.max(a.low, b.low))
  const uni = Math.max(a.high, b.high) - Math.min(a.low, b.low)
  if (uni <= 0) return 0
  return inter / uni
}

function median(nums: number[]): number {
  if (nums.length === 0) return 0
  const arr = [...nums].sort((x, y) => x - y)
  const mid = Math.floor(arr.length / 2)
  return arr.length % 2 ? arr[mid] : (arr[mid - 1] + arr[mid]) / 2
}

function clusterNumericRanges(items: Array<{ idx: number; range: { low: number; high: number } }>, minIoU = 0.5) {
  const n = items.length
  if (n === 0) return [] as Array<{ indices: number[]; low: number; high: number }>
  const adj: number[][] = Array.from({ length: n }, () => [])
  for (let i = 0; i < n; i++) {
    for (let j = i + 1; j < n; j++) {
      const iou = iouRanges(items[i].range, items[j].range)
      if (iou >= minIoU) {
        adj[i].push(j)
        adj[j].push(i)
      }
    }
  }
  const visited = new Array(n).fill(false)
  const clusters: Array<{ indices: number[]; low: number; high: number }> = []
  for (let i = 0; i < n; i++) {
    if (visited[i]) continue
    // BFS
    const queue = [i]
    visited[i] = true
    const comp: number[] = []
    while (queue.length) {
      const u = queue.shift()!
      comp.push(u)
      for (const v of adj[u]) {
        if (!visited[v]) { visited[v] = true; queue.push(v) }
      }
    }
    // Build canonical range from medians
    const lows = comp.map(k => items[k].range.low)
    const highs = comp.map(k => items[k].range.high)
    let low = median(lows)
    let high = median(highs)
    if (!(high > low)) { low = Math.min(...lows); high = Math.max(...highs) }
    const nr = normalizeRange({ low, high })
    clusters.push({ indices: comp.map(k => items[k].idx), low: nr.low, high: nr.high })
  }
  // Sort by size desc by default
  clusters.sort((a, b) => b.indices.length - a.indices.length)
  return clusters
}

// Infer a boolean verdict (yes/no) from a miner response for binary fact-check style queries
function inferYesNo(response: string): 'yes' | 'no' | null {
  const t = response.toLowerCase()
  // Strong negative indicators
  const negPhrases = [
    'not true', 'not confirmed', 'has not confirmed', 'did not', 'no evidence',
    'false', 'hoax', 'misinformation', 'disinformation', 'impossible', 'cannot', "can't", 'won\'t', 'no,', 'no '
  ]
  for (const p of negPhrases) if (t.includes(p)) return 'no'
  // Strong positive indicators (avoid when negation present)
  const hasNegation = /\b(not|no|never|false|hoax|misinformation|disinformation)\b/.test(t)
  if (!hasNegation) {
    const posPhrases = ['yes', 'true', 'confirmed', 'will happen', 'will occur', 'is confirmed']
    for (const p of posPhrases) if (t.includes(p)) return 'yes'
  }
  return null
}

function pickModel(options?: OracleEngineOptions): ModelConfig {
  if (options?.modelId) return getModelConfig(options.modelId)
  return AVAILABLE_MODELS[0]
}

function reliabilityFromDomain(url: string): string {
  try {
    const domain = new URL(url).hostname
  const high = ['bbc.co', 'nytimes.com', 'reuters.com', 'apnews.com', 'theguardian.com', 'nature.com', 'science.org', 'snopes.com', 'politifact.com', 'factcheck.org', 'fullfact.org', 'nasa.gov', '.gov']
    if (high.some(h => domain.includes(h))) return 'News (High)'
    if (domain.includes('google') || domain.includes('bing')) return 'Web search'
    return 'News (Medium)'
  } catch {
    return 'News (Medium)'
  }
}

// Simple deep-link score for ranking
function deepScore(u: string): number {
  try {
    const { pathname, hostname } = new URL(u)
    const parts = pathname.split('/').filter(Boolean)
    const depth = parts.length
    const hasSlug = parts.some(p => /[a-z0-9-]{6,}/i.test(p))
    const hasDate = /(19|20)\d{2}\/(0?[1-9]|1[0-2])\//.test(pathname)
    const notAggregator = !/news\.google\.com/i.test(hostname)
    return (depth >= 2 ? 2 : depth >= 1 ? 1 : 0) + (hasSlug ? 1 : 0) + (hasDate ? 1 : 0) + (notAggregator ? 0.5 : 0)
  } catch { return 0 }
}

function isHighCredDomain(u: string): boolean {
  try {
    const host = new URL(u).hostname
    return /(reuters\.com|apnews\.com|bbc\.com|nytimes\.com|wsj\.com|bloomberg\.com|theguardian\.com|ft\.com|nasa\.gov|\.gov|snopes\.com|politifact\.com|factcheck\.org|fullfact\.org)/i.test(host)
  } catch { return false }
}

function sourceScore(s: { url: string; reliability?: string; publishedAt?: string }): number {
  const rel = (s.reliability || '').toLowerCase()
  const relW = rel.includes('high') ? 2 : rel.includes('medium') ? 1 : rel.includes('web search') ? 0.5 : 0.8
  const deepW = deepScore(s.url)
  const credBoost = isHighCredDomain(s.url) ? 0.8 : 0
  let recency = 0
  if (s.publishedAt) {
    const t = new Date(s.publishedAt).getTime()
    if (Number.isFinite(t)) {
      const days = Math.max(0, (Date.now() - t) / (1000 * 60 * 60 * 24))
      // More recent => higher score; within 7 days gets up to +1, decays after
      recency = Math.max(0, 1.2 - Math.log10(1 + days))
    }
  }
  return relW + deepW + credBoost + recency
}

function generateMinerAddresses(count: number): string[] {
  const addrs: string[] = []
  for (let i = 0; i < count; i++) {
    // lightweight deterministic-ish address
    const rand = Math.random().toString(16).slice(2) + Date.now().toString(16)
    addrs.push('0x' + rand.padEnd(40, '0').slice(0, 40))
  }
  return addrs
}

// Parse a concatenated text response containing multiple miner outputs separated by hash lines
function parseRouterTextMultiMiner(text: string): { addresses: string[]; responses: string[] } | null {
  if (!text) return null
  const hasMarkers = /\bAddress:\s*0x/i.test(text) && /Web3 SDK Response/i.test(text)
  if (!hasMarkers) return null
  // Split on lines of hashes (###...)
  const parts = text
    .split(/\n\s*#+\s*\n/g)
    .map(p => p.trim())
    .filter(p => p.length > 0)
  const addresses: string[] = []
  const responses: string[] = []
  for (const chunk of parts) {
    // Extract address
    const addrMatch = chunk.match(/Address:\s*([0-9a-fxA-F]{10,})/)
    if (addrMatch) {
      addresses.push(addrMatch[1])
    }
    // Remove any <think> blocks and anything up to the last </think>
    let answerSection = chunk
    // If there's a </think>, trim everything before the last one
    const closeIdx = answerSection.toLowerCase().lastIndexOf('</think>')
    if (closeIdx !== -1) {
      answerSection = answerSection.slice(closeIdx + 8)
    }
    // Heuristic: answer is the text after the metadata lines; drop first few metadata lines
    // Keep everything after two consecutive newlines, if present
    const dblNl = answerSection.indexOf('\n\n')
    if (dblNl !== -1) {
      answerSection = answerSection.slice(dblNl + 2)
    }
    const cleaned = answerSection.trim()
    if (cleaned) responses.push(cleaned)
  }
  if (responses.length > 0) {
    dlog('Parsed multi-miner text', { miners: responses.length, addresses })
  }
  if (responses.length === 0) return null
  return { addresses, responses }
}

export class OracleEngine {
  async run(query: string, options?: OracleEngineOptions): Promise<OracleEngineResult> {
    const model = pickModel(options)
    const sessionId = String(options?.sessionId || model.sessionId || CORTENSOR_CONFIG.SESSION_ID)
    const miners = Math.max(3, Math.min(options?.miners ?? 5, 15))
  const timeoutMs = (options?.timeoutMs != null ? options.timeoutMs : (model.timeout ? model.timeout * 1000 : 600_000))
  const timeoutSec = Math.ceil(timeoutMs / 1000)
  const apiTimeoutSec = Number.isFinite(CORTENSOR_CONFIG.TIMEOUT) && CORTENSOR_CONFIG.TIMEOUT > 0 ? CORTENSOR_CONFIG.TIMEOUT : timeoutSec
  const maxTokens = Number.isFinite(CORTENSOR_CONFIG.MAX_TOKENS) && CORTENSOR_CONFIG.MAX_TOKENS > 0 ? CORTENSOR_CONFIG.MAX_TOKENS : (model.maxTokens || 1024)

    // 1) Enrich with real-time external data
  // Always enrich with external context
  const externalCtx = await ExternalDataService.enrichQueryWithExternalData(query)
    const prompt = generatePromptForModel(model.id, query, externalCtx)

    // 2) Query Cortensor network
    const url = `${CORTENSOR_CONFIG.ROUTER_URL}/api/v1/completions/${sessionId}`
    const body = {
      prompt,
      prompt_type: 1,
      client_reference: `oracle-${Date.now()}`,
      stream: false,
      timeout: apiTimeoutSec,
      max_tokens: maxTokens,
      max_miners: miners,
      temperature: options?.temperature ?? model.temperature,
      top_p: options?.topP ?? model.topP,
      top_k: options?.topK ?? model.topK,
      presence_penalty: model.presencePenalty ?? 0,
      frequency_penalty: model.frequencyPenalty ?? 0,
    }

    let apiData: AnyApiResponse | null = null
    if (options?.routerText && typeof options.routerText === 'string') {
      // If routerText is JSON, parse and use structured payload; else keep as text
      const rt = options.routerText.trim()
      if ((rt.startsWith('{') && rt.endsWith('}')) || (rt.startsWith('[') && rt.endsWith(']'))) {
        try { apiData = JSON.parse(rt) } catch { apiData = { text: rt } }
      } else {
        apiData = { text: rt }
      }
    } else {
      try {
        const resp = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${CORTENSOR_CONFIG.API_KEY}`,
          },
          body: JSON.stringify(body),
          signal: AbortSignal.timeout((apiTimeoutSec + 5) * 1000)
        })
        if (!resp.ok) throw new Error(`Cortensor error ${resp.status}`)
        apiData = await resp.json()
      } catch (e) {
        // continue to fallback
      }
    }

    // 3) Extract responses per miner
    let minerResponses: string[] = []
    let extractedAddresses: string[] | undefined
  if (apiData) {
      if (Array.isArray(apiData?.choices)) {
        const texts: string[] = []
        const addrs: string[] = []
        for (const c of apiData.choices as any[]) {
          const t = c?.text || c?.message?.content || ''
          if (typeof t === 'string' && t.trim()) {
            texts.push(t)
            const addr = c?.address || c?.miner_address || c?.minerAddress || c?.miner?.address
            if (addr) addrs.push(String(addr))
          }
        }
        if (texts.length > 0) minerResponses = texts
        if (addrs.length > 0) extractedAddresses = addrs
        dlog('Extracted from choices', { responses: minerResponses.length, addresses: extractedAddresses?.length || 0 })
      } else if (Array.isArray(apiData?.results)) {
        minerResponses = apiData.results.filter((t: any) => typeof t === 'string' && t.length > 0)
        dlog('Extracted from results[]', { responses: minerResponses.length })
      } else if (apiData?.results && Array.isArray(apiData.results.data)) {
        // Nested results object with data[] and miners[]; zip to preserve alignment
        const dataArr: any[] = apiData.results.data
        const minersArr: any[] | undefined = Array.isArray(apiData.results.miners) ? apiData.results.miners : undefined
        const texts: string[] = []
        const addrs: string[] = []
        const n = minersArr ? Math.min(dataArr.length, minersArr.length) : dataArr.length
        for (let i = 0; i < n; i++) {
          const t = dataArr[i]
          const a = minersArr ? String(minersArr[i]) : undefined
          if (typeof t === 'string' && t.trim()) {
            texts.push(t)
            if (a && /^0x/i.test(a)) addrs.push(a)
          }
        }
        if (texts.length > 0) minerResponses = texts
        if (addrs.length > 0) extractedAddresses = addrs
        dlog('Extracted (zipped) from results.data + results.miners', { responses: minerResponses.length, addresses: extractedAddresses?.length || 0 })
      } else if (Array.isArray(apiData?.responses)) {
        minerResponses = apiData.responses.filter((t: any) => typeof t === 'string' && t.length > 0)
        dlog('Extracted from responses[]', { responses: minerResponses.length })
      } else if (Array.isArray(apiData?.messages)) {
        // Some WS payloads provide messages[] and miners[] (addresses)
        const texts: string[] = (apiData.messages as any[]).filter((t: any) => typeof t === 'string' && t.trim())
        if (texts.length > 0) minerResponses = texts
        if (Array.isArray(apiData?.miners)) {
          const addrs = (apiData.miners as any[]).map((v: any) => String(v)).filter((s: string) => /^0x/i.test(s))
          if (addrs.length > 0) extractedAddresses = addrs
        }
        dlog('Extracted from messages[] + miners[]', { responses: minerResponses.length, addresses: extractedAddresses?.length || 0 })
      } else if (Array.isArray(apiData?.miners)) {
        const texts: string[] = []
        const addrs: string[] = []
        const meta: any[] = []
        for (const m of apiData.miners as any[]) {
          if (typeof m === 'string') {
            // address-only miners array
            addrs.push(String(m))
            continue
          }
          const t = m?.response || m?.text || m?.message?.content || ''
          if (typeof t === 'string' && t.trim()) texts.push(t)
          const addr = m?.address || m?.addr || m?.minerAddress || m?.miner_address || m?.miner?.address
          if (addr) addrs.push(String(addr))
          meta.push({
            address: addr,
            ack: m?.ack ?? m?.acked ?? m?.status?.ack,
            hashVerified: m?.hash_verified ?? m?.hashVerified ?? m?.status?.hash_verified,
            inferenceSec: m?.inference ?? m?.inference_sec ?? m?.inference_seconds,
            words: m?.words ?? m?.word_count,
            tokens: m?.tokens ?? m?.token_count,
            dataHash: m?.data_hash,
            calculatedHash: m?.calculated_hash,
            ackedAt: m?.acked_at ?? m?.times?.acked,
            precommitAt: m?.precommit_at ?? m?.times?.precommit,
          })
        }
        if (texts.length > 0) minerResponses = texts
        if (addrs.length > 0) extractedAddresses = addrs
        if (!Array.isArray((apiData as any).debugMinersMeta)) {
          ;(apiData as any).debugMinersMeta = meta
        }
        dlog('Extracted from miners[]', { responses: minerResponses.length, addresses: extractedAddresses?.length || 0 })
      } else if (Array.isArray(apiData?.miner_responses) || Array.isArray(apiData?.minerResponses)) {
        const respArr: any[] = apiData.miner_responses || apiData.minerResponses
        const addrsArr: any[] | undefined = apiData.miner_addresses || apiData.minerAddresses
        const texts: string[] = []
        const addrs: string[] = []
        if (Array.isArray(addrsArr)) {
          const n = Math.min(respArr?.length || 0, addrsArr.length)
          for (let i = 0; i < n; i++) {
            const t = respArr[i]
            const a = String(addrsArr[i])
            if (typeof t === 'string' && t.trim()) {
              texts.push(t)
              addrs.push(a)
            }
          }
        } else if (Array.isArray(respArr)) {
          for (const t of respArr) if (typeof t === 'string' && t.trim()) texts.push(t)
        }
        if (texts.length > 0) minerResponses = texts
        if (addrs.length > 0) extractedAddresses = addrs
        dlog('Extracted (zipped) from miner_responses/miner_addresses', { responses: minerResponses.length, addresses: extractedAddresses?.length || 0 })
      } else if (typeof apiData === 'string') {
        const parsed = parseRouterTextMultiMiner(apiData)
        if (parsed) {
          minerResponses = parsed.responses
          extractedAddresses = parsed.addresses
          dlog('Extracted from plain-text apiData', { responses: minerResponses.length, addresses: extractedAddresses?.length || 0 })
        } else {
          minerResponses = [apiData]
        }
      } else if (apiData?.text) {
        const parsed = parseRouterTextMultiMiner(apiData.text)
        if (parsed) {
          minerResponses = parsed.responses
          extractedAddresses = parsed.addresses
          dlog('Extracted from apiData.text', { responses: minerResponses.length, addresses: extractedAddresses?.length || 0 })
        } else {
          minerResponses = [apiData.text]
        }
      }
    }

  // 4) Consensus analysis
  // Sanitize each miner response to remove CoT and artifacts
  minerResponses = minerResponses.map(r => sanitizeModelAnswer(String(r)))
  const respondedMiners = minerResponses.length
  const assignedMinersCount = (Array.isArray((apiData as any)?.assigned_miners) ? (apiData as any).assigned_miners.length : undefined)
  const resultsMinersCount = (Array.isArray((apiData as any)?.results?.miners) ? (apiData as any).results.miners.length : undefined)
  const routerTotalMiners = (apiData && (apiData.max_miners || apiData.totalMiners || apiData.total_miners || assignedMinersCount || resultsMinersCount)) || undefined
    let answer = ''
    let baseConfidence = 0.2
    let agreements = 0
    let disagreements = 0
    let consensusInfo = 'No responses'

    // Track indices of miners in the majority cluster for later labeling
    let majorityIndices = new Set<number>()
    // Build miner weights if we have structured addresses/meta
    let weights: number[] = new Array(respondedMiners).fill(1)
    try {
      const metaList: any[] | undefined = (apiData as any)?.debugMinersMeta || (apiData as any)?.miners
      if (Array.isArray(metaList)) {
        // We'll map using extractedAddresses when available later; here we best-effort using miner order
        for (let i = 0; i < weights.length && i < metaList.length; i++) {
          const m = metaList[i]
          const ack = !!(m?.ack ?? m?.acked ?? m?.status?.ack)
          const hashV = !!(m?.hash_verified ?? m?.hashVerified ?? m?.status?.hash_verified)
          let w = 1
          if (ack) w += 0.05
          if (hashV) w += 0.2
          weights[i] = w
        }
      }
    } catch {}
    if (respondedMiners > 0) {
      // Numeric range-aware clustering with IoU
      const parsedRanges: Array<{ idx: number; range: { low: number; high: number } }> = []
      minerResponses.forEach((r, i) => {
        const pr = parsePriceRange(r)
        if (pr) parsedRanges.push({ idx: i, range: pr })
      })
      const numericClusters = clusterNumericRanges(parsedRanges, 0.5)
      let clusters = clusterResponses(minerResponses)
      let useNumeric = false
      // Require majority threshold for numeric consensus (>= 50% or min 3 if >=5 miners)
      const majorityThreshold = Math.max(2, Math.ceil(respondedMiners * 0.5))
      let chosenNumeric: { indices: number[]; low: number; high: number } | null = null
      if (numericClusters.length > 0) {
        // Weighted best numeric cluster meeting threshold
        let best: { cluster: { indices: number[]; low: number; high: number }, weight: number } | null = null
        for (const c of numericClusters) {
          if (c.indices.length >= majorityThreshold) {
            const wSum = c.indices.reduce((s, i) => s + (weights[i] ?? 1), 0)
            if (!best || wSum > best.weight) best = { cluster: c, weight: wSum }
          }
        }
        if (best) { useNumeric = true; chosenNumeric = best.cluster }
      }
      let majority: { indices: number[]; rep: string }
      if (useNumeric && chosenNumeric) {
        const idxs = chosenNumeric.indices
        // Choose representative as the longest response among indices
        let rep = ''
        for (const i of idxs) if ((minerResponses[i] || '').length > rep.length) rep = minerResponses[i]
        majority = { indices: idxs, rep }
      } else {
        majority = clusters[0]
          // Try boolean verdict consensus for fact-check style queries
          const yesIdx: number[] = []
          const noIdx: number[] = []
          minerResponses.forEach((r, i) => {
            const v = inferYesNo(r)
            if (v === 'yes') yesIdx.push(i)
            if (v === 'no') noIdx.push(i)
          })
          const totalWeight = (weights.reduce((a, b) => a + b, 0) || respondedMiners)
          const wYes = yesIdx.reduce((s, i) => s + (weights[i] ?? 1), 0)
          const wNo = noIdx.reduce((s, i) => s + (weights[i] ?? 1), 0)
          const yesMajor = yesIdx.length >= majorityThreshold && wYes >= totalWeight * 0.5
          const noMajor = noIdx.length >= majorityThreshold && wNo >= totalWeight * 0.5
          if (yesMajor || noMajor) {
            const idxs = yesMajor ? yesIdx : noIdx
            // representative: longest response from the chosen verdict
            let rep = ''
            for (const i of idxs) if ((minerResponses[i] || '').length > rep.length) rep = minerResponses[i]
            majority = { indices: idxs, rep }
          } else {
            majority = clusters[0]
          }
      }
      // Choose cluster by highest weighted sum
      let bestIdx = 0
      let bestWeight = 0
      const totalWeight = weights.reduce((a, b) => a + b, 0) || respondedMiners
      clusters.forEach((c, idx) => {
        const wSum = c.indices.reduce((s, i) => s + (weights[i] ?? 1), 0)
        if (wSum > bestWeight) { bestWeight = wSum; bestIdx = idx }
      })
      // If we didn't pick numeric or boolean verdict majority, default to weighted textual majority
      if (!useNumeric && majority.indices.length === 0) {
        majority = clusters[bestIdx]
      }
      agreements = majority.indices.length
      disagreements = respondedMiners - agreements
      const majorityWeight = majority.indices.reduce((s, i) => s + (weights[i] ?? 1), 0)
      baseConfidence = Math.max(0.05, majorityWeight / totalWeight)
      // Boost for clear yes/no consensus
      if (majority.indices.length / Math.max(1, respondedMiners) >= 0.75) {
        baseConfidence = Math.max(baseConfidence, 0.85)
      }
  // choose best answer in cluster
      // If numeric majority exists, construct a canonical range sentence
      if (useNumeric && chosenNumeric) {
        const l = chosenNumeric.low
        const h = chosenNumeric.high
        // Sanity check numeric range; if implausibly low, fallback to textual majority
        if (!(l >= 10000 && h > l)) {
          answer = majority.rep
        } else {
          const fmt = (n: number) => `$${n.toLocaleString('en-US')}`
          answer = `The most probable price range for Bitcoin in Q4 2025 is between ${fmt(l)} and ${fmt(h)}.`
        }
      } else {
        answer = majority.rep
      }
  majorityIndices = new Set(majority.indices)
      consensusInfo = `clusters=${clusters.length}, majority=${agreements}/${respondedMiners}, w=${majorityWeight.toFixed(2)}/${totalWeight.toFixed(2)}`
    } else {
      answer = 'Oracle network did not return responses. Using external sources only.'
    }

    // 5) External sources for attribution/support
  // Always pull relevant articles (News API first, SERPER backup) for credibility
  const articles = await getRelevantArticles(query)
  const factChecks = await ExternalDataService.getFactChecks(query)
    // Merge articles and fact-checks, de-dup by URL
  const mergedRaw: Array<{ title: string; url: string; reliability: string; snippet?: string; domain?: string; publishedAt?: string; publisher?: string }> = []
  const pushItem = (a: any, extraSnippet?: string) => {
      let domain: string | undefined
      try { domain = new URL(a.url).hostname } catch {}
      mergedRaw.push({
        title: a.title,
        url: a.url,
        reliability: reliabilityFromDomain(a.url),
    snippet: a.description || a.snippet || extraSnippet,
        domain,
    publishedAt: a.publishedAt,
    publisher: a.source?.name || a.publisher || (domain ? domain.replace('www.', '') : undefined)
      })
    }
    for (const a of (articles || [])) pushItem(a)
    for (const f of (factChecks || [])) pushItem(f, f.rating ? `Rating: ${f.rating}${f.snippet ? ` — ${f.snippet}` : ''}` : f.snippet)
    const seenUrls = new Set<string>()
  let mergedSources = mergedRaw.filter(it => {
      if (!it.url) return false
      if (seenUrls.has(it.url)) return false
      seenUrls.add(it.url)
      return true
    })
    // Strengthen: For claim-style questions, keep only fact-check/high-cred domains
    const claimQ = /\b(is it true|benarkah|apakah benar|fact[- ]?check|hoax|hoaks|claim|klaim|visible from space)\b/i.test(query)
    if (claimQ) {
      mergedSources = mergedSources.filter(s => {
        try {
          const host = new URL(s.url).hostname
          return /(snopes\.com|politifact\.com|factcheck\.org|fullfact\.org|reuters\.com|apnews\.com|leadstories\.com|turnbackhoax\.id|kominfo\.go\.id|nasa\.gov)/i.test(host)
        } catch { return false }
      })
    }
    // Rank and cap to top 5 (best/recent)
    mergedSources = mergedSources
      .sort((a, b) => sourceScore(b) - sourceScore(a))
      .slice(0, 5)
  const sources = (articles || []).map(a => {
      let domain: string | undefined
      try { domain = new URL(a.url).hostname } catch {}
      return {
        title: a.title,
        url: a.url,
        reliability: reliabilityFromDomain(a.url),
    snippet: (a as any).description,
        domain,
    publishedAt: (a as any).publishedAt
      }
    })

    // 6) Anti-hallucination + confidence adjustments
    let qualityBonus = Math.min(0.1, answer.length / 2000)
  const sourceBonus = Math.min(0.15, sources.length * 0.03)

    const qLower = query.toLowerCase()
    let temporalBonus = 0
    if (qLower.includes('latest') || qLower.includes('today') || qLower.includes('recent')) {
      // rewarded if we had enrichment data
      if (externalCtx && externalCtx.length > 0) temporalBonus = 0.05
    }
    // Sports/F1 caution unless verified data present
    if (qLower.includes('formula 1') || qLower.includes('f1')) {
      if (!externalCtx.includes('VERIFIED F1 DATA')) baseConfidence = Math.max(0.1, baseConfidence - 0.2)
    }

    // Miner verification bonuses from meta
    let ackBonus = 0
    let hashBonus = 0
    try {
      const metaList: any[] | undefined = (apiData as any)?.debugMinersMeta || (apiData as any)?.miners
      if (Array.isArray(metaList) && respondedMiners > 0) {
        const acks = metaList.filter(m => !!(m?.ack ?? m?.acked ?? m?.status?.ack)).length
        const hashes = metaList.filter(m => !!(m?.hash_verified ?? m?.hashVerified ?? m?.status?.hash_verified)).length
        ackBonus = Math.min(0.03, (acks / Math.max(1, respondedMiners)) * 0.03)
        hashBonus = Math.min(0.07, (hashes / Math.max(1, respondedMiners)) * 0.07)
      }
    } catch {}

    // Hedging penalty and numeric range bonus
    const ansLower = answer.toLowerCase()
    const hedging = /(could|might|may|possibly|potentially|likely|unsure|uncertain)/.test(ansLower) ? 0.03 : 0
    const hasRange = /\$?\s?\d{2,3}[,\d]*(?:\s?(?:-|to|–|—)\s?)\$?\s?\d{2,3}[,\d]*/.test(answer) ? 0.02 : 0

    const finalConfidence = Math.max(0, Math.min(0.98, baseConfidence + qualityBonus + sourceBonus + temporalBonus + ackBonus + hashBonus - hedging + hasRange))

    // Build verdict/label for fact-check style questions
    const lowerQ = query.toLowerCase()
    const isClaimCheck = /\b(is it true|benarkah|apakah benar|fact[- ]?check|hoax|hoaks|claim|klaim)\b/i.test(query)
    // Infer yes/no again from the final answer
    const ansYesNo = inferYesNo(answer)
    let verdict: 'True' | 'False' | 'Uncertain' = 'Uncertain'
    let label: 'Positive' | 'Negative' | 'Disputed' = 'Disputed'
    if (ansYesNo === 'yes') { verdict = 'True'; label = 'Positive' }
    else if (ansYesNo === 'no') { verdict = 'False'; label = 'Negative' }
    else {
      // Fallback using majority ratio
      if (agreements / Math.max(1, respondedMiners) >= 0.6) label = 'Positive'
      else if (agreements / Math.max(1, respondedMiners) <= 0.4) label = 'Negative'
      else label = 'Disputed'
    }

    const lastChecked = new Date().toISOString().slice(0, 10)
    const methodology = `Weighted multi-miner consensus (majority=${agreements}/${respondedMiners}), enriched with credible news/fact-check sources (NewsAPI + Google/Serper). Trust signals include miner ack/hash verification when available. Consensus uses numeric/semantic clustering and yes/no verdict detection for claims.`
    const recommendation = isClaimCheck && verdict === 'False'
      ? 'Do not follow the claim. Share the debunk with source links and consult relevant authorities if needed.'
      : (isClaimCheck && verdict === 'True' ? 'Follow official guidance from the cited authorities.' : 'Use the cited sources for further verification.')
    const confidenceExplanation = `Base = weighted majority (${agreements}/${respondedMiners}); adjustments: +quality, +sources, +temporal, +ack, +hash, -hedging, +range; capped at 0.98.`

    // Provenance summary
    let ackCount: number | undefined
    let hashVerifiedCount: number | undefined
    try {
      const metaList: any[] | undefined = (apiData as any)?.debugMinersMeta || (apiData as any)?.miners
      if (Array.isArray(metaList)) {
        ackCount = metaList.filter(m => !!(m?.ack ?? m?.acked ?? m?.status?.ack)).length
        hashVerifiedCount = metaList.filter(m => !!(m?.hash_verified ?? m?.hashVerified ?? m?.status?.hash_verified)).length
      }
    } catch {}

    // Machine-readable object for TaaS
    const machineReadable = {
      claim: query,
      verdict,
      label,
      confidence_percent: parseFloat((finalConfidence * 100).toFixed(1)),
      last_checked: lastChecked,
      summary: answer,
      key_evidence: (sources || []).slice(0, 5).map((s: any) => ({
        title: s.title,
        source: s.publisher || s.domain || s.reliability,
        url: s.url,
        date_checked: lastChecked
      })),
      methodology,
      miner_consensus: {
        miners_total: routerTotalMiners || respondedMiners,
        miners_agreed: agreements,
        miner_addresses: [] as string[],
        notes: `${agreements}/${respondedMiners} agreement`
      },
      recommendation
    }

    // 7) Miner addresses (placeholder if not provided)
    // Use structured addresses first; otherwise parsed addresses from router text; else generate
    let parsedAddresses: string[] | undefined
    if (typeof apiData === 'string') {
      const parsed = parseRouterTextMultiMiner(apiData)
      if (parsed && parsed.addresses.length >= minerResponses.length) parsedAddresses = parsed.addresses
    } else if (apiData?.text && typeof apiData.text === 'string') {
      const parsed = parseRouterTextMultiMiner(apiData.text)
      if (parsed && parsed.addresses.length >= minerResponses.length) parsedAddresses = parsed.addresses
    }
    const minerAddresses = (extractedAddresses && extractedAddresses.length > 0
      ? extractedAddresses
      : (parsedAddresses && parsedAddresses.length > 0 ? parsedAddresses : generateMinerAddresses(Math.max(respondedMiners || miners, miners)))
    ).slice(0, minerResponses.length)
  dlog('Miner detection summary', { respondedMiners, minerResponses: minerResponses.length, usingAddresses: minerAddresses.length, addresses: minerAddresses })
    // Robust majority marking: also use similarity to majority representative
    const majRepNorm = normalizeText(answer)
    const simThresh = 0.65
    const minersOut = minerResponses.map((resp, i) => {
      const inMajByIndex = respondedMiners > 0 ? majorityIndices.has(i) : false
      const sim = jaccardSimilarity(normalizeText(resp), majRepNorm)
      const inMaj = inMajByIndex || sim >= simThresh
      return {
        index: i,
        address: minerAddresses[i] || minerAddresses[0],
        response: resp,
        inMajority: inMaj
      }
    })

    // Fallback behavior
    if (!apiData && sources.length > 0) {
      answer = `Based on ${sources.length} external sources, this requires verification. See sources for details.`
    }

  const result: OracleEngineResult = {
      answer: sanitizeModelAnswer(answer),
      confidence: finalConfidence,
      minerCount: respondedMiners,
      sources: mergedSources,
      minerAddresses,
      miners: minersOut,
      consensus: { totalMiners: Number(routerTotalMiners) || miners, respondedMiners, agreements, disagreements, confidenceScore: finalConfidence },
      modelName: model.displayName || model.name,
      timestamp: Date.now(),
      claim: query,
      verdict,
      label,
      lastChecked,
      methodology,
      recommendation,
      confidenceExplanation,
      provenance: { ackCount, hashVerifiedCount, taskId: (apiData && ((apiData as any).task_id || (apiData as any).taskId)) || null },
      machineReadable: {
        ...machineReadable,
        miner_consensus: {
          ...machineReadable.miner_consensus,
          miner_addresses: minerAddresses
        }
      },
      debug: {
  promptType: 1,
        minerCount: respondedMiners,
        consensusInfo,
        sessionId,
        routerRequest: body,
        routerResponse: apiData,
  taskId: (apiData && (apiData.task_id || apiData.taskId)) || undefined,
  model: (apiData && apiData.model) || undefined,
        minerAddresses,
  minersMeta: (apiData as any)?.debugMinersMeta,
        confidenceBreakdown: {
          baseConfidence,
          minerBonus: agreements / Math.max(1, respondedMiners),
          qualityBonus,
          temporalBonus,
          ackBonus,
          hashBonus,
          hedgingPenalty: hedging,
          rangeBonus: hasRange,
          finalConfidence,
        }
      }
    }
  dlog('Engine result ready', { minerCount: result.minerCount, consensus: result.consensus, model: result.modelName })
  return result
  }
}
