# Function Interaction Map

## Overview
This document maps all function interactions in the new Redux architecture, showing what calls what and in what order.

## 1. Hook Dependencies & Call Chain

### useNewChat() Hook - Main Orchestrator
```
useNewChat() 
├── useAppDispatch() → Returns typed dispatch function
├── useAppSelector(selectCurrentSession) → Gets current chat session
├── useAppSelector(selectAllSessions) → Gets all chat sessions  
├── useAppSelector(selectIsSidebarOpen) → Gets sidebar state
├── useAppSelector(selectUser) → Gets user data
├── useAppSelector(selectCurrentModel) → Gets selected model
├── useAppSelector(selectCurrentDomain) → Gets selected domain
├── useAppSelector(selectCurrentPersona) → Gets selected persona
└── useAppSelector(selectIsMemoryEnabled) → Gets memory setting

├── useEffect(() => {
│   dispatch(initializeUser()) → Loads/creates user
│   dispatch(loadConfigurations()) → Loads models/domains/personas
│ }, [])
│
├── useEffect(() => {
│   if (user.userId) dispatch(loadChatSessions(userId))
│ }, [user.userId]) → Loads chat sessions when user ready
│
└── useEffect(() => {
    if (user.userId && allSessions.length > 0) {
      dispatch(saveChatSessions({ userId, sessions }))
    }
  }, [allSessions]) → Auto-saves sessions when they change
```

### Action Handlers in useNewChat()
```
handleNewChat()
├── crypto.randomUUID() → Generate session ID
├── dispatch(createSession({ id, name })) → Create new session in Redux
└── dispatch(toggleSidebar()) → Close sidebar on mobile

handleSelectChat(chatId)
├── dispatch(selectSession(chatId)) → Set active session
└── dispatch(toggleSidebar()) → Close sidebar on mobile

handleDeleteChat(chatId)
└── dispatch(deleteSession(chatId)) → Remove session from Redux

handleRenameChat(chatId, newName)
└── dispatch(renameSession({ id: chatId, name: newName })) → Update name

handleSendMessage(content)
├── crypto.randomUUID() → Generate message ID
├── dispatch(addMessage({ sessionId, message })) → Add user message
└── dispatch(sendMessage({ 
     sessionId, message, modelId, domainId, persona 
   })) → Send to API and stream response

handleToggleSidebar()
└── dispatch(toggleSidebar()) → Toggle sidebar visibility

handleToggleResearch()
└── if (supportsResearch) dispatch(toggleResearchMode()) → Toggle research
```

## 2. Redux Action Flow

### Synchronous Actions (Reducers)
```
chatSlice.ts - Synchronous Actions:

createSession(state, action)
├── state.sessions[id] = newSessionObject
└── state.currentSessionId = id

selectSession(state, action)
└── state.currentSessionId = action.payload

deleteSession(state, action)
├── delete state.sessions[sessionId]
└── state.currentSessionId = findNextSession() || null

addMessage(state, action)
├── session = state.sessions[sessionId]
├── session.messages.push(newMessage)
└── session.timestamp = Date.now()

startStream(state, action)
├── state.activeStreams[sessionId] = streamState
└── state.sessions[sessionId].isLoading = true

appendStreamChunk(state, action)
├── stream.buffer += chunk
├── stream.chunks.push(chunk)
└── lastMessage.content = stream.buffer

endStream(state, action)
├── lastMessage.content = finalContent
├── session.isLoading = false
└── delete state.activeStreams[sessionId]

toggleSidebar(state)
└── state.ui.isSidebarOpen = !state.ui.isSidebarOpen

toggleResearchMode(state)
└── state.ui.isResearchMode = !state.ui.isResearchMode
```

### Asynchronous Actions (Thunks)
```
chatSlice.ts - Async Thunks:

loadChatSessions(userId)
├── localStorage.getItem(`chat_sessions_${userId}`)
├── JSON.parse(stored) || {}
└── return sessions → Goes to fulfilled handler

saveChatSessions({ userId, sessions })
├── localStorage.setItem(`chat_sessions_${userId}`, JSON.stringify(sessions))
└── return sessions

sendMessage(params, { dispatch })
├── dispatch(startStream({ sessionId })) → Start loading state
├── fetch('/api/conversation', { body: params }) → API call
├── response.body.getReader() → Get stream reader
└── return reader → Goes to fulfilled handler
```

### User & Config Thunks
```
userSlice.ts - Async Thunks:

initializeUser()
├── localStorage.getItem('user')
├── if (saved) return JSON.parse(saved)
├── else crypto.randomUUID() → Generate new user ID
├── localStorage.setItem('user', newUser)
└── return newUser

connectWallet()
├── walletConnection.connect() → Connect to wallet
├── localStorage.setItem('user', updatedUser)
└── return { address, isConnected: true }

configSlice.ts - Async Thunks:

loadConfigurations()
├── import('@/lib/models') → Get AVAILABLE_MODELS
├── import('@/lib/domains') → Get DOMAIN_CONFIGS  
├── localStorage.getItem('app_config') → Get saved preferences
└── return { models, domains, personas, ...savedConfig }
```

## 3. Component → Hook → Action Chain

### ChatInputForm Component Flow
```
ChatInputForm.tsx
├── onSubmit={(e) => handleFormSubmit(e)}
    └── handleFormSubmit(e)
        └── handleSendMessage(inputValue) → From useNewChat()
            ├── dispatch(addMessage()) → Add user message immediately
            └── dispatch(sendMessage()) → Send to API
                ├── dispatch(startStream()) → Show loading
                ├── fetch('/api/conversation') → API call
                ├── processStreamResponse() → Handle streaming
                └── dispatch(endStream()) → Complete
```

### Sidebar Component Flow  
```
Sidebar.tsx
├── onNewChat={() => handleNewChatAndToggle()}
│   └── handleNewChatAndToggle()
│       ├── handleNewChat() → From useNewChat()
│       │   ├── dispatch(createSession())
│       │   └── dispatch(toggleSidebar())
│       └── if (mobile) toggleSidebar()
│
├── onSelectChat={(chatId) => handleSelectChatAndToggle(chatId)}
│   └── handleSelectChatAndToggle(chatId)
│       ├── handleSelectChat(chatId) → From useNewChat()  
│       │   ├── dispatch(selectSession(chatId))
│       │   └── dispatch(toggleSidebar())
│       └── if (mobile) toggleSidebar()
│
├── onDeleteChat={(chatId, event) => handleDeleteChat(chatId)}
│   └── handleDeleteChat(chatId) → From useNewChat()
│       └── dispatch(deleteSession(chatId))
│
└── onRenameChat={(chatId, newName) => handleRenameChat(chatId, newName)}
    └── handleRenameChat(chatId, newName) → From useNewChat()
        └── dispatch(renameSession({ id: chatId, name: newName }))
```

### ChatHeader Component Flow
```
ChatHeader.tsx
├── toggleSidebar={() => handleToggleSidebar()}
│   └── handleToggleSidebar() → From useNewChat()
│       └── dispatch(toggleSidebar())
│
├── onSelectModel={(modelId) => dispatch(selectModel(modelId))}
│   └── dispatch(selectModel(modelId)) → Direct dispatch to configSlice
│
├── onSelectDomain={(domainId) => dispatch(selectDomain(domainId))} 
│   └── dispatch(selectDomain(domainId)) → Direct dispatch to configSlice
│
├── onSelectPersona={(personaId) => dispatch(selectPersona(personaId))}
│   └── dispatch(selectPersona(personaId)) → Direct dispatch to configSlice
│
└── onToggleMemory={() => dispatch(toggleMemory())}
    └── dispatch(toggleMemory()) → Direct dispatch to configSlice
```

## 4. Service Layer Function Calls

### Service Hook Usage
```
useLogger() 
└── useService<ILogger>(TYPES.Logger)
    └── container.get<ILogger>(TYPES.Logger)
        └── Returns Logger instance
            ├── debug(message, context)
            ├── info(message, context)  
            ├── warn(message, context)
            └── error(message, error, context)
                ├── console.error(formatted)
                └── sendToMonitoring() → Sentry integration

useEventBus()
└── useService<IEventBus>(TYPES.EventBus)
    └── container.get<IEventBus>(TYPES.EventBus)
        └── Returns EventBus instance
            ├── emit(event, data) → Notify all listeners
            ├── on(event, callback) → Add listener
            ├── once(event, callback) → Add one-time listener
            └── off(event, callback) → Remove listener

useHttpClient()
└── useService<IHttpClient>(TYPES.HttpClient)
    └── container.get<IHttpClient>(TYPES.HttpClient)
        └── Returns HttpClient instance
            ├── get(url, config) → GET request
            ├── post(url, data, config) → POST request
            ├── put(url, data, config) → PUT request
            └── delete(url, config) → DELETE request
```

### Service Implementation Calls
```
Logger.ts
├── debug() → if (level <= DEBUG) console.debug()
├── info() → if (level <= INFO) console.info()
├── warn() → if (level <= WARN) console.warn()
└── error() → 
    ├── if (level <= ERROR) console.error()
    └── if (production) sendToMonitoring()
        └── window.Sentry.captureException()

EventBus.ts
├── emit(event, data)
│   ├── listeners = this.listeners.get(event)
│   └── listeners.forEach(callback => callback(data))
├── on(event, callback)
│   ├── this.listeners.get(event).add(callback)
│   └── return unsubscribe function
└── off(event, callback)
    └── this.listeners.get(event).delete(callback)

HttpClient.ts
├── get/post/put/delete() → this.request()
└── request(url, config)
    ├── fetch(fullUrl, config)
    ├── parse response (JSON or text)
    ├── if (!response.ok) throw Error
    └── return { data, status, headers }
```

## 5. API Route Function Chain

### /api/conversation Route Flow
```
/api/conversation/route.ts
├── POST(request) → Main handler
├── request.json() → Parse request body  
├── getModelConfig(modelId) → Get model configuration
├── getPromptService(modelId) → Get model-specific prompt service
├── promptService.buildPrompt({ messages, persona, domainContext })
├── fetch(CORTENSOR_API_URL/completions) → External API call
├── if (ENABLE_STREAMING) return response.body → Stream response
└── else simulateStreaming() → Convert to streaming format
```

### Prompt Service Chain
```
getPromptService(modelId)
├── promptServices[modelId] → Get service from registry
└── return deepseekPromptService || llavaPromptService

DeepSeekPromptService.buildPrompt({ messages, persona, domainContext })
├── buildAdvancedPromptPlain(messages, persona, domainContext)
└── return formatted prompt string

LlavaPromptService.buildPrompt({ messages, persona, domainContext, historySummary })
├── buildLlavaPrompt(messages, persona, historySummary, domainContext) 
└── return formatted prompt string
```

## 6. Error Handling Function Chain

### Error Boundary Flow
```
ErrorBoundary.tsx
├── componentDidCatch(error, errorInfo)
├── if (error instanceof AppError) → Handle known errors
│   └── console.error(error.toJSON())
├── else → Handle unknown errors  
│   └── console.error(error.message)
├── sendToMonitoring(error, errorInfo)
│   └── window.Sentry.captureException()
└── setState({ hasError: true, error })
    └── render() → Show DefaultErrorFallback
        ├── Try Again → this.handleReset()
        │   └── setState({ hasError: false })
        └── Refresh Page → window.location.reload()
```

### Error Classes Hierarchy
```
AppError (abstract base)
├── ValidationError → 400 status
├── AuthenticationError → 401 status  
├── NetworkError → 503 status
├── StreamError → 500 status + streamId
├── TaskError → 500 status + taskId
└── ConfigurationError → 500 status

Each error:
├── constructor() → Set id, timestamp, code, message
├── toJSON() → Serialize for logging
└── Error.captureStackTrace() → Capture stack trace
```

## 7. Selector Chain & State Access

### Redux Selectors
```
selectCurrentSession(state)
├── state.chat.currentSessionId → Get current session ID
└── state.chat.sessions[currentSessionId] → Get session object

selectAllSessions(state)
└── Object.values(state.chat.sessions) → Convert to array

selectStreamState(sessionId)(state) 
└── state.chat.activeStreams[sessionId] → Get stream state

selectCurrentModel(state)
├── state.config.selectedModelId → Get selected model ID
└── state.config.models.find(m => m.id === selectedModelId) → Find model

selectCurrentDomain(state)
├── state.config.selectedDomainId → Get selected domain ID
└── state.config.domains.find(d => d.id === selectedDomainId) → Find domain
```

### useAppSelector Usage Chain
```
Component uses useAppSelector(selectCurrentSession)
├── useAppSelector() → Uses TypedUseSelectorHook<RootState>
├── useSelector() → React-Redux hook
├── selectCurrentSession(state) → Selector function
└── Returns current session object → Component re-renders if changed
```

## 8. Complete Function Call Example

### User Sends Message - Complete Chain
```
User types "Hello" and presses Enter
    ↓
ChatInputForm.onSubmit(e)
    ↓
handleFormSubmit(e) 
    ↓
handleSendMessage("Hello") [from useNewChat()]
    ↓
dispatch(addMessage({
  sessionId: "session-123",
  message: { id: "msg-456", role: "user", content: "Hello" }
}))
    ↓ 
chatSlice.addMessage reducer
    ├── state.sessions["session-123"].messages.push(newMessage)
    └── state.sessions["session-123"].timestamp = Date.now()
    ↓
useAppSelector(selectCurrentSession) detects change
    ↓
MessageList component re-renders with new message
    ↓
dispatch(sendMessage({
  sessionId: "session-123", 
  message: "Hello",
  modelId: "deepseek-r1"
}))
    ↓
sendMessage async thunk
    ├── dispatch(startStream({ sessionId: "session-123" }))
    │   ├── chatSlice.startStream reducer
    │   │   ├── state.activeStreams["session-123"] = { ... }
    │   │   └── state.sessions["session-123"].isLoading = true
    │   └── MessageList shows loading indicator
    ├── fetch('/api/conversation', { 
    │     method: 'POST',
    │     body: JSON.stringify({ messages, modelId, ... })
    │   })
    │   ├── POST handler in /api/conversation/route.ts
    │   ├── getModelConfig("deepseek-r1") 
    │   ├── getPromptService("deepseek-r1")
    │   ├── promptService.buildPrompt({ messages, ... })
    │   ├── fetch(CORTENSOR_API_URL)  
    │   └── return streaming response
    ├── response.body.getReader()
    └── return reader
    ↓
sendMessage.fulfilled handler
    ├── Stream processing loop begins
    ├── reader.read() → Get chunk
    ├── dispatch(appendStreamChunk({ sessionId, chunk }))
    │   ├── chatSlice.appendStreamChunk reducer
    │   │   ├── stream.buffer += chunk
    │   │   └── lastMessage.content = stream.buffer  
    │   └── MessageList updates with streaming text
    ├── Continue until done
    └── dispatch(endStream({ sessionId }))
        ├── chatSlice.endStream reducer
        │   ├── lastMessage.content = finalContent
        │   ├── session.isLoading = false
        │   └── delete activeStreams[sessionId]
        └── MessageList removes loading indicator
```

This complete function interaction map shows exactly which functions call which other functions, making it easy to trace any issue or understand how features work together.