/**
 * API Client Service
 */
import axios, {AxiosInstance, AxiosRequestConfig} from 'axios';
import {storageService} from './storageService';

const API_BASE_URL = 'https://api.saas-ocr.com'; // Replace with your API URL

class APIClient {
  private client: AxiosInstance;
  private authToken: string | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor
    this.client.interceptors.request.use(
      async (config) => {
        // Add auth token if available
        if (this.authToken) {
          config.headers.Authorization = `Bearer ${this.authToken}`;
        }

        return config;
      },
      (error) => {
        return Promise.reject(error);
      },
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => response,
      async (error) => {
        // Handle 401 errors (unauthorized)
        if (error.response?.status === 401) {
          // Token expired, logout
          // This will be handled by the auth store
        }

        return Promise.reject(error);
      },
    );
  }

  setAuthToken(token: string | null) {
    this.authToken = token;
  }

  async get<T = any>(url: string, config?: AxiosRequestConfig) {
    return this.client.get<T>(url, config);
  }

  async post<T = any>(url: string, data?: any, config?: AxiosRequestConfig) {
    return this.client.post<T>(url, data, config);
  }

  async put<T = any>(url: string, data?: any, config?: AxiosRequestConfig) {
    return this.client.put<T>(url, data, config);
  }

  async patch<T = any>(url: string, data?: any, config?: AxiosRequestConfig) {
    return this.client.patch<T>(url, data, config);
  }

  async delete<T = any>(url: string, config?: AxiosRequestConfig) {
    return this.client.delete<T>(url, config);
  }

  async uploadFile(
    url: string,
    file: {uri: string; type: string; name: string},
    additionalData?: any,
  ) {
    const formData = new FormData();
    formData.append('file', file as any);

    if (additionalData) {
      Object.keys(additionalData).forEach((key) => {
        formData.append(key, additionalData[key]);
      });
    }

    return this.client.post(url, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  }
}

export const apiClient = new APIClient();
