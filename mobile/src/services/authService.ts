/**
 * Authentication Service
 */
import {apiClient} from './apiClient';

interface LoginResponse {
  token: string;
  user: {
    id: number;
    email: string;
    full_name: string | null;
    organization_id: number | null;
    tier: string;
    is_verified: boolean;
  };
}

class AuthService {
  async login(email: string, password: string): Promise<LoginResponse> {
    const response = await apiClient.post('/api/v1/login', {
      email,
      password,
    });

    return {
      token: response.data.access_token,
      user: response.data.user,
    };
  }

  async register(
    email: string,
    password: string,
    fullName?: string,
  ): Promise<LoginResponse> {
    const response = await apiClient.post('/api/v1/register', {
      email,
      password,
      full_name: fullName,
    });

    return {
      token: response.data.access_token,
      user: response.data.user,
    };
  }

  async getCurrentUser() {
    const response = await apiClient.get('/api/v1/me');
    return response.data;
  }

  async refreshToken(): Promise<string | null> {
    try {
      const response = await apiClient.post('/api/v1/refresh');
      return response.data.access_token;
    } catch (error) {
      return null;
    }
  }

  async resetPassword(email: string): Promise<void> {
    await apiClient.post('/api/v1/reset-password', {email});
  }

  async verifyEmail(token: string): Promise<void> {
    await apiClient.post('/api/v1/verify-email', {token});
  }
}

export const authService = new AuthService();
