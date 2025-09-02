# Stream Parsing Algorithms for Thinking Section Detection

## Overview
This document outlines multiple algorithms for handling stream parsing to ensure content is only displayed after the thinking section appears. Any response before the thinking section should be considered as loading state.

## Algorithm 1: Buffered Detection with Markers

### Description
Buffer all incoming stream chunks without parsing until thinking section markers are detected.

### Implementation Steps
```
1. Buffer all incoming stream chunks without parsing
2. Continuously scan buffer for thinking section markers:
   - `</think>` (DeepSeek R1 format)
   - `Thinking:` (structured format)
   - `<｜begin of thinking｜>` (legacy format)
3. Once marker detected:
   - Set flag `hasReachedContent = true`
   - Begin parsing accumulated buffer
   - Continue parsing all subsequent chunks normally
4. If stream ends without finding markers:
   - Parse entire buffer as fallback
```

### Pros & Cons
- ✅ **Pros:** Simple implementation, works with multiple formats, reliable detection
- ❌ **Cons:** May delay content display if thinking section comes late, memory usage for large buffers

### Code Structure
```typescript
interface BufferedDetectionState {
  buffer: string;
  hasReachedThinking: boolean;
  markers: string[];
}

function processWithBufferedDetection(chunk: string, state: BufferedDetectionState) {
  state.buffer += chunk;
  
  if (!state.hasReachedThinking) {
    const markerFound = state.markers.some(marker => state.buffer.includes(marker));
    if (markerFound) {
      state.hasReachedThinking = true;
      return parseContent(state.buffer);
    }
    return null; // Still loading
  }
  
  return parseContent(state.buffer);
}
```

---

## Algorithm 2: Two-Phase Stream Processing

### Description
Separate stream processing into distinct detection and display phases.

### Implementation Steps
```
Phase 1 (Detection):
1. Accumulate chunks in raw buffer
2. Show loading state with animated dots
3. Search for thinking pattern in each new chunk
4. When pattern found, transition to Phase 2

Phase 2 (Display):
1. Parse entire accumulated buffer at once
2. Display parsed content immediately
3. Continue streaming and parsing normally
```

### Pros & Cons
- ✅ **Pros:** Clear separation of concerns, predictable behavior, easy to debug
- ❌ **Cons:** Sudden content appearance might be jarring, no progressive reveal

### Code Structure
```typescript
enum ProcessingPhase {
  DETECTION = 'detection',
  DISPLAY = 'display'
}

interface TwoPhaseState {
  phase: ProcessingPhase;
  detectionBuffer: string;
  displayBuffer: string;
}

function processTwoPhase(chunk: string, state: TwoPhaseState) {
  switch(state.phase) {
    case ProcessingPhase.DETECTION:
      state.detectionBuffer += chunk;
      if (hasThinkingMarker(state.detectionBuffer)) {
        state.phase = ProcessingPhase.DISPLAY;
        return parseAndDisplay(state.detectionBuffer);
      }
      return showLoading();
      
    case ProcessingPhase.DISPLAY:
      state.displayBuffer += chunk;
      return parseAndDisplay(state.displayBuffer);
  }
}
```

---

## Algorithm 3: Sliding Window Detection

### Description
Use a memory-efficient sliding window to detect thinking markers without storing entire buffer.

### Implementation Steps
```
1. Maintain a sliding window of last N characters (e.g., 500)
2. Check window for thinking markers after each chunk
3. Keep track of:
   - Total bytes received
   - Position of thinking marker when found
4. Once marker detected:
   - Retroactively parse from marker position
   - Begin normal streaming from that point
```

### Pros & Cons
- ✅ **Pros:** Memory efficient, can handle very long pre-thinking content, good for large responses
- ❌ **Cons:** More complex implementation, may miss markers split across window boundaries

### Code Structure
```typescript
interface SlidingWindowState {
  window: string;
  windowSize: number;
  totalReceived: number;
  markerPosition: number | null;
  fullBuffer: string;
}

function processSlidingWindow(chunk: string, state: SlidingWindowState) {
  state.fullBuffer += chunk;
  state.totalReceived += chunk.length;
  
  // Update sliding window
  state.window = (state.window + chunk).slice(-state.windowSize);
  
  if (!state.markerPosition && hasThinkingMarker(state.window)) {
    state.markerPosition = state.totalReceived - state.window.length + findMarkerPosition(state.window);
    return parseFromPosition(state.fullBuffer, state.markerPosition);
  }
  
  return state.markerPosition ? parseContent(chunk) : null;
}
```

---

## Algorithm 4: Progressive Reveal with Confidence Scoring

### Description
Use confidence scores to progressively determine when to start parsing and displaying content.

### Implementation Steps
```
1. Assign confidence scores to different markers:
   - `</think>`: 100% confidence
   - `Thinking:`: 90% confidence  
   - Line breaks + capital letter: 30% confidence
2. Accumulate confidence as stream progresses
3. When confidence > threshold (e.g., 80%):
   - Start parsing and displaying
4. Show different loading states:
   - "Initializing..." (0-30% confidence)
   - "Processing..." (30-70% confidence)
   - "Analyzing..." (70%+ confidence)
```

### Pros & Cons
- ✅ **Pros:** Better UX with progressive feedback, handles ambiguous cases gracefully
- ❌ **Cons:** May occasionally misdetect start point, requires tuning confidence thresholds

### Code Structure
```typescript
interface ConfidenceState {
  buffer: string;
  confidenceScore: number;
  threshold: number;
  isParsing: boolean;
}

const CONFIDENCE_RULES = [
  { pattern: /<\/think>/, score: 100 },
  { pattern: /Thinking:/, score: 90 },
  { pattern: /\n[A-Z]/, score: 30 }
];

function processWithConfidence(chunk: string, state: ConfidenceState) {
  state.buffer += chunk;
  
  if (!state.isParsing) {
    state.confidenceScore = calculateConfidence(state.buffer, CONFIDENCE_RULES);
    
    if (state.confidenceScore >= state.threshold) {
      state.isParsing = true;
      return parseContent(state.buffer);
    }
    
    return showLoadingWithConfidence(state.confidenceScore);
  }
  
  return parseContent(state.buffer);
}
```

---

## Algorithm 5: Timeout-Based Hybrid

### Description
Combine marker detection with a timeout fallback for responses without thinking sections.

### Implementation Steps
```
1. Buffer chunks without parsing
2. Start a timeout timer (e.g., 2 seconds)
3. If thinking marker found before timeout:
   - Parse from beginning
4. If timeout expires without marker:
   - Assume no thinking section
   - Parse everything as regular content
5. Reset approach for each message
```

### Pros & Cons
- ✅ **Pros:** Handles both formatted and unformatted responses, predictable maximum wait time
- ❌ **Cons:** May show content prematurely on slow streams, timeout needs tuning

### Code Structure
```typescript
interface TimeoutHybridState {
  buffer: string;
  timeoutId: NodeJS.Timeout | null;
  hasStartedParsing: boolean;
  startTime: number;
  timeoutDuration: number;
}

function processTimeoutHybrid(chunk: string, state: TimeoutHybridState) {
  state.buffer += chunk;
  
  if (!state.hasStartedParsing) {
    if (!state.timeoutId) {
      state.timeoutId = setTimeout(() => {
        state.hasStartedParsing = true;
        forceParseBuffer(state.buffer);
      }, state.timeoutDuration);
    }
    
    if (hasThinkingMarker(state.buffer)) {
      clearTimeout(state.timeoutId);
      state.hasStartedParsing = true;
      return parseContent(state.buffer);
    }
    
    return showLoading();
  }
  
  return parseContent(state.buffer);
}
```

---

## Algorithm 6: Model-Specific State Machine

### Description
Implement a state machine that transitions based on model-specific patterns and markers.

### Implementation Steps
```
States: WAITING → THINKING → CONTENT → COMPLETE

1. Start in WAITING state
2. WAITING state:
   - Show loading indicator
   - Buffer all content
   - Look for model-specific patterns
3. THINKING state (when marker found):
   - Parse thinking section
   - Show "AI is thinking..." message
4. CONTENT state (after thinking):
   - Parse and display answer section
   - Stream content in real-time
5. COMPLETE state:
   - Finalize message
   - Save to history
```

### Pros & Cons
- ✅ **Pros:** Most accurate for each model type, clean state management, extensible
- ❌ **Cons:** Requires model-specific implementations, more complex setup

### Code Structure
```typescript
enum StreamState {
  WAITING = 'waiting',
  THINKING = 'thinking',
  CONTENT = 'content',
  COMPLETE = 'complete'
}

interface StateMachineState {
  currentState: StreamState;
  buffer: string;
  thinkingContent: string;
  displayContent: string;
  modelId: string;
}

const MODEL_PATTERNS = {
  'deepseek-r1': {
    thinkingStart: /<\/think>|Thinking:/,
    thinkingEnd: /Answer:|Title:/,
    contentStart: /Answer:/
  },
  'llava': {
    thinkingStart: /Thinking:/,
    thinkingEnd: /Response:/,
    contentStart: /Response:/
  }
};

function processStateMachine(chunk: string, state: StateMachineState) {
  state.buffer += chunk;
  const patterns = MODEL_PATTERNS[state.modelId];
  
  switch(state.currentState) {
    case StreamState.WAITING:
      if (patterns.thinkingStart.test(state.buffer)) {
        state.currentState = StreamState.THINKING;
        return { type: 'thinking', content: parseThinking(state.buffer) };
      }
      return { type: 'loading' };
      
    case StreamState.THINKING:
      if (patterns.contentStart.test(state.buffer)) {
        state.currentState = StreamState.CONTENT;
        return { type: 'content', content: parseContent(state.buffer) };
      }
      return { type: 'thinking', content: parseThinking(state.buffer) };
      
    case StreamState.CONTENT:
      return { type: 'content', content: parseContent(state.buffer) };
      
    case StreamState.COMPLETE:
      return { type: 'complete', content: state.displayContent };
  }
}
```

---

## Algorithm 7: Parallel Processing with Web Worker

### Description
Offload pattern detection to a Web Worker for non-blocking stream processing.

### Implementation Steps
```
1. Main thread: Buffer chunks and show loading
2. Web Worker: Continuously analyze buffer
3. Worker signals when thinking section detected
4. Main thread then:
   - Receives signal from worker
   - Starts parsing and displaying
5. Worker continues monitoring for section transitions
```

### Pros & Cons
- ✅ **Pros:** Non-blocking UI, smooth performance, can handle complex pattern matching
- ❌ **Cons:** Additional complexity with worker communication, debugging challenges

### Code Structure
```typescript
// Main Thread
interface WorkerState {
  worker: Worker;
  buffer: string;
  isParsing: boolean;
}

function initWorkerProcessing(state: WorkerState) {
  state.worker = new Worker('pattern-detector.worker.js');
  
  state.worker.onmessage = (event) => {
    if (event.data.type === 'thinking-detected') {
      state.isParsing = true;
      startParsing(state.buffer);
    }
  };
}

function processWithWorker(chunk: string, state: WorkerState) {
  state.buffer += chunk;
  state.worker.postMessage({ type: 'analyze', buffer: state.buffer });
  
  return state.isParsing ? parseContent(state.buffer) : showLoading();
}

// Worker Thread (pattern-detector.worker.js)
self.onmessage = (event) => {
  if (event.data.type === 'analyze') {
    const hasThinking = detectThinkingSection(event.data.buffer);
    if (hasThinking) {
      self.postMessage({ type: 'thinking-detected' });
    }
  }
};
```

---

## Algorithm 8: Chunked Validation

### Description
Validate buffer content against expected structure before beginning parsing.

### Implementation Steps
```
1. Define minimum valid response size (e.g., 50 chars)
2. Buffer until minimum size reached
3. Validate buffer contains expected structure:
   - Has opening marker OR
   - Has "Thinking:" prefix OR
   - Matches model's expected format
4. If valid: begin parsing
5. If invalid but size > threshold: parse as fallback
```

### Pros & Cons
- ✅ **Pros:** Balances speed and accuracy, prevents premature parsing
- ❌ **Cons:** May miss edge cases, requires defining validation rules

### Code Structure
```typescript
interface ValidationState {
  buffer: string;
  minSize: number;
  maxSizeForValidation: number;
  isValidated: boolean;
}

const VALIDATION_RULES = [
  (buffer: string) => buffer.includes('</think>'),
  (buffer: string) => buffer.includes('Thinking:'),
  (buffer: string) => buffer.match(/<｜begin of thinking｜>/)
];

function processWithValidation(chunk: string, state: ValidationState) {
  state.buffer += chunk;
  
  if (!state.isValidated) {
    if (state.buffer.length < state.minSize) {
      return showLoading();
    }
    
    const isValid = VALIDATION_RULES.some(rule => rule(state.buffer));
    
    if (isValid || state.buffer.length > state.maxSizeForValidation) {
      state.isValidated = true;
      return parseContent(state.buffer);
    }
    
    return showLoading();
  }
  
  return parseContent(state.buffer);
}
```

---

## Recommended Implementation Strategy

### Primary Approach: Model-Specific State Machine + Timeout Hybrid

For the best balance of accuracy, reliability, and user experience, combine **Algorithm 6** (Model-Specific State Machine) with **Algorithm 5** (Timeout-Based Hybrid) as a fallback.

### Implementation Plan

```typescript
interface CombinedStrategy {
  stateMachine: StateMachineState;
  timeout: TimeoutHybridState;
  activeStrategy: 'state-machine' | 'timeout';
}

function processCombined(chunk: string, state: CombinedStrategy) {
  // Try state machine first
  const stateMachineResult = processStateMachine(chunk, state.stateMachine);
  
  // If state machine hasn't detected anything and timeout expires, switch to timeout strategy
  if (state.stateMachine.currentState === StreamState.WAITING && 
      Date.now() - state.timeout.startTime > state.timeout.timeoutDuration) {
    state.activeStrategy = 'timeout';
    return processTimeoutHybrid(chunk, state.timeout);
  }
  
  return stateMachineResult;
}
```

### Key Features

1. **Model-Specific Detection**: Accurate pattern matching for each AI model
2. **Timeout Fallback**: Ensures response even if patterns aren't detected
3. **Progressive Loading States**: Different messages based on processing stage
4. **Performance Optimization**: Caches pattern detection per model

### Configuration

```typescript
const STREAM_CONFIG = {
  deepseek: {
    patterns: {
      thinking: [/</think>/, /Thinking:/, /<｜begin of thinking｜>/],
      content: [/Answer:/, /Title:/]
    },
    timeout: 3000,
    minBufferSize: 50
  },
  llava: {
    patterns: {
      thinking: [/Thinking:/],
      content: [/Response:/]
    },
    timeout: 2000,
    minBufferSize: 30
  },
  default: {
    patterns: {
      thinking: [/Thinking:/],
      content: [/Answer:/]
    },
    timeout: 2500,
    minBufferSize: 40
  }
};
```

## Performance Considerations

### Memory Usage
- Buffer size limits: Cap at 100KB to prevent memory issues
- Sliding window: Use 500-1000 character windows
- Clear buffers after processing complete

### CPU Usage
- Pattern matching: Use compiled regex patterns
- Throttle detection: Check every 100ms max
- Worker threads: Offload heavy processing

### Network Considerations
- Handle slow connections: Increase timeout for slow streams
- Chunk size: Process minimum 10 bytes at a time
- Connection drops: Gracefully handle incomplete streams

## Testing Strategy

### Unit Tests
```typescript
describe('Stream Parser', () => {
  it('should detect thinking section markers', () => {
    const buffer = 'Some content </think> Thinking: ...';
    expect(hasThinkingMarker(buffer)).toBe(true);
  });
  
  it('should timeout after specified duration', async () => {
    const state = createTimeoutState(1000);
    await delay(1100);
    expect(state.hasStartedParsing).toBe(true);
  });
  
  it('should handle model-specific patterns', () => {
    const deepseekBuffer = '</think> Answer: Hello';
    const llavaBuffer = 'Thinking: Processing... Response: Hi';
    
    expect(detectModelPattern('deepseek', deepseekBuffer)).toBe(true);
    expect(detectModelPattern('llava', llavaBuffer)).toBe(true);
  });
});
```

### Integration Tests
- Test with real streaming responses
- Simulate slow connections
- Test pattern detection across chunk boundaries
- Verify state transitions

### Edge Cases to Test
1. Empty responses
2. Responses without thinking sections
3. Malformed markers
4. Very long pre-thinking content
5. Network interruptions
6. Rapid message sending
7. Model switching mid-stream

## Monitoring & Metrics

### Key Metrics to Track
```typescript
interface StreamMetrics {
  timeToFirstByte: number;
  timeToThinkingDetection: number;
  timeToContentDisplay: number;
  bufferSize: number;
  parseAttempts: number;
  strategyUsed: 'state-machine' | 'timeout' | 'fallback';
  modelId: string;
}
```

### Logging Points
1. Stream start
2. First chunk received
3. Thinking section detected
4. Content parsing begun
5. Stream complete
6. Any errors or timeouts

## Future Enhancements

1. **Machine Learning Detection**: Train a model to detect section boundaries
2. **Adaptive Timeouts**: Adjust timeout based on historical response times
3. **Streaming Compression**: Compress buffer data for large responses
4. **Pattern Caching**: Cache successful patterns per model/prompt type
5. **Predictive Loading**: Pre-detect likely response structure based on prompt
6. **A/B Testing**: Test different algorithms with user segments
7. **Custom Markers**: Allow users to define custom section markers

## Conclusion

The recommended approach combines the accuracy of model-specific state machines with the reliability of timeout-based fallbacks. This ensures:

- ✅ Accurate detection of thinking sections
- ✅ Graceful handling of edge cases
- ✅ Good user experience with progressive feedback
- ✅ Extensibility for new models
- ✅ Performance optimization

Implementation should start with the combined strategy and iterate based on real-world usage patterns and user feedback.