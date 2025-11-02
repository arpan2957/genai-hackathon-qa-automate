// Configuration file for the frontend application
// This centralizes all configuration including backend URL

// Backend URL configuration with debugging
const getBackendUrl = () => {
  const envUrl = process.env.REACT_APP_BACKEND_URL;
  
  // Use environment variable for fallback URL too, to avoid embedding localhost in production
  const fallbackUrl = process.env.REACT_APP_FALLBACK_URL || 
                      (process.env.NODE_ENV === 'development' 
                        ? process.env.REACT_APP_DEV_BACKEND_URL || 'https://backend-dev-not-configured.example.com'
                        : 'https://backend-not-configured.example.com');
  
  // Debug logging (only in development)
  if (process.env.NODE_ENV === 'development') {
    console.log('🔧 Backend URL Configuration:');
    console.log('  REACT_APP_BACKEND_URL:', envUrl);
    console.log('  Fallback URL:', fallbackUrl);
    console.log('  Final URL:', envUrl || fallbackUrl);
  }
  
  // In production, environment variable should always be set
  if (!envUrl && process.env.NODE_ENV === 'production') {
    console.error('❌ REACT_APP_BACKEND_URL not set in production build!');
    console.error('Using fallback:', fallbackUrl);
  }
  
  return envUrl || fallbackUrl;
};

// Firebase configuration
const getFirebaseConfig = () => {
  return {
    apiKey: process.env.REACT_APP_FIREBASE_API_KEY,
    authDomain: process.env.REACT_APP_FIREBASE_AUTH_DOMAIN,
    projectId: process.env.REACT_APP_FIREBASE_PROJECT_ID,
    storageBucket: process.env.REACT_APP_FIREBASE_STORAGE_BUCKET,
    messagingSenderId: process.env.REACT_APP_FIREBASE_MESSAGING_SENDER_ID,
    appId: process.env.REACT_APP_FIREBASE_APP_ID
  };
};

// Export configuration
export const config = {
  BACKEND_URL: getBackendUrl(),
  FIREBASE_CONFIG: getFirebaseConfig(),
  
  // Environment info
  NODE_ENV: process.env.NODE_ENV,
  IS_PRODUCTION: process.env.NODE_ENV === 'production',
  IS_DEVELOPMENT: process.env.NODE_ENV === 'development',
  
  // Debug info (for troubleshooting)
  DEBUG_INFO: {
    allEnvVars: Object.keys(process.env)
      .filter(key => key.startsWith('REACT_APP_'))
      .reduce((obj, key) => {
        obj[key] = process.env[key];
        return obj;
      }, {}),
    buildTime: new Date().toISOString()
  }
};

// Log configuration in development
if (process.env.NODE_ENV === 'development') {
  console.log('🚀 App Configuration:', config);
}

export default config;
