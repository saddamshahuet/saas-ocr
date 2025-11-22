/**
 * Push Notification Service
 */
import messaging from '@react-native-firebase/messaging';
import notifee, {AndroidImportance, EventType} from '@notifee/react-native';
import {Platform} from 'react-native';

class NotificationService {
  /**
   * Initialize push notifications
   */
  async initialize(): Promise<void> {
    try {
      // Request permission
      await this.requestPermission();

      // Get FCM token
      const token = await messaging().getToken();
      console.log('FCM Token:', token);

      // Listen for foreground messages
      messaging().onMessage(async (remoteMessage) => {
        console.log('Foreground message:', remoteMessage);
        await this.displayNotification(remoteMessage);
      });

      // Handle background messages
      messaging().setBackgroundMessageHandler(async (remoteMessage) => {
        console.log('Background message:', remoteMessage);
      });

      // Handle notification interactions
      notifee.onForegroundEvent(({type, detail}) => {
        if (type === EventType.PRESS) {
          console.log('Notification pressed:', detail);
          this.handleNotificationPress(detail);
        }
      });

      notifee.onBackgroundEvent(async ({type, detail}) => {
        if (type === EventType.PRESS) {
          console.log('Background notification pressed:', detail);
        }
      });
    } catch (error) {
      console.error('Notification initialization error:', error);
    }
  }

  /**
   * Request notification permission
   */
  async requestPermission(): Promise<boolean> {
    try {
      const authStatus = await messaging().requestPermission();
      const enabled =
        authStatus === messaging.AuthorizationStatus.AUTHORIZED ||
        authStatus === messaging.AuthorizationStatus.PROVISIONAL;

      if (enabled) {
        console.log('Notification permission granted');
      }

      return enabled;
    } catch (error) {
      console.error('Permission request error:', error);
      return false;
    }
  }

  /**
   * Display local notification
   */
  async displayNotification(message: any): Promise<void> {
    try {
      const channelId = await notifee.createChannel({
        id: 'default',
        name: 'Default Channel',
        importance: AndroidImportance.HIGH,
      });

      await notifee.displayNotification({
        title: message.notification?.title || 'SaaS OCR',
        body: message.notification?.body || '',
        android: {
          channelId,
          importance: AndroidImportance.HIGH,
          pressAction: {
            id: 'default',
          },
        },
        ios: {
          sound: 'default',
          foregroundPresentationOptions: {
            alert: true,
            badge: true,
            sound: true,
          },
        },
        data: message.data,
      });
    } catch (error) {
      console.error('Display notification error:', error);
    }
  }

  /**
   * Handle notification press
   */
  handleNotificationPress(detail: any): void {
    const {notification, pressAction} = detail;

    // Navigate based on notification data
    if (notification?.data?.type === 'job_completed') {
      // Navigate to job details
      const jobId = notification.data.job_id;
      console.log('Navigate to job:', jobId);
    }
  }

  /**
   * Subscribe to topic
   */
  async subscribeToTopic(topic: string): Promise<void> {
    try {
      await messaging().subscribeToTopic(topic);
      console.log(`Subscribed to topic: ${topic}`);
    } catch (error) {
      console.error('Subscribe to topic error:', error);
    }
  }

  /**
   * Unsubscribe from topic
   */
  async unsubscribeFromTopic(topic: string): Promise<void> {
    try {
      await messaging().unsubscribeFromTopic(topic);
      console.log(`Unsubscribed from topic: ${topic}`);
    } catch (error) {
      console.error('Unsubscribe from topic error:', error);
    }
  }

  /**
   * Send FCM token to backend
   */
  async sendTokenToBackend(userId: number): Promise<void> {
    try {
      const token = await messaging().getToken();
      const {apiClient} = require('./apiClient');

      await apiClient.post('/api/v1/push-tokens', {
        user_id: userId,
        token,
        platform: Platform.OS,
      });

      console.log('Token sent to backend');
    } catch (error) {
      console.error('Send token error:', error);
    }
  }
}

export const notificationService = new NotificationService();

export const initializeNotifications = async () => {
  await notificationService.initialize();
};
