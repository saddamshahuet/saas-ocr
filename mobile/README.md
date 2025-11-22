# SaaS OCR Mobile App

Enterprise-grade mobile application for document scanning and data extraction built with React Native.

## Features

### ✅ Implemented

- **Authentication**
  - Email/password login and registration
  - JWT token management with secure storage (Keychain)
  - Biometric authentication (Face ID, Touch ID, Fingerprint)
  - Auto token refresh
  - Persistent session

- **Document Scanning**
  - Camera integration with edge detection
  - Document scanner with automatic crop
  - Multi-document batch scanning
  - Photo capture and gallery picker
  - Real-time upload to server

- **Offline Support**
  - Encrypted local storage (MMKV)
  - Offline queue for uploads
  - Document and job caching
  - Automatic sync when online

- **Push Notifications**
  - Firebase Cloud Messaging (FCM)
  - Local notifications with Notifee
  - Job completion alerts
  - Topic-based subscriptions
  - Notification handling

- **Security**
  - Biometric authentication
  - Secure token storage
  - Encrypted local data
  - Certificate pinning ready
  - Permission management

## Tech Stack

- **React Native** 0.73
- **TypeScript** 5.3
- **React Navigation** 6.1
- **Zustand** - State management
- **React Query** - Server state
- **React Hook Form** + **Yup** - Form validation
- **MMKV** - Fast encrypted storage
- **Keychain** - Secure credentials storage
- **Firebase** - Push notifications
- **Notifee** - Local notifications
- **Vision Camera** - Camera functionality
- **Document Scanner** - Edge detection
- **Biometrics** - Face ID / Touch ID

## Prerequisites

- Node.js >= 18
- React Native CLI
- Xcode (for iOS)
- Android Studio (for Android)
- CocoaPods (for iOS dependencies)

## Installation

```bash
# Install dependencies
cd mobile
npm install

# iOS only - Install pods
cd ios && pod install && cd ..

# Android - No additional steps needed
```

## Configuration

### 1. API Configuration

Update the API base URL in `src/services/apiClient.ts`:

```typescript
const API_BASE_URL = 'https://your-api-domain.com';
```

### 2. Firebase Setup

1. Create a Firebase project
2. Add iOS and Android apps
3. Download `GoogleService-Info.plist` (iOS) and `google-services.json` (Android)
4. Place them in respective directories:
   - iOS: `ios/GoogleService-Info.plist`
   - Android: `android/app/google-services.json`

### 3. Environment Variables

Create a `.env` file:

```env
API_URL=https://api.saas-ocr.com
SENTRY_DSN=your_sentry_dsn
```

## Running the App

### iOS

```bash
npm run ios
# or
react-native run-ios --device "iPhone 15 Pro"
```

### Android

```bash
npm run android
# or
react-native run-android
```

## Project Structure

```
mobile/
├── src/
│   ├── screens/          # Screen components
│   │   ├── LoginScreen.tsx
│   │   ├── RegisterScreen.tsx
│   │   ├── HomeScreen.tsx
│   │   ├── ScanScreen.tsx
│   │   └── ...
│   ├── components/       # Reusable components
│   │   ├── Button.tsx
│   │   ├── Input.tsx
│   │   └── ...
│   ├── navigation/       # Navigation configuration
│   │   └── AppNavigator.tsx
│   ├── services/         # API and external services
│   │   ├── apiClient.ts
│   │   ├── authService.ts
│   │   ├── documentScannerService.ts
│   │   ├── notificationService.ts
│   │   ├── biometricService.ts
│   │   └── storageService.ts
│   ├── store/           # Global state management
│   │   ├── authStore.ts
│   │   └── ...
│   ├── hooks/           # Custom React hooks
│   ├── utils/           # Utility functions
│   └── assets/          # Images, fonts, etc.
├── android/             # Android native code
├── ios/                 # iOS native code
├── App.tsx             # Root component
├── package.json
└── tsconfig.json
```

## Key Services

### AuthStore (`src/store/authStore.ts`)
- User authentication state
- Login/logout functionality
- Token management
- Biometric authentication

### DocumentScannerService (`src/services/documentScannerService.ts`)
- Camera access and permissions
- Document scanning with edge detection
- Photo capture and gallery picker
- Document upload to server
- Batch processing

### StorageService (`src/services/storageService.ts`)
- Encrypted local storage
- Offline queue management
- Document and job caching
- Settings persistence

### NotificationService (`src/services/notificationService.ts`)
- Push notification handling
- Local notifications
- Topic subscriptions
- FCM token management

### BiometricService (`src/services/biometricService.ts`)
- Biometric availability check
- Face ID / Touch ID authentication
- Biometric key management

## Permissions

### iOS (`Info.plist`)
```xml
<key>NSCameraUsageDescription</key>
<string>We need camera access to scan documents</string>
<key>NSPhotoLibraryUsageDescription</key>
<string>We need photo library access to select images</string>
<key>NSFaceIDUsageDescription</key>
<string>We use Face ID for secure authentication</string>
```

### Android (`AndroidManifest.xml`)
```xml
<uses-permission android:name="android.permission.CAMERA" />
<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />
<uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" />
<uses-permission android:name="android.permission.USE_BIOMETRIC" />
<uses-permission android:name="android.permission.USE_FINGERPRINT" />
```

## Building for Production

### iOS

```bash
# Build archive
xcodebuild -workspace ios/SaasOCRMobile.xcworkspace \
  -scheme SaasOCRMobile \
  -configuration Release \
  -archivePath build/SaasOCRMobile.xcarchive \
  archive

# Export IPA
xcodebuild -exportArchive \
  -archivePath build/SaasOCRMobile.xcarchive \
  -exportPath build \
  -exportOptionsPlist exportOptions.plist
```

### Android

```bash
cd android
./gradlew assembleRelease

# APK will be at:
# android/app/build/outputs/apk/release/app-release.apk

# Or build AAB for Play Store:
./gradlew bundleRelease
# android/app/build/outputs/bundle/release/app-release.aab
```

## Testing

```bash
# Run tests
npm test

# Run with coverage
npm test -- --coverage

# E2E tests (with Detox)
npm run e2e:ios
npm run e2e:android
```

## Troubleshooting

### Common Issues

1. **Metro bundler issues**
   ```bash
   npm start -- --reset-cache
   ```

2. **iOS build fails**
   ```bash
   cd ios && pod install && cd ..
   ```

3. **Android build fails**
   ```bash
   cd android && ./gradlew clean && cd ..
   ```

## License

Proprietary - All rights reserved

## Support

For issues and questions, contact: support@saas-ocr.com
