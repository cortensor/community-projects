import { configureStore } from '@reduxjs/toolkit';
import chatReducer from './slices/chatSlice';
import userReducer from './slices/userSlice';
import configReducer from './slices/configSlice';

export const store = configureStore({
  reducer: {
    chat: chatReducer,
    user: userReducer,
    config: configReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        // Ignore these action types for non-serializable data
        ignoredActions: ['chat/streamUpdate', 'chat/addMessage'],
        // Ignore these field paths in all actions
        ignoredActionPaths: ['payload.timestamp', 'payload.file'],
        // Ignore these paths in the state
        ignoredPaths: ['chat.activeStreams'],
      },
    }),
  devTools: process.env.NODE_ENV !== 'production',
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;