import React from 'react';

const LoadingModal = ({ isVisible, progress, message, onCancel }) => {
  if (!isVisible) return null;

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center z-50 p-4">
      <div className="bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 border border-purple-500/30 rounded-3xl p-10 max-w-lg w-full shadow-2xl shadow-purple-500/30">
        <div className="text-center">
          {/* Animated Icon */}
          <div className="mb-6 relative">
            <div className="relative inline-block">
              <div className="animate-spin rounded-full h-20 w-20 border-4 border-purple-500/30 border-t-purple-400 mx-auto"></div>
              <div className="absolute inset-0 animate-ping rounded-full h-20 w-20 border-4 border-purple-500/20"></div>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-3xl">🎬</span>
              </div>
            </div>
          </div>
          
          {/* Title */}
          <h3 className="text-2xl font-bold mb-3 bg-gradient-to-r from-purple-300 via-pink-300 to-purple-300 bg-clip-text text-transparent">
            Generating Mathematical Visualization
          </h3>
          
          {/* Message */}
          <p className="text-purple-200 mb-6 text-lg">
            {message || 'Processing your mathematical content...'}
          </p>
          
          {/* Progress Bar */}
          <div className="w-full bg-slate-800/50 rounded-full h-3 mb-3 overflow-hidden border border-purple-500/20">
            <div 
              className="h-3 rounded-full transition-all duration-500 ease-out bg-gradient-to-r from-purple-400 via-pink-500 to-purple-600 shadow-lg shadow-purple-500/50"
              style={{ width: `${progress || 0}%` }}
            />
          </div>
          
          {/* Progress Text */}
          <div className="text-sm text-purple-300 mb-6 font-semibold">
            {progress || 0}% Complete
          </div>
          
          {/* Info Box */}
          <div className="bg-gradient-to-r from-purple-900/50 to-pink-900/50 border border-purple-500/30 rounded-2xl p-5 mb-6 backdrop-blur-sm">
            <p className="text-sm text-purple-200 leading-relaxed">
              <span className="text-2xl mr-2">✨</span>
              AI is creating your personalized math video animation...
              <br />
              <span className="text-purple-300">This may take 1-2 minutes depending on complexity.</span>
            </p>
          </div>
          
          {/* Cancel Button */}
          {onCancel && (
            <button
              onClick={onCancel}
              className="bg-gradient-to-r from-slate-700 to-slate-800 hover:from-slate-600 hover:to-slate-700 text-white px-6 py-3 rounded-xl font-semibold shadow-lg hover:shadow-xl transform hover:scale-105 transition-all duration-200 border border-slate-600/30"
            >
              Cancel
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default LoadingModal;

