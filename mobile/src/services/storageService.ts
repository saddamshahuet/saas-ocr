/**
 * Storage Service for offline data persistence
 */
import {MMKV} from 'react-native-mmkv';

// Initialize MMKV storage
const storage = new MMKV({
  id: 'saas-ocr-storage',
  encryptionKey: 'your-encryption-key-here', // Should be generated securely
});

class StorageService {
  // General purpose storage
  set(key: string, value: any): void {
    try {
      const jsonValue = JSON.stringify(value);
      storage.set(key, jsonValue);
    } catch (error) {
      console.error('Storage set error:', error);
    }
  }

  get(key: string): any {
    try {
      const jsonValue = storage.getString(key);
      return jsonValue ? JSON.parse(jsonValue) : null;
    } catch (error) {
      console.error('Storage get error:', error);
      return null;
    }
  }

  delete(key: string): void {
    try {
      storage.delete(key);
    } catch (error) {
      console.error('Storage delete error:', error);
    }
  }

  // Offline queue management
  addToOfflineQueue(item: any): void {
    const queue = this.getOfflineQueue();
    queue.push({
      ...item,
      timestamp: Date.now(),
      id: `offline_${Date.now()}_${Math.random()}`,
    });
    this.set('offline_queue', queue);
  }

  getOfflineQueue(): any[] {
    return this.get('offline_queue') || [];
  }

  removeFromOfflineQueue(id: string): void {
    const queue = this.getOfflineQueue();
    const filtered = queue.filter((item) => item.id !== id);
    this.set('offline_queue', filtered);
  }

  clearOfflineQueue(): void {
    this.set('offline_queue', []);
  }

  // Document cache
  cacheDocument(documentId: string, data: any): void {
    this.set(`doc_${documentId}`, data);
  }

  getCachedDocument(documentId: string): any {
    return this.get(`doc_${documentId}`);
  }

  // Job cache
  cacheJob(jobId: string, data: any): void {
    this.set(`job_${jobId}`, data);
  }

  getCachedJob(jobId: string): any {
    return this.get(`job_${jobId}`);
  }

  // Settings
  setSetting(key: string, value: any): void {
    this.set(`setting_${key}`, value);
  }

  getSetting(key: string, defaultValue?: any): any {
    const value = this.get(`setting_${key}`);
    return value !== null ? value : defaultValue;
  }

  // Clear all data
  clearAll(): void {
    storage.clearAll();
  }
}

export const storageService = new StorageService();

export const initializeStorage = async () => {
  // Perform any initialization tasks
  console.log('Storage initialized');
};
