// API service for communicating with unified Flask backend
const API_BASE_URL = 'http://localhost:5000/api';

export const mathVideoAPI = {
  // Generate video from selected text
  generateVideo: async (selectedText, options = {}) => {
    try {
      const response = await fetch(`${API_BASE_URL}/generate-video`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text: selectedText,
          quality: options.quality || 'medium_quality'
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error generating video:', error);
      throw error;
    }
  },

  // Generate video from LaTeX content
  generateFromLatex: async (latexContent, options = {}) => {
    try {
      console.log('🚀 Generating video from LaTeX:', latexContent);
      const response = await fetch(`${API_BASE_URL}/generate-from-latex`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          latex: latexContent,
          quality: options.quality || 'medium'
        })
      });

      console.log('📡 Response status:', response.status);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log('✅ Video generation response:', data);
      return data;
    } catch (error) {
      console.error('❌ Error generating video from LaTeX:', error);
      throw error;
    }
  },

  // Check generation status
  checkStatus: async (taskId) => {
    try {
      const statusUrl = `${API_BASE_URL}/video-status/${taskId}`;
      console.log('🔍 Checking video status at:', statusUrl);
      
      const response = await fetch(statusUrl);
      
      console.log('📡 Status response:', {
        url: statusUrl,
        status: response.status,
        ok: response.ok,
        statusText: response.statusText
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status} for URL: ${statusUrl}`);
      }

      const data = await response.json();
      console.log('✅ Status data received:', data);
      return data;
    } catch (error) {
      console.error('💥 Error checking status:', {
        taskId,
        url: `${API_BASE_URL}/video-status/${taskId}`,
        error: error.message
      });
      throw error;
    }
  },

  // Download video
  downloadVideo: (videoPath) => {
    const downloadUrl = `${API_BASE_URL}/video/${encodeURIComponent(videoPath)}`;
    window.open(downloadUrl, '_blank');
  },

  // Check if backend is properly set up
  checkSetup: async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/health`);
      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error checking setup:', error);
      return { status: 'error', message: 'Backend unavailable' };
    }
  },

  // List all generated videos - not implemented yet
  listVideos: async () => {
    try {
      // For now, return empty array since endpoint doesn't exist
      console.log('📋 Video listing not implemented yet');
      return [];
    } catch (error) {
      console.error('Error listing videos:', error);
      return [];
    }
  }
};

export const ocrAPI = {
  // Extract mathematical content from image data
  extractContent: async (imageData, preprocessingLevel = 'moderate') => {
    try {
      console.log('🚀 API Service: Sending extraction request', {
        endpoint: `${API_BASE_URL}/extract-latex`,
        imageDataLength: imageData?.length || 0,
        preprocessingLevel,
        imageDataValid: !!imageData && imageData.startsWith('data:image/'),
        imageDataPreview: imageData?.substring(0, 50) + '...'
      });
      
      // Prepare the request payload - backend expects 'image' file upload, not base64
      const response = await fetch(`${API_BASE_URL}/extract-latex`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          image_data: imageData,
          preprocessing_level: preprocessingLevel
        })
      });

      console.log('📡 API Service: Received response', {
        status: response.status,
        ok: response.ok
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log('✅ API Service: Parsed JSON response', {
        success: data.success,
        hasLatex: !!data.latex,
        confidence: data.confidence,
        message: data.message || 'No message'
      });
      
      // Log the actual response for debugging
      console.log('🔍 Full API Response:', data);
      
      return data;
    } catch (error) {
      console.error('💥 API Service Error:', error);
      throw error;
    }
  },

  // Check OCR system status
  checkStatus: async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/health`);
      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error checking OCR status:', error);
      return { status: 'error', message: 'OCR backend unavailable' };
    }
  },

  // List all generated videos
  listVideos: async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/list-videos`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error listing videos:', error);
      throw error;
    }
  }
};