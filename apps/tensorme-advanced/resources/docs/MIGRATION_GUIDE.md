# Migration Guide: From Old Hooks to New Redux Architecture

## Overview
This guide shows exactly how to migrate your existing components from the old hook-based system to the new Redux architecture. Both systems will work in parallel during the migration.

## Current vs New Architecture Comparison

### Before (Old System)
```typescript
// Old way - Multiple separate hooks
function ChatPage() {
  const { userId } = useUser();
  const { personas, selectedPersona, handleSelectPersona } = usePersonas();
  const { models, selectedModel, selectModel } = useModels();
  const { domains, selectedDomain, selectDomain } = useDomains();
  const { isMemoryEnabled, toggleMemory } = useMemory();
  const {
    inputValue,
    error,
    handleInputChange,
    handleSubmit,
    // ... 10+ more returns
  } = useChatCompletion(
    chatSessions,      // Props passed down
    currentChatId,     // Props passed down  
    setChatSessions,   // Props passed down
    selectedPersona,   // Props passed down
    selectedModel,     // Props passed down
    selectedDomain,    // Props passed down
    isMemoryEnabled,   // Props passed down
  );

  // 15+ props passed to components
  return (
    <ChatHeader
      personas={personas}
      selectedPersona={selectedPersona}
      onSelectPersona={handleSelectPersona}
      models={models}
      selectedModel={selectedModel}
      onSelectModel={selectModel}
      // ... 9+ more props
    />
  );
}
```

### After (New System)
```typescript
// New way - Single hook with everything
function ChatPage() {
  const {
    // State
    currentSession,
    allSessions, 
    user,
    currentModel,
    currentDomain,
    supportsResearch,
    // Actions
    handleNewChat,
    handleSelectChat,
    handleSendMessage,
    // ... everything you need
  } = useNewChat();

  // Clean component tree - no prop drilling
  return (
    <div>
      <ChatHeader /> {/* Gets data from Redux internally */}
      <MessageList messages={currentSession?.messages || []} />
      <ChatInputForm onSubmit={handleSendMessage} />
    </div>
  );
}
```

## Step-by-Step Migration

### Step 1: Update Main Page Component

**Replace this old code in `src/app/page.tsx`:**
```typescript
// OLD - Remove all these imports
import { useUser } from '@/hooks/useUser';
import { useChatSessions } from '@/hooks/useChatSessions';
import { useChatCompletion } from '@/hooks/useChatCompletion';
import { usePersonas } from '@/hooks/usePersonas';
import { useModels } from '@/hooks/useModels';
import { useDomains } from '@/hooks/useDomains';

export default function ChatPage() {
  const { userId } = useUser();
  const { personas, selectedPersona, handleSelectPersona } = usePersonas();
  const { models, selectedModel, selectModel } = useModels();
  const { domains, selectedDomain, selectDomain } = useDomains();
  const { isMemoryEnabled, toggleMemory } = useMemory();
  // ... all the old hooks
}
```

**With this new code:**
```typescript
// NEW - Single import and hook
import { useNewChat } from '@/hooks/useNewChat';

export default function ChatPage() {
  const {
    // All the state you need
    currentSession,
    allSessions,
    isSidebarOpen,
    isResearchMode,
    user,
    currentModel,
    currentDomain,
    supportsResearch,
    
    // All the actions you need
    handleNewChat,
    handleSelectChat,
    handleDeleteChat,
    handleRenameChat,
    handleSendMessage,
    handleToggleSidebar,
    handleToggleResearch,
  } = useNewChat();

  // Use the data directly - no prop passing needed
  const isLoading = currentSession?.isLoading || false;
  const currentMessages = currentSession?.messages || [];
  
  return (
    // Your JSX here - much cleaner without props
  );
}
```

### Step 2: Update ChatHeader Component

**Old ChatHeader usage:**
```typescript
<ChatHeader
  isSidebarOpen={isSidebarOpen}
  toggleSidebar={toggleSidebar}
  currentChatId={currentChatId}
  chatSessions={chatSessions}
  personas={personas}
  selectedPersona={selectedPersona}
  onSelectPersona={handleSelectPersona}
  models={models}
  selectedModel={selectedModel}
  onSelectModel={selectModel}
  domains={domains}
  selectedDomain={selectedDomain}
  onSelectDomain={selectDomain}
  isMemoryEnabled={isMemoryEnabled}
  onToggleMemory={toggleMemory}
/>
```

**New ChatHeader usage:**
```typescript
<ChatHeader /> {/* That's it! No props needed */}
```

**Update ChatHeader component itself:**
```typescript
// src/components/chat/ChatHeader.tsx
import { useAppDispatch, useAppSelector } from '@/hooks/redux';
import { selectCurrentModel, selectCurrentDomain, selectAllModels, selectAllDomains } from '@/store/slices/configSlice';
import { selectCurrentSession, selectAllSessions, selectIsSidebarOpen } from '@/store/slices/chatSlice';

const ChatHeader: React.FC = () => {
  const dispatch = useAppDispatch();
  
  // Get data directly from Redux
  const currentSession = useAppSelector(selectCurrentSession);
  const isSidebarOpen = useAppSelector(selectIsSidebarOpen);
  const models = useAppSelector(selectAllModels);
  const selectedModel = useAppSelector(selectCurrentModel);
  const domains = useAppSelector(selectAllDomains);
  const selectedDomain = useAppSelector(selectCurrentDomain);
  
  // Actions dispatch directly to Redux
  const handleToggleSidebar = () => dispatch(toggleSidebar());
  const handleSelectModel = (modelId: string) => dispatch(selectModel(modelId));
  const handleSelectDomain = (domainId: string) => dispatch(selectDomain(domainId));

  return (
    // Your JSX here
  );
};
```

### Step 3: Update Sidebar Component

**Old Sidebar usage:**
```typescript
<Sidebar
  userId={userId}
  isSidebarOpen={isSidebarOpen}
  toggleSidebar={toggleSidebar}
  chatSessions={chatSessions}
  currentChatId={currentChatId}
  onNewChat={handleNewChat}
  onSelectChat={handleSelectChat}
  onDeleteChat={handleDeleteChat}
  onRenameChat={handleRenameChat}
/>
```

**New Sidebar usage:**
```typescript
<Sidebar /> {/* No props needed */}
```

**Update Sidebar component:**
```typescript
// src/components/sidebar/Sidebar.tsx
import { useAppDispatch, useAppSelector } from '@/hooks/redux';
import { selectAllSessions, selectCurrentSession, selectIsSidebarOpen } from '@/store/slices/chatSlice';
import { selectUser } from '@/store/slices/userSlice';

const Sidebar: React.FC = () => {
  const dispatch = useAppDispatch();
  
  // Get data from Redux
  const user = useAppSelector(selectUser);
  const allSessions = useAppSelector(selectAllSessions);
  const currentSession = useAppSelector(selectCurrentSession);
  const isSidebarOpen = useAppSelector(selectIsSidebarOpen);
  
  // Actions
  const handleNewChat = () => {
    const sessionId = crypto.randomUUID();
    dispatch(createSession({ id: sessionId, name: `Chat ${allSessions.length + 1}` }));
  };
  
  const handleSelectChat = (chatId: string) => {
    dispatch(selectSession(chatId));
  };

  return (
    // Your JSX here
  );
};
```

### Step 4: Update MessageList Component  

**Old MessageList usage:**
```typescript
<MessageList 
  messages={currentMessages} 
  messagesEndRef={messagesEndRef}
  handleSelectResponse={handleSelectResponse}
  isLoading={isLoading}
  loadingMessage={loadingMessage}
/>
```

**New MessageList usage (two options):**

**Option A: Keep props (easier migration):**
```typescript
<MessageList 
  messages={currentSession?.messages || []}
  isLoading={currentSession?.isLoading || false}
/>
```

**Option B: Use Redux internally (cleaner):**
```typescript
<MessageList /> {/* Gets data from Redux internally */}

// Update MessageList component:
const MessageList: React.FC = () => {
  const currentSession = useAppSelector(selectCurrentSession);
  const streamState = useAppSelector(selectStreamState(currentSession?.id || ''));
  
  const messages = currentSession?.messages || [];
  const isLoading = currentSession?.isLoading || false;
  
  return (
    // Your JSX here
  );
};
```

### Step 5: Update ChatInputForm

**Old ChatInputForm usage:**
```typescript
<ChatInputForm 
  inputValue={inputValue} 
  onInputChange={handleInputChange} 
  onSubmit={handleFormSubmit} 
  inputRef={inputRef} 
  isLoading={isLoading}
  isResearchMode={isResearchMode}
  onResearchToggle={handleResearchToggle}
  showResearchToggle={supportsResearch}
/>
```

**New ChatInputForm usage:**
```typescript
<ChatInputForm onSubmit={handleSendMessage} />

// Update ChatInputForm component:
const ChatInputForm: React.FC<{ onSubmit: (message: string) => void }> = ({ onSubmit }) => {
  const [inputValue, setInputValue] = useState('');
  const isResearchMode = useAppSelector(selectIsResearchMode);
  const currentModel = useAppSelector(selectCurrentModel);
  const dispatch = useAppDispatch();
  
  const supportsResearch = currentModel ? modelSupportsResearch(currentModel.id) : false;
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputValue.trim()) {
      onSubmit(inputValue.trim());
      setInputValue('');
    }
  };
  
  const handleResearchToggle = () => {
    dispatch(toggleResearchMode());
  };

  return (
    // Your JSX here
  );
};
```

## Migration Strategy

### Phase 1: Parallel Implementation (Recommended)
```typescript
// Keep old system working while adding new
function ChatPage() {
  // OLD SYSTEM (keep working)
  const oldUser = useUser();
  const oldChat = useChatCompletion(/* ... */);
  
  // NEW SYSTEM (add alongside)  
  const newChat = useNewChat();
  
  // Feature flag to switch between systems
  const useNewSystem = process.env.NEXT_PUBLIC_USE_NEW_SYSTEM === 'true';
  
  if (useNewSystem) {
    // Use new system
    return <NewChatInterface {...newChat} />;
  } else {
    // Use old system  
    return <OldChatInterface {...oldChat} />;
  }
}
```

### Phase 2: Component-by-Component Migration
```typescript
// Migrate one component at a time
function ChatPage() {
  // Still using old hooks for most things
  const oldHooks = useOldSystem();
  
  // But migrate ChatHeader to new system
  return (
    <div>
      <ChatHeader /> {/* Now uses Redux */}
      <OldSidebar {...oldHooks} /> {/* Still uses old props */}
      <OldMessageList {...oldHooks} /> {/* Still uses old props */}
    </div>
  );
}
```

### Phase 3: Complete Migration
```typescript
// Everything uses new system
function ChatPage() {
  const chat = useNewChat();
  
  return (
    <div>
      <ChatHeader />
      <Sidebar />
      <MessageList />
      <ChatInputForm onSubmit={chat.handleSendMessage} />
    </div>
  );
}
```

## Debugging Migration Issues

### Common Issues & Solutions

#### 1. Component Not Re-rendering
**Problem:** Component doesn't update when Redux state changes
**Solution:** Make sure you're using `useAppSelector()` 
```typescript
// ❌ Wrong - won't trigger re-renders
const sessions = store.getState().chat.sessions;

// ✅ Correct - will trigger re-renders  
const sessions = useAppSelector(selectAllSessions);
```

#### 2. Actions Not Working
**Problem:** Dispatch calls don't update state
**Solution:** Make sure you're using `useAppDispatch()`
```typescript
// ❌ Wrong - not the typed dispatch
const dispatch = useDispatch();

// ✅ Correct - typed dispatch  
const dispatch = useAppDispatch();
```

#### 3. State Not Persisting
**Problem:** State resets on page refresh
**Solution:** Make sure async thunks are being called
```typescript
// Make sure this runs on app startup
useEffect(() => {
  dispatch(initializeUser());
  dispatch(loadConfigurations());  
}, []);
```

#### 4. Selectors Returning Undefined
**Problem:** Selectors return undefined unexpectedly
**Solution:** Add proper null checks
```typescript
// ❌ Can crash if no current session
const messages = useAppSelector(state => 
  state.chat.sessions[state.chat.currentSessionId].messages
);

// ✅ Safe selector
const messages = useAppSelector(state => {
  const sessionId = state.chat.currentSessionId;
  return sessionId ? state.chat.sessions[sessionId]?.messages || [] : [];
});
```

## Testing Migration

### How to Test Each Phase

#### 1. Test Redux Store
```typescript
// In browser console:
console.log(window.__REDUX_DEVTOOLS_EXTENSION__); // Should exist
console.log(store.getState()); // Should show your state
```

#### 2. Test Actions  
```typescript
// In component:
const dispatch = useAppDispatch();

const testAction = () => {
  dispatch(createSession({ id: 'test', name: 'Test Chat' }));
  console.log('Action dispatched');
};
```

#### 3. Test Selectors
```typescript
// In component:
const currentSession = useAppSelector(selectCurrentSession);
console.log('Current session:', currentSession);
```

#### 4. Test Persistence
```typescript
// Create session, refresh page, check if it's still there
const handleTest = () => {
  dispatch(createSession({ id: 'persist-test', name: 'Persist Test' }));
  setTimeout(() => {
    window.location.reload(); // Should restore after reload
  }, 1000);
};
```

## Rollback Plan

If you need to rollback during migration:

### Emergency Rollback
```typescript
// 1. Comment out new imports
// import { useNewChat } from '@/hooks/useNewChat';

// 2. Uncomment old imports  
import { useUser } from '@/hooks/useUser';
import { useChatCompletion } from '@/hooks/useChatCompletion';
// ... etc

// 3. Revert component to old prop-passing pattern
// 4. Remove AppProviders from layout.tsx if needed
```

### Gradual Rollback
```typescript
// Use feature flag to disable new system
const useNewSystem = false; // Set to false

if (useNewSystem) {
  return <NewSystem />;
} else {
  return <OldSystem />; // Fallback to old system
}
```

This migration guide allows you to move at your own pace while keeping everything working!