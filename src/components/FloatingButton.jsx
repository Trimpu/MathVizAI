import React, { useState } from 'react';

const FloatingButton = ({ onVisualize, position, selectedText }) => {
  const [showOptions, setShowOptions] = useState(false);
  const [difficulty, setDifficulty] = useState('intermediate');
  const [quality, setQuality] = useState('medium_quality');

  const handleVisualize = (customOptions = {}) => {
    const options = {
      difficulty,
      quality,
      duration: 45,
      ...customOptions
    };
    onVisualize(options);
    setShowOptions(false);
  };

  const handleQuickVisualize = () => {
    handleVisualize();
  };

  return (
    <div
      className="fixed z-50 transform -translate-x-1/2 pointer-events-none"
      style={{
        left: `${position.x}px`,
        top: `${position.y}px`,
      }}
    >
      {!showOptions ? (
        // Main button - Windscribe Style
        <div className="flex space-x-2 pointer-events-auto">
          <button
            onClick={handleQuickVisualize}
            className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white px-4 py-2 rounded-xl text-sm font-semibold shadow-2xl shadow-purple-500/50 transition-all duration-200 ease-in-out transform hover:scale-110 border border-purple-400/50 animate-pulse"
            title="Quick visualization"
          >
            ✨ Visualize
          </button>
          
          <button
            onClick={() => setShowOptions(true)}
            className="bg-gradient-to-r from-slate-700 to-slate-800 hover:from-slate-600 hover:to-slate-700 text-white px-3 py-2 rounded-xl text-sm font-semibold shadow-2xl shadow-slate-500/50 transition-all duration-200 ease-in-out transform hover:scale-110 border border-slate-600/50"
            title="More options"
          >
            ⚙️
          </button>
        </div>
      ) : (
        // Options panel - Windscribe Style
        <div className="bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 border border-purple-500/40 rounded-2xl shadow-2xl shadow-purple-500/30 p-5 min-w-[320px] pointer-events-auto backdrop-blur-xl">
          <div className="mb-4">
            <h4 className="font-bold text-purple-100 text-base mb-2 flex items-center">
              <span className="mr-2">🎬</span> Video Generation
            </h4>
            <p className="text-xs text-purple-300 mb-3 max-w-[280px] truncate bg-slate-800/50 px-3 py-2 rounded-lg border border-purple-500/20" title={selectedText}>
              "{selectedText}"
            </p>
          </div>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-semibold text-purple-200 mb-2">
                Difficulty Level
              </label>
              <select
                value={difficulty}
                onChange={(e) => setDifficulty(e.target.value)}
                className="w-full text-sm bg-slate-800/70 border border-purple-500/30 text-purple-100 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
              >
                <option value="beginner" className="bg-slate-900">🟢 Beginner</option>
                <option value="intermediate" className="bg-slate-900">🟡 Intermediate</option>
                <option value="advanced" className="bg-slate-900">🔴 Advanced</option>
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-semibold text-purple-200 mb-2">
                Video Quality
              </label>
              <select
                value={quality}
                onChange={(e) => setQuality(e.target.value)}
                className="w-full text-sm bg-slate-800/70 border border-purple-500/30 text-purple-100 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
              >
                <option value="low_quality" className="bg-slate-900">📱 Low (Fast)</option>
                <option value="medium_quality" className="bg-slate-900">💻 Medium</option>
                <option value="high_quality" className="bg-slate-900">🎬 High (Slow)</option>
              </select>
            </div>
          </div>
          
          <div className="flex justify-between mt-5 pt-4 border-t border-purple-500/30">
            <button
              onClick={() => setShowOptions(false)}
              className="text-sm bg-gradient-to-r from-slate-700 to-slate-800 hover:from-slate-600 hover:to-slate-700 text-white px-4 py-2 rounded-lg transition-all duration-200 transform hover:scale-105 border border-slate-600/30"
            >
              Cancel
            </button>
            <button
              onClick={() => handleVisualize()}
              className="text-sm bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white px-4 py-2 rounded-lg transition-all duration-200 transform hover:scale-105 shadow-lg border border-purple-400/30 font-semibold"
            >
              Generate Video 🎬
            </button>
          </div>
        </div>
      )}
      
      {/* Arrow pointing down - Windscribe Style */}
      {!showOptions && (
        <div className="absolute left-1/2 top-full transform -translate-x-1/2 mt-1">
          <div className="w-0 h-0 border-l-4 border-r-4 border-t-4 border-l-transparent border-r-transparent border-t-purple-500 drop-shadow-lg"></div>
        </div>
      )}
    </div>
  );
};

export default FloatingButton;
