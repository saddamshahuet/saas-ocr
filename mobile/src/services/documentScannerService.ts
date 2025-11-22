/**
 * Document Scanner Service with edge detection
 */
import {Platform, PermissionsAndroid} from 'react-native';
import DocumentScanner from 'react-native-document-scanner-plugin';
import {launchCamera, launchImageLibrary} from 'react-native-image-picker';
import {check, request, PERMISSIONS, RESULTS} from 'react-native-permissions';

interface ScannedDocument {
  uri: string;
  width: number;
  height: number;
  type: string;
  fileName: string;
}

class DocumentScannerService {
  /**
   * Request camera permission
   */
  async requestCameraPermission(): Promise<boolean> {
    try {
      if (Platform.OS === 'android') {
        const granted = await PermissionsAndroid.request(
          PermissionsAndroid.PERMISSIONS.CAMERA,
          {
            title: 'Camera Permission',
            message: 'SaaS OCR needs access to your camera to scan documents',
            buttonNeutral: 'Ask Me Later',
            buttonNegative: 'Cancel',
            buttonPositive: 'OK',
          },
        );
        return granted === PermissionsAndroid.RESULTS.GRANTED;
      } else {
        const result = await request(PERMISSIONS.IOS.CAMERA);
        return result === RESULTS.GRANTED;
      }
    } catch (error) {
      console.error('Camera permission error:', error);
      return false;
    }
  }

  /**
   * Scan document with edge detection
   */
  async scanDocument(): Promise<ScannedDocument | null> {
    try {
      const hasPermission = await this.requestCameraPermission();

      if (!hasPermission) {
        throw new Error('Camera permission denied');
      }

      const {scannedImages} = await DocumentScanner.scanDocument({
        maxNumDocuments: 1,
        letUserAdjustCrop: true,
        croppedImageQuality: 100,
      });

      if (scannedImages && scannedImages.length > 0) {
        const scanned = scannedImages[0];

        return {
          uri: scanned,
          width: 0,
          height: 0,
          type: 'image/jpeg',
          fileName: `scan_${Date.now()}.jpg`,
        };
      }

      return null;
    } catch (error) {
      console.error('Document scan error:', error);
      throw error;
    }
  }

  /**
   * Take a photo of a document
   */
  async takePhoto(): Promise<ScannedDocument | null> {
    try {
      const hasPermission = await this.requestCameraPermission();

      if (!hasPermission) {
        throw new Error('Camera permission denied');
      }

      const result = await launchCamera({
        mediaType: 'photo',
        quality: 1,
        includeBase64: false,
        saveToPhotos: false,
      });

      if (result.assets && result.assets.length > 0) {
        const asset = result.assets[0];

        return {
          uri: asset.uri!,
          width: asset.width || 0,
          height: asset.height || 0,
          type: asset.type || 'image/jpeg',
          fileName: asset.fileName || `photo_${Date.now()}.jpg`,
        };
      }

      return null;
    } catch (error) {
      console.error('Take photo error:', error);
      throw error;
    }
  }

  /**
   * Pick image from gallery
   */
  async pickFromGallery(): Promise<ScannedDocument | null> {
    try {
      const result = await launchImageLibrary({
        mediaType: 'photo',
        quality: 1,
        includeBase64: false,
      });

      if (result.assets && result.assets.length > 0) {
        const asset = result.assets[0];

        return {
          uri: asset.uri!,
          width: asset.width || 0,
          height: asset.height || 0,
          type: asset.type || 'image/jpeg',
          fileName: asset.fileName || `photo_${Date.now()}.jpg`,
        };
      }

      return null;
    } catch (error) {
      console.error('Pick from gallery error:', error);
      throw error;
    }
  }

  /**
   * Upload scanned document to server
   */
  async uploadDocument(
    document: ScannedDocument,
    organizationId: number,
    workspaceId?: number,
  ): Promise<any> {
    const {apiClient} = require('./apiClient');

    const file = {
      uri: document.uri,
      type: document.type,
      name: document.fileName,
    };

    const additionalData: any = {
      organization_id: organizationId,
    };

    if (workspaceId) {
      additionalData.workspace_id = workspaceId;
    }

    const response = await apiClient.uploadFile('/api/v1/jobs', file, additionalData);

    return response.data;
  }

  /**
   * Process multiple documents in batch
   */
  async processBatch(
    documents: ScannedDocument[],
    organizationId: number,
    workspaceId?: number,
  ): Promise<any[]> {
    const results = [];

    for (const doc of documents) {
      try {
        const result = await this.uploadDocument(doc, organizationId, workspaceId);
        results.push(result);
      } catch (error) {
        console.error('Batch upload error:', error);
        results.push({error: true, document: doc});
      }
    }

    return results;
  }
}

export const documentScannerService = new DocumentScannerService();
