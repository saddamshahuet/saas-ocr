/**
 * Authentication Store using Zustand
 */
import {create} from 'zustand';
import {persist, createJSONStorage} from 'zustand/middleware';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Keychain from 'react-native-keychain';

import {authService} from '../services/authService';
import {apiClient} from '../services/apiClient';

interface User {
  id: number;
  email: string;
  full_name: string | null;
  organization_id: number | null;
  tier: string;
  is_verified: boolean;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isInitialized: boolean;
  biometricEnabled: boolean;

  // Actions
  initialize: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  refreshToken: () => Promise<void>;
  enableBiometric: () => Promise<void>;
  disableBiometric: () => Promise<void>;
  loginWithBiometric: () => Promise<void>;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      isInitialized: false,
      biometricEnabled: false,

      initialize: async () => {
        try {
          // Try to load token from secure storage
          const credentials = await Keychain.getGenericPassword();

          if (credentials) {
            const token = credentials.password;
            apiClient.setAuthToken(token);

            // Fetch user profile
            const user = await authService.getCurrentUser();

            set({
              user,
              token,
              isAuthenticated: true,
              isInitialized: true,
            });
          } else {
            set({isInitialized: true});
          }
        } catch (error) {
          console.error('Initialize error:', error);
          set({isInitialized: true});
        }
      },

      login: async (email: string, password: string) => {
        try {
          const response = await authService.login(email, password);
          const {token, user} = response;

          // Store token in secure storage
          await Keychain.setGenericPassword('auth_token', token);

          // Set token in API client
          apiClient.setAuthToken(token);

          set({
            user,
            token,
            isAuthenticated: true,
          });
        } catch (error) {
          throw error;
        }
      },

      logout: async () => {
        try {
          // Clear secure storage
          await Keychain.resetGenericPassword();

          // Clear API client token
          apiClient.setAuthToken(null);

          set({
            user: null,
            token: null,
            isAuthenticated: false,
            biometricEnabled: false,
          });
        } catch (error) {
          console.error('Logout error:', error);
        }
      },

      register: async (email: string, password: string, fullName?: string) => {
        try {
          const response = await authService.register(email, password, fullName);
          const {token, user} = response;

          // Store token
          await Keychain.setGenericPassword('auth_token', token);
          apiClient.setAuthToken(token);

          set({
            user,
            token,
            isAuthenticated: true,
          });
        } catch (error) {
          throw error;
        }
      },

      refreshToken: async () => {
        try {
          const newToken = await authService.refreshToken();

          if (newToken) {
            await Keychain.setGenericPassword('auth_token', newToken);
            apiClient.setAuthToken(newToken);

            set({token: newToken});
          }
        } catch (error) {
          console.error('Token refresh error:', error);
          await get().logout();
        }
      },

      enableBiometric: async () => {
        try {
          const state = get();

          if (state.token) {
            // Store biometric flag
            await AsyncStorage.setItem('biometric_enabled', 'true');

            set({biometricEnabled: true});
          }
        } catch (error) {
          console.error('Enable biometric error:', error);
          throw error;
        }
      },

      disableBiometric: async () => {
        try {
          await AsyncStorage.removeItem('biometric_enabled');
          set({biometricEnabled: false});
        } catch (error) {
          console.error('Disable biometric error:', error);
        }
      },

      loginWithBiometric: async () => {
        try {
          const ReactNativeBiometrics = require('react-native-biometrics').default;
          const rnBiometrics = new ReactNativeBiometrics();

          const {success} = await rnBiometrics.simplePrompt({
            promptMessage: 'Authenticate to login',
          });

          if (success) {
            // Get stored token
            const credentials = await Keychain.getGenericPassword();

            if (credentials) {
              const token = credentials.password;
              apiClient.setAuthToken(token);

              const user = await authService.getCurrentUser();

              set({
                user,
                token,
                isAuthenticated: true,
              });
            }
          }
        } catch (error) {
          console.error('Biometric login error:', error);
          throw error;
        }
      },
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => AsyncStorage),
      partialize: (state) => ({
        // Only persist non-sensitive data
        biometricEnabled: state.biometricEnabled,
      }),
    },
  ),
);
