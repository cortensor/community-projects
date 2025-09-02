import { createSlice, PayloadAction, createAsyncThunk } from '@reduxjs/toolkit';
import { createSelector } from 'reselect';

interface UserState {
  userId: string | null;
  address: string | null;
  isConnected: boolean;
  preferences: {
    theme: 'light' | 'dark' | 'system';
    fontSize: 'small' | 'medium' | 'large';
    soundEnabled: boolean;
    autoSave: boolean;
  };
  isLoading: boolean;
}

const initialState: UserState = {
  userId: null,
  address: null,
  isConnected: false,
  preferences: {
    theme: 'system',
    fontSize: 'medium',
    soundEnabled: true,
    autoSave: true,
  },
  isLoading: false,
};

// Async thunks
export const initializeUser = createAsyncThunk(
  'user/initialize',
  async () => {
    // Try to restore user from localStorage
    const savedUser = localStorage.getItem('user');
    if (savedUser) {
      return JSON.parse(savedUser);
    }
    
    // Generate new user ID if none exists
    const userId = crypto.randomUUID();
    const userData = { userId, address: null, isConnected: false };
    localStorage.setItem('user', JSON.stringify(userData));
    return userData;
  }
);

export const connectWallet = createAsyncThunk(
  'user/connectWallet',
  async () => {
    // This would integrate with your Web3 wallet connection logic
    // For now, we'll simulate the connection
    try {
      // In real implementation, you'd use your wallet connection logic here
      const address = '0x' + Array.from({length: 40}, () => Math.floor(Math.random() * 16).toString(16)).join('');
      const userData = { address, isConnected: true };
      
      // Update localStorage
      const currentUser = JSON.parse(localStorage.getItem('user') || '{}');
      const updatedUser = { ...currentUser, ...userData };
      localStorage.setItem('user', JSON.stringify(updatedUser));
      
      return userData;
    } catch (error) {
      throw new Error('Failed to connect wallet');
    }
  }
);

export const savePreferences = createAsyncThunk(
  'user/savePreferences',
  async (preferences: Partial<UserState['preferences']>) => {
    // Save preferences to localStorage
    const currentUser = JSON.parse(localStorage.getItem('user') || '{}');
    const updatedPreferences = { ...currentUser.preferences, ...preferences };
    const updatedUser = { ...currentUser, preferences: updatedPreferences };
    localStorage.setItem('user', JSON.stringify(updatedUser));
    return updatedPreferences;
  }
);

const userSlice = createSlice({
  name: 'user',
  initialState,
  reducers: {
    setUser: (state, action: PayloadAction<{ userId: string; address?: string }>) => {
      state.userId = action.payload.userId;
      state.address = action.payload.address || null;
      state.isConnected = !!action.payload.address;
    },

    disconnect: (state) => {
      state.address = null;
      state.isConnected = false;
      // Keep userId but remove connection info from localStorage
      const userData = { userId: state.userId, address: null, isConnected: false };
      localStorage.setItem('user', JSON.stringify(userData));
    },

    updatePreferences: (state, action: PayloadAction<Partial<UserState['preferences']>>) => {
      state.preferences = { ...state.preferences, ...action.payload };
    },

    clearUser: (state) => {
      state.userId = null;
      state.address = null;
      state.isConnected = false;
      state.preferences = initialState.preferences;
      localStorage.removeItem('user');
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(initializeUser.pending, (state) => {
        state.isLoading = true;
      })
      .addCase(initializeUser.fulfilled, (state, action) => {
        state.isLoading = false;
        if (action.payload) {
          state.userId = action.payload.userId;
          state.address = action.payload.address || null;
          state.isConnected = action.payload.isConnected || false;
          state.preferences = { ...state.preferences, ...action.payload.preferences };
        }
      })
      .addCase(initializeUser.rejected, (state) => {
        state.isLoading = false;
        // Fallback to generating new user ID
        state.userId = crypto.randomUUID();
      })
      .addCase(connectWallet.pending, (state) => {
        state.isLoading = true;
      })
      .addCase(connectWallet.fulfilled, (state, action) => {
        state.isLoading = false;
        state.address = action.payload.address;
        state.isConnected = action.payload.isConnected;
      })
      .addCase(connectWallet.rejected, (state) => {
        state.isLoading = false;
        // Keep disconnected state
      })
      .addCase(savePreferences.fulfilled, (state, action) => {
        state.preferences = action.payload as UserState['preferences'];
      });
  },
});

export const { setUser, disconnect, updatePreferences, clearUser } = userSlice.actions;

export default userSlice.reducer;

// Basic selectors (input selectors)
const selectUserState = (state: { user: UserState }) => state.user;

// Memoized selectors for derived data
export const selectUser = createSelector(
  [selectUserState],
  (user) => ({
    userId: user.userId,
    address: user.address,
    isConnected: user.isConnected,
  })
);

export const selectUserId = createSelector(
  [selectUserState],
  (user) => user.userId
);

export const selectUserAddress = createSelector(
  [selectUserState],
  (user) => user.address
);

export const selectIsConnected = createSelector(
  [selectUserState],
  (user) => user.isConnected
);

export const selectPreferences = createSelector(
  [selectUserState],
  (user) => user.preferences
);

export const selectIsUserLoading = createSelector(
  [selectUserState],
  (user) => user.isLoading
);

// Derived preference selectors
export const selectTheme = createSelector(
  [selectPreferences],
  (preferences) => preferences.theme
);

export const selectFontSize = createSelector(
  [selectPreferences],
  (preferences) => preferences.fontSize
);

export const selectSoundEnabled = createSelector(
  [selectPreferences],
  (preferences) => preferences.soundEnabled
);

export const selectAutoSave = createSelector(
  [selectPreferences],
  (preferences) => preferences.autoSave
);

// Complex derived selectors
export const selectIsUserInitialized = createSelector(
  [selectUserId, selectIsUserLoading],
  (userId, isLoading) => !isLoading && userId !== null
);

export const selectCanConnectWallet = createSelector(
  [selectIsConnected, selectIsUserLoading],
  (isConnected, isLoading) => !isConnected && !isLoading
);