/**
 * SaaS OCR Mobile App
 * Enterprise document scanning and data extraction
 */

import React, {useEffect} from 'react';
import {StatusBar, LogBox} from 'react-native';
import {NavigationContainer} from '@react-navigation/native';
import {QueryClient, QueryClientProvider} from 'react-query';
import {GestureHandlerRootView} from 'react-native-gesture-handler';
import Toast from 'react-native-toast-message';

import AppNavigator from './src/navigation/AppNavigator';
import {useAuthStore} from './src/store/authStore';
import {initializeNotifications} from './src/services/notificationService';
import {initializeStorage} from './src/services/storageService';

// Ignore specific warnings
LogBox.ignoreLogs([
  'Non-serializable values were found in the navigation state',
]);

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

const App = () => {
  const {initialize, isInitialized} = useAuthStore();

  useEffect(() => {
    // Initialize app
    const initApp = async () => {
      try {
        await initializeStorage();
        await initializeNotifications();
        await initialize();
      } catch (error) {
        console.error('App initialization error:', error);
      }
    };

    initApp();
  }, [initialize]);

  if (!isInitialized) {
    // Show splash screen or loading indicator
    return null;
  }

  return (
    <GestureHandlerRootView style={{flex: 1}}>
      <QueryClientProvider client={queryClient}>
        <NavigationContainer>
          <StatusBar barStyle="dark-content" backgroundColor="#FFFFFF" />
          <AppNavigator />
          <Toast />
        </NavigationContainer>
      </QueryClientProvider>
    </GestureHandlerRootView>
  );
};

export default App;
