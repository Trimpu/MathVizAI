import React, { useState } from 'react';

const VideoPlayer = ({ videoUrl, title, onClose }) => {
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const handleVideoLoad = () => {
    console.log('✅ Video loaded successfully');
    setIsLoading(false);
  };

  const handleError = (e) => {
    console.error('❌ Video load error:', e);
    console.error('Video URL:', videoUrl);
    setError('Failed to load video. Please check if the file exists.');
    setIsLoading(false);
  };

  console.log('🎬 VideoPlayer rendering with URL:', videoUrl);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded-lg p-6 max-w-4xl max-h-[90vh] w-full mx-4 overflow-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold text-gray-800">
            {title || 'Mathematical Visualization'}
          </h3>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 text-2xl font-bold"
          >
            ×
          </button>
        </div>
        
        {/* Debug Info */}
        <div className="mb-2 text-xs text-gray-500 bg-gray-50 p-2 rounded">
          <strong>Video URL:</strong> {videoUrl}
        </div>
        
        <div className="relative bg-black rounded-lg">
          {isLoading && !error && (
            <div className="absolute inset-0 flex items-center justify-center bg-gray-900 rounded-lg z-10">
              <div className="flex items-center space-x-2">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-white"></div>
                <span className="text-white">Loading video...</span>
              </div>
            </div>
          )}
          
          {error && (
            <div className="absolute inset-0 flex items-center justify-center bg-red-50 rounded-lg z-10">
              <div className="text-center p-4">
                <div className="text-4xl mb-2">⚠️</div>
                <div className="text-red-600 font-medium">{error}</div>
              </div>
            </div>
          )}
          
          <video
            key={videoUrl}
            controls
            controlsList="nodownload"
            className="w-full max-h-[60vh] rounded-lg"
            style={{ display: 'block', backgroundColor: '#000' }}
            onLoadedData={handleVideoLoad}
            onLoadedMetadata={() => console.log('📊 Video metadata loaded')}
            onCanPlay={() => console.log('▶️ Video can play')}
            onError={handleError}
            preload="metadata"
          >
            <source src={videoUrl} type="video/mp4" />
            Your browser does not support the video tag.
          </video>
        </div>
        
        <div className="mt-4 flex justify-end space-x-2">
          <button
            onClick={() => window.open(videoUrl, '_blank')}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors duration-200"
          >
            Download Video
          </button>
          <button
            onClick={onClose}
            className="bg-gray-300 hover:bg-gray-400 text-gray-700 px-4 py-2 rounded-md text-sm font-medium transition-colors duration-200"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default VideoPlayer;

