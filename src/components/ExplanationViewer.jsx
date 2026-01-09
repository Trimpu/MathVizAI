import React from 'react';

const ExplanationViewer = ({ explanation, title, onClose }) => {
  if (!explanation) return null;

  const formatExplanation = (text) => {
    // Split by common section headers and format
    return text.split('\n').map((line, index) => {
      const trimmedLine = line.trim();
      
      if (trimmedLine.startsWith('**') && trimmedLine.endsWith('**')) {
        // Bold headers
        return (
          <h3 key={index} className="text-xl font-bold bg-gradient-to-r from-purple-300 to-pink-300 bg-clip-text text-transparent mt-6 mb-3">
            {trimmedLine.replace(/\*\*/g, '')}
          </h3>
        );
      } else if (trimmedLine.includes(':') && trimmedLine.length < 100) {
        // Section headers
        return (
          <h4 key={index} className="font-semibold text-purple-200 mt-4 mb-2">
            {trimmedLine}
          </h4>
        );
      } else if (trimmedLine.match(/^\d+\./)) {
        // Numbered steps
        return (
          <div key={index} className="bg-gradient-to-r from-purple-900/40 to-pink-900/40 border border-purple-500/30 p-4 rounded-xl my-3 backdrop-blur-sm">
            <p className="text-purple-100">{trimmedLine}</p>
          </div>
        );
      } else if (trimmedLine.includes('=') || trimmedLine.includes('≈')) {
        // Mathematical equations
        return (
          <div key={index} className="bg-slate-900/50 border border-purple-500/20 p-3 rounded-xl my-2 font-mono text-center">
            <p className="text-purple-200 text-lg">{trimmedLine}</p>
          </div>
        );
      } else if (trimmedLine) {
        // Regular paragraphs
        return (
          <p key={index} className="text-purple-200 mb-3 leading-relaxed">
            {trimmedLine}
          </p>
        );
      }
      return null;
    }).filter(Boolean);
  };

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 border border-purple-500/30 rounded-3xl p-8 max-w-5xl max-h-[95vh] w-full overflow-auto shadow-2xl shadow-purple-500/20">
        {/* Header */}
        <div className="flex justify-between items-center mb-6 pb-4 border-b border-purple-500/30">
          <h2 className="text-3xl font-bold bg-gradient-to-r from-purple-300 via-pink-300 to-purple-300 bg-clip-text text-transparent">
            📚 Mathematical Explanation
          </h2>
          <button
            onClick={onClose}
            className="text-purple-300 hover:text-white text-3xl font-bold transition-all duration-200 hover:rotate-90 transform"
          >
            ×
          </button>
        </div>
        
        {/* Problem Section */}
        <div className="mb-6">
          <h3 className="text-xl font-semibold text-purple-300 mb-3 flex items-center">
            <span className="mr-2">🎯</span> Problem:
          </h3>
          <div className="bg-gradient-to-r from-yellow-900/40 to-orange-900/40 border-l-4 border-yellow-500 p-5 rounded-xl backdrop-blur-sm">
            <p className="text-purple-100 text-lg">{title}</p>
          </div>
        </div>
        
        {/* Solution Section */}
        <div className="prose max-w-none">
          <h3 className="text-xl font-semibold text-green-300 mb-4 flex items-center">
            <span className="mr-2">✨</span> Solution:
          </h3>
          <div className="space-y-3 bg-slate-900/30 p-6 rounded-2xl border border-purple-500/20">
            {formatExplanation(explanation)}
          </div>
        </div>
        
        {/* Footer Actions */}
        <div className="mt-8 pt-6 border-t border-purple-500/30 flex justify-end space-x-3">
          <button
            onClick={() => {
              const content = `Problem: ${title}\n\nSolution:\n${explanation}`;
              navigator.clipboard.writeText(content);
              alert('Explanation copied to clipboard!');
            }}
            className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white px-6 py-3 rounded-xl font-semibold shadow-lg hover:shadow-xl transform hover:scale-105 transition-all duration-200 border border-purple-400/30 flex items-center"
          >
            <span className="mr-2">📋</span> Copy Explanation
          </button>
          <button
            onClick={onClose}
            className="bg-gradient-to-r from-slate-700 to-slate-800 hover:from-slate-600 hover:to-slate-700 text-white px-6 py-3 rounded-xl font-semibold shadow-lg hover:shadow-xl transform hover:scale-105 transition-all duration-200 border border-slate-600/30"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default ExplanationViewer;

