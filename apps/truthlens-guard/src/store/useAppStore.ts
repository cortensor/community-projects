import { create } from 'zustand';

export interface FactCheck {
  id: string;
  claim: string;
  type: 'text' | 'url' | 'headline';
  source?: string;
  checkedAt: Date;
  status: 'analyzing' | 'completed' | 'error';
  credibilityScore?: number;
  analysis?: {
    isCredible: boolean;
    confidence: number;
    consensus: string;
    supportingSources: Array<{
      url: string;
      title: string;
      credibility: number;
      excerpt: string;
    }>;
    minerResponses: Array<{
      minerId: string;
      score: number;
      reasoning: string;
      sources: string[];
    }>;
  };
}

interface AppState {
  // Theme
  isDarkMode: boolean;
  toggleDarkMode: () => void;

  // User
  user: {
    id?: string;
    name?: string;
    email?: string;
    avatar?: string;
  } | null;
  setUser: (user: AppState['user']) => void;

  // Fact Checks
  factChecks: FactCheck[];
  addFactCheck: (factCheck: FactCheck) => void;
  updateFactCheck: (id: string, updates: Partial<FactCheck>) => void;
  removeFactCheck: (id: string) => void;

  // Current analysis
  currentAnalysis: string | null;
  setCurrentAnalysis: (id: string | null) => void;

  // UI State
  sidebarCollapsed: boolean;
  setSidebarCollapsed: (collapsed: boolean) => void;
}

export const useAppStore = create<AppState>((set, get) => ({
  // Theme
  isDarkMode: true,
  toggleDarkMode: () => {
    const { isDarkMode } = get();
    const newMode = !isDarkMode;
    set({ isDarkMode: newMode });
    
    // Apply to document
    if (!newMode) {
      document.documentElement.classList.add('light');
    } else {
      document.documentElement.classList.remove('light');
    }
  },

  // User
  user: null,
  setUser: (user) => set({ user }),

  // Fact Checks
  factChecks: [],
  addFactCheck: (factCheck) => {
    set((state) => ({
      factChecks: [factCheck, ...state.factChecks]
    }));
  },
  updateFactCheck: (id, updates) => {
    set((state) => ({
      factChecks: state.factChecks.map((factCheck) =>
        factCheck.id === id ? { ...factCheck, ...updates } : factCheck
      )
    }));
  },
  removeFactCheck: (id) => {
    set((state) => ({
      factChecks: state.factChecks.filter((factCheck) => factCheck.id !== id)
    }));
  },

  // Current analysis
  currentAnalysis: null,
  setCurrentAnalysis: (id) => set({ currentAnalysis: id }),

  // UI State
  sidebarCollapsed: false,
  setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
}));