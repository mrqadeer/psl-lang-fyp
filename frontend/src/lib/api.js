const API_URL = import.meta.env.VITE_API_URL || '/api';

/**
 * Base API class for making requests to the backend
 */
export class Api {
  static async request(endpoint, options = {}) {
    const url = `${API_URL}${endpoint}`;
    
    const defaultOptions = {
      headers: {
        'Content-Type': 'application/json',
      },
    };
    
    const fetchOptions = {
      ...defaultOptions,
      ...options,
      headers: {
        ...defaultOptions.headers,
        ...(options.headers || {}),
      },
    };
    
    try {
      const response = await fetch(url, fetchOptions);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'An error occurred');
      }
      
      return await response.json();
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }
  
  static get(endpoint) {
    return this.request(endpoint, { method: 'GET' });
  }
  
  static post(endpoint, data) {
    return this.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }
}

/**
 * Sign Language Recognition API
 */
export class SignLanguageApi {
  static startOpenpose() {
    return Api.post('/start-openpose', {});
  }
  
  static stopOpenpose() {
    return Api.post('/stop-openpose', {});
  }
  
  static capture(duration, mode = 'alphabet') {
    return Api.post('/capture', { duration, mode });
  }
  
  static getFileCount() {
    return Api.get('/get-file-count');
  }
  
  static deleteImage(imageId) {
    return Api.post('/delete-image', { image_id: imageId });
  }
  
  static saveLabel(label) {
    return Api.post('/save-label', { label });
  }
  
  static retrain() {
    return Api.post('/retrain', {});
  }
  
  static infer(mode = 'alphabet', speechEnabled = false) {
    return Api.post('/infer', { 
      image_base64: '', // Not used in the current backend implementation
      mode,
      speech_enabled: speechEnabled
    });
  }
  
  static startLearning() {
    return Api.post('/start-learning', {});
  }
  
  static getAlphabet(index) {
    return Api.get(`/get-alphabet/${index}`);
  }
  
  static skipSign() {
    return Api.post('/skip-sign', {});
  }
}
