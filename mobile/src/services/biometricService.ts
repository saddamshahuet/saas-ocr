/**
 * Biometric Authentication Service
 */
import ReactNativeBiometrics, {BiometryTypes} from 'react-native-biometrics';

const rnBiometrics = new ReactNativeBiometrics({
  allowDeviceCredentials: true,
});

class BiometricService {
  /**
   * Check if biometric authentication is available
   */
  async isBiometricAvailable(): Promise<boolean> {
    try {
      const {available, biometryType} = await rnBiometrics.isSensorAvailable();

      if (available) {
        console.log(`Biometric available: ${biometryType}`);
        return true;
      }

      return false;
    } catch (error) {
      console.error('Biometric check error:', error);
      return false;
    }
  }

  /**
   * Get biometry type
   */
  async getBiometryType(): Promise<BiometryTypes | null> {
    try {
      const {biometryType} = await rnBiometrics.isSensorAvailable();
      return biometryType || null;
    } catch (error) {
      return null;
    }
  }

  /**
   * Authenticate with biometrics
   */
  async authenticate(promptMessage: string = 'Authenticate'): Promise<boolean> {
    try {
      const {success} = await rnBiometrics.simplePrompt({
        promptMessage,
      });

      return success;
    } catch (error) {
      console.error('Biometric auth error:', error);
      return false;
    }
  }

  /**
   * Create biometric keys for signature
   */
  async createKeys(): Promise<boolean> {
    try {
      const {publicKey} = await rnBiometrics.createKeys();
      console.log('Public key created:', publicKey);
      return true;
    } catch (error) {
      console.error('Create keys error:', error);
      return false;
    }
  }

  /**
   * Delete biometric keys
   */
  async deleteKeys(): Promise<boolean> {
    try {
      const {keysDeleted} = await rnBiometrics.deleteKeys();
      return keysDeleted;
    } catch (error) {
      console.error('Delete keys error:', error);
      return false;
    }
  }

  /**
   * Create signature with biometric authentication
   */
  async createSignature(payload: string): Promise<string | null> {
    try {
      const {success, signature} = await rnBiometrics.createSignature({
        promptMessage: 'Sign to authenticate',
        payload,
      });

      if (success && signature) {
        return signature;
      }

      return null;
    } catch (error) {
      console.error('Create signature error:', error);
      return null;
    }
  }
}

export const biometricService = new BiometricService();
