# Add your context providers here

Example context structure:

```tsx
import { createContext, useContext, ReactNode } from 'react';

interface YourContextType {
  // Define your context type
}

const YourContext = createContext<YourContextType | undefined>(undefined);

export function YourProvider({ children }: { children: ReactNode }) {
  return (
    <YourContext.Provider value={{}}>
      {children}
    </YourContext.Provider>
  );
}

export function useYourContext() {
  const context = useContext(YourContext);
  if (!context) throw new Error('useYourContext must be used within YourProvider');
  return context;
}
```
