import React, { useState } from 'react';

const InlineOcrButton = ({ 
  position, 
  viewportPosition,
  latexContent, 
  onVisualize, 
  onRemove,
  isGenerating = false 
}) => {
  const [showVideo, setShowVideo] = useState(false);
  const [videoUrl, setVideoUrl] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [generationProgress, setGenerationProgress] = useState('');
  const [showButton, setShowButton] = useState(true);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [videoPosition, setVideoPosition] = useState({ x: 0, y: 60 });

  const handleVisualize = async () => {
    if (!latexContent || isLoading) return;
    
    setIsLoading(true);
    setShowButton(false); // Hide the button during generation
    setGenerationProgress('Starting video generation...');
    
    try {
      // Import the API service
      const { mathVideoAPI } = await import('../services/api');
      
      console.log('🎬 Starting inline video generation for:', latexContent);
      
      // Generate video
      const response = await mathVideoAPI.generateVideo(latexContent, {
        difficulty: 'intermediate',
        quality: 'medium_quality'
      });
      
      if (response.success && response.task_id) {
        console.log('✅ Video generation started:', response.task_id);
        
        // Poll for completion
        await pollVideoGeneration(response.task_id);
      } else {
        console.error('❌ Video generation failed:', response);
        alert('Failed to start video generation');
      }
    } catch (error) {
      console.error('❌ Error generating video:', error);
      
      // Provide user-friendly error messages
      let message = 'Error starting video generation';
      if (error.message.includes('fetch')) {
        message = 'Unable to connect to the backend server. Please check if the server is running.';
      } else if (error.message.includes('HTTP error')) {
        message = 'Backend server error. Please try again in a moment.';
      } else {
        message += ': ' + error.message;
      }
      
      alert(message);
    } finally {
      setIsLoading(false);
      setShowButton(true); // Show button again on error
      setGenerationProgress('');
    }
  };

  const pollVideoGeneration = async (taskId) => {
    try {
      const { mathVideoAPI } = await import('../services/api');
      
      const checkStatus = async () => {
        const status = await mathVideoAPI.checkStatus(taskId);
        
        // Update progress message
        if (status.message) {
          setGenerationProgress(status.message);
        }
        
        // Handle successful completion
        if (status.success && status.status === 'completed' && (status.video_url || status.video_path)) {
          const pathPart = status.video_url ? status.video_url : `/api/videos/${encodeURIComponent(status.video_path.split('/').pop())}`;
          setVideoUrl(`http://localhost:5000${pathPart}`);
          setShowVideo(true);
          setIsLoading(false);
          setShowButton(true);
          setGenerationProgress('');
          console.log('✅ Video generation completed:', pathPart);
          return;
        }
        
        // Handle various error conditions
        if (!status.success) {
          if (status.error_type === 'task_expired') {
            console.warn('⏰ Task expired, suggesting retry');
            const retry = confirm(`${status.message}\n\nWould you like to try generating the video again?`);
            if (retry) {
              // Restart generation
              handleVisualize();
            }
            return;
          } else if (status.error_type === 'network_error') {
            console.error('🌐 Network error:', status.message);
            alert(status.message);
            return;
          } else if (status.status === 'error' || status.status === 'failed') {
            console.error('❌ Generation failed:', status.message);
            alert('Video generation failed: ' + status.message);
            return;
          }
        }
        
        // Handle ongoing generation
        if (status.status === 'generating' || status.status === 'starting') {
          console.log(`⏳ Still generating: ${status.message}`);
          setGenerationProgress(status.message || 'Generating video...');
          setTimeout(checkStatus, 3000); // Poll every 3 seconds
          return;
        }
        
        // Unknown status - provide fallback
        console.warn('⚠️ Unknown status received:', status);
        const retry = confirm('An unexpected status was received. Would you like to try again?');
        if (retry) {
          handleVisualize();
        }
      };
      
      checkStatus();
      
    } catch (error) {
      console.error('❌ Error polling video status:', error);
      alert('Error checking video generation status');
    }
  };

  const handleCloseVideo = () => {
    setShowVideo(false);
    setVideoUrl(null);
    setIsFullscreen(false);
    setVideoPosition({ x: 0, y: 60 });
  };

  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
  };

  const handleMouseDown = (e) => {
    setIsDragging(true);
    const rect = e.target.getBoundingClientRect();
    setDragOffset({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top
    });
  };

  const handleMouseMove = (e) => {
    if (!isDragging) return;
    
    const baseX = viewportPosition ? viewportPosition.x : position.x;
    const baseY = viewportPosition ? viewportPosition.y : position.y;
    
    setVideoPosition({
      x: e.clientX - baseX - dragOffset.x,
      y: e.clientY - baseY - dragOffset.y
    });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  // Add event listeners for dragging
  React.useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isDragging, dragOffset]);

  return (
    <>
      {/* Inline Button - use fixed viewport positioning when available */}


      {/* Enhanced Video Player - Draggable & Fullscreen */}
      {showVideo && videoUrl && (
        <>
          {/* Fullscreen Overlay */}
          {isFullscreen && (
            <div className="fixed inset-0 bg-black bg-opacity-90 z-[100] flex items-center justify-center">
              <div className="relative max-w-screen-lg max-h-screen-lg">
                <button
                  onClick={toggleFullscreen}
                  className="absolute top-4 right-4 z-10 bg-black bg-opacity-50 text-white p-2 rounded-full hover:bg-opacity-75 transition-all"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
                <video
                  src={videoUrl}
                  controls
                  autoPlay
                  className="w-full h-full rounded-lg"
                  style={{ maxWidth: '90vw', maxHeight: '90vh' }}
                >
                  Your browser does not support video playback.
                </video>
              </div>
            </div>
          )}

          {/* Regular Draggable Player */}
          {!isFullscreen && (
            <div 
              className={`${viewportPosition ? 'fixed' : 'absolute'} z-60 ${isDragging ? 'cursor-grabbing' : 'cursor-grab'}`}
              style={{ 
                left: (viewportPosition ? viewportPosition.x : position.x) + videoPosition.x, 
                top: (viewportPosition ? viewportPosition.y : position.y) + videoPosition.y,
                pointerEvents: 'auto'
              }}
            >
              <div className="bg-white rounded-lg shadow-2xl border-2 border-gray-300 overflow-hidden">
                {/* Video Header - Draggable Handle */}
                <div 
                  className="bg-gradient-to-r from-purple-500 to-blue-500 px-4 py-2 flex justify-between items-center cursor-grab select-none"
                  onMouseDown={handleMouseDown}
                >
                  <h3 className="text-sm font-medium text-white truncate max-w-xs">
                    🎬 Mathematical Animation
                  </h3>
                  <div className="flex space-x-2">
                    {/* Fullscreen Button */}
                    <button
                      onClick={toggleFullscreen}
                      className="p-1 hover:bg-white hover:bg-opacity-20 rounded transition-colors"
                      title="Fullscreen"
                    >
                      <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                      </svg>
                    </button>
                    {/* Close Button */}
                    <button
                      onClick={handleCloseVideo}
                      className="p-1 hover:bg-white hover:bg-opacity-20 rounded transition-colors"
                      title="Close"
                    >
                      <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                </div>
                
                {/* Video Player */}
                <div className="p-2">
                  <video
                    src={videoUrl}
                    controls
                    autoPlay
                    loop
                    className="w-96 h-72 rounded border"
                    onError={(e) => {
                      console.error('❌ Video load error:', e);
                      alert('Error loading video');
                      handleCloseVideo();
                    }}
                  >
                    Your browser does not support video playback.
                  </video>
                </div>
                
                {/* Video Footer */}
                <div className="bg-gray-50 px-4 py-2 text-xs text-gray-600 border-t">
                  <div className="flex justify-between items-center">
                    <span>LaTeX: {latexContent?.substring(0, 30)}{latexContent?.length > 30 ? '...' : ''}</span>
                    <span className="text-purple-600 font-medium">Drag to move • Click fullscreen to expand</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </>
  );
};

export default InlineOcrButton;