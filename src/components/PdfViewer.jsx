import React, { useState, useRef, useCallback, useEffect } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/esm/Page/AnnotationLayer.css';
import 'react-pdf/dist/esm/Page/TextLayer.css';
import Toolbar from './Toolbar';
import VideoPlayer from './VideoPlayer';
import ExplanationViewer from './ExplanationViewer';
import LoadingModal from './LoadingModal';
import OCRSelectionOverlay from './OCRSelectionOverlay';
import InlineOcrButton from './InlineOcrButton';
import { mathVideoAPI, ocrAPI } from '../services/api';

// Set up PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.js`;

const PdfViewer = () => {
  const [numPages, setNumPages] = useState(null);
  const [scale, setScale] = useState(1.0);
  const [file, setFile] = useState(null);
  const [selectedText, setSelectedText] = useState('');
  const [selectionPosition, setSelectionPosition] = useState({ x: 0, y: 0 });
  
  // PDF Loading and Caching states
  const [isLoadingPdf, setIsLoadingPdf] = useState(false);
  const [loadingProgress, setLoadingProgress] = useState(0);
  const [loadedPages, setLoadedPages] = useState(new Set());
  const [pageCache, setPageCache] = useState(new Map());
  const [loadingMessage, setLoadingMessage] = useState('');
  
  // Video generation states
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationProgress, setGenerationProgress] = useState(0);
  const [generationMessage, setGenerationMessage] = useState('');
  const [currentTaskId, setCurrentTaskId] = useState(null);
  
  // Video display states
  const [showVideoPlayer, setShowVideoPlayer] = useState(false);
  const [currentVideoUrl, setCurrentVideoUrl] = useState('');
  const [currentVideoTitle, setCurrentVideoTitle] = useState('');
  
  // Explanation display states
  const [showExplanationViewer, setShowExplanationViewer] = useState(false);
  const [currentExplanation, setCurrentExplanation] = useState('');
  const [currentExplanationTitle, setCurrentExplanationTitle] = useState('');
  
  // Backend status
  const [backendStatus, setBackendStatus] = useState('checking');
  
  // OCR functionality states
  const [ocrMode, setOcrMode] = useState(false);
  const [ocrResults, setOcrResults] = useState([]);  // Array of OCR results with positions
  const [ocrLoading, setOcrLoading] = useState(false);
  const [ocrBackendStatus, setOcrBackendStatus] = useState('checking');
  
  // OCR Results Panel states
  const [showOcrPanel, setShowOcrPanel] = useState(false);
  const [ocrPanelMinimized, setOcrPanelMinimized] = useState(false);
  const [latestOcrResult, setLatestOcrResult] = useState(null);
  const [panelPosition, setPanelPosition] = useState({ x: window.innerWidth - 400, y: window.innerHeight - 420 });
  const [isDraggingPanel, setIsDraggingPanel] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  
  // Generated Videos Gallery states
  const [showVideosGallery, setShowVideosGallery] = useState(false);
  const [videosList, setVideosList] = useState([]);
  const [loadingVideos, setLoadingVideos] = useState(false);
  
  const containerRef = useRef(null);
  const dragOffsetRef = useRef({ x: 0, y: 0 });

  // Handle panel dragging with global mouse events
  useEffect(() => {
    if (!isDraggingPanel) return;

    const handleMouseMove = (e) => {
      setPanelPosition({
        x: e.clientX - dragOffsetRef.current.x,
        y: e.clientY - dragOffsetRef.current.y
      });
    };

    const handleMouseUp = () => {
      setIsDraggingPanel(false);
      document.body.style.userSelect = '';
      document.body.style.cursor = '';
    };

    document.body.style.userSelect = 'none';
    document.body.style.cursor = 'grabbing';
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.userSelect = '';
      document.body.style.cursor = '';
    };
  }, [isDraggingPanel]);

  const onDocumentLoadSuccess = ({ numPages }) => {
    console.log(`📚 PDF loaded successfully! ${numPages} pages found.`);
    setNumPages(numPages);
    setError(null); // Clear any previous errors
    
    // Check memory usage and warn for large PDFs
    const memInfo = checkMemoryUsage();
    
    // Warn about very large PDFs
    if (numPages > 100) {
      setWarningMessage(`Large PDF detected (${numPages} pages). Loading may take time and use significant memory.`);
    }
    
    // Suggest alternatives for extremely large PDFs
    if (numPages > 500) {
      setWarningMessage(`Very large PDF (${numPages} pages). Consider using "Skip & View Now" for better performance.`);
    }
    
    // Start preloading all pages immediately
    try {
      preloadAllPages(numPages);
    } catch (error) {
      handlePdfError(error, 'Page preloading');
    }
  };
  
  const onDocumentLoadError = (error) => {
    console.error('📄 PDF load error:', error);
    handlePdfError(error, 'PDF document loading');
  };

  const handleFileChange = (event) => {
    const selectedFile = event.target.files[0];
    if (selectedFile && selectedFile.type === 'application/pdf') {
      // Reset loading states
      setIsLoadingPdf(true);
      setLoadingProgress(0);
      setLoadedPages(new Set());
      setPageCache(new Map());
      setLoadingMessage('Loading PDF document...');
      
      setFile(selectedFile);
    }
  };

  // Track page loading promises and performance metrics
  const pageLoadPromises = useRef(new Map());
  const pageLoadStartTime = useRef(null);
  const [loadingStats, setLoadingStats] = useState({ startTime: null, pagesLoaded: 0, totalPages: 0 });
  
  // Error handling states
  const [error, setError] = useState(null);
  const [warningMessage, setWarningMessage] = useState('');
  const [memoryWarning, setMemoryWarning] = useState(false);
  
  // Handle individual page load success with performance tracking
  const handlePageLoadSuccess = useCallback((pageNumber) => {
    console.log(`📄 Page ${pageNumber} rendered successfully`);
    
    // Update loaded pages and progress
    setLoadedPages(prev => {
      const newSet = new Set(prev);
      newSet.add(pageNumber);
      
      // Update progress if we're in loading mode
      if (isLoadingPdf && numPages) {
        const progress = Math.round((newSet.size / numPages) * 100);
        setLoadingProgress(progress);
        setLoadingMessage(`Rendering pages... ${newSet.size}/${numPages} (${progress}%)`);
        
        // Update loading stats
        setLoadingStats(prev => ({ ...prev, pagesLoaded: newSet.size }));
        
        // Check if all pages are loaded
        if (newSet.size === numPages) {
          const loadTime = Date.now() - (pageLoadStartTime.current || Date.now());
          console.log(`✅ All ${numPages} pages rendered in ${loadTime}ms! (${(loadTime/numPages).toFixed(1)}ms/page)`);
          
          // Complete loading with brief delay to show 100%
          setTimeout(() => {
            setIsLoadingPdf(false);
            setLoadingMessage(`All pages ready! (${(loadTime/1000).toFixed(1)}s total)`);
            setTimeout(() => setLoadingMessage(''), 2500);
          }, 200);
        }
      }
      
      return newSet;
    });
    
    // Update page cache with performance data
    setPageCache(prev => {
      const newCache = new Map(prev);
      newCache.set(pageNumber, { 
        loaded: true, 
        timestamp: Date.now(),
        renderTime: Date.now() - (pageLoadStartTime.current || Date.now())
      });
      return newCache;
    });
    
    // Resolve page loading promise if exists
    if (pageLoadPromises.current.has(pageNumber)) {
      const resolve = pageLoadPromises.current.get(pageNumber);
      resolve(pageNumber);
      pageLoadPromises.current.delete(pageNumber);
    }
  }, [isLoadingPdf, numPages]);
  
  // Memory monitoring and error handling
  const checkMemoryUsage = useCallback(() => {
    if ('memory' in performance) {
      const memInfo = performance.memory;
      const usedMB = Math.round(memInfo.usedJSHeapSize / 1024 / 1024);
      const limitMB = Math.round(memInfo.jsHeapSizeLimit / 1024 / 1024);
      const usage = (usedMB / limitMB) * 100;
      
      console.log(`🧠 Memory Usage: ${usedMB}MB / ${limitMB}MB (${usage.toFixed(1)}%)`);
      
      if (usage > 80) {
        setMemoryWarning(true);
        setWarningMessage(`High memory usage: ${usage.toFixed(1)}%. Consider reducing PDF size or page count.`);
      } else if (usage > 60) {
        setWarningMessage(`Memory usage: ${usage.toFixed(1)}%. Performance may be affected with large PDFs.`);
      }
      
      return { usedMB, limitMB, usage };
    }
    return null;
  }, []);
  
  // Enhanced error handling for PDF operations
  const handlePdfError = useCallback((error, context = 'PDF operation') => {
    console.error(`❌ ${context} failed:`, error);
    
    let errorMessage = 'An unexpected error occurred.';
    let suggestions = [];
    
    if (error.name === 'InvalidPDFException') {
      errorMessage = 'Invalid or corrupted PDF file.';
      suggestions = [
        'Try a different PDF file',
        'Ensure the PDF is not password-protected',
        'Check if the file downloaded completely'
      ];
    } else if (error.name === 'MissingPDFException') {
      errorMessage = 'PDF file could not be loaded.';
      suggestions = [
        'Check your internet connection',
        'Verify the file path is correct',
        'Try uploading the file again'
      ];
    } else if (error.message?.includes('memory') || error.name === 'RangeError') {
      errorMessage = 'PDF is too large for available memory.';
      suggestions = [
        'Try a smaller PDF file',
        'Close other browser tabs to free memory',
        'Consider splitting the PDF into smaller parts',
        'Use the "Skip & View Now" option for faster loading'
      ];
      setMemoryWarning(true);
    } else if (error.name === 'UnexpectedResponseException') {
      errorMessage = 'Network error while loading PDF.';
      suggestions = [
        'Check your internet connection',
        'Try refreshing the page',
        'Upload the file locally instead'
      ];
    }
    
    setError({
      message: errorMessage,
      suggestions,
      timestamp: new Date().toISOString(),
      context
    });
  }, []);
  
  // Preload all PDF pages for instant display - uses actual page rendering events
  const preloadAllPages = async (totalPages) => {
    console.log(`🚀 Starting to preload ${totalPages} pages...`);
    pageLoadStartTime.current = Date.now();
    setIsLoadingPdf(true);
    setLoadingProgress(0);
    setLoadingMessage('Initializing page rendering...');
    
    // Initialize loading stats
    setLoadingStats({ startTime: Date.now(), pagesLoaded: 0, totalPages });
    
    // Clear previous state
    setLoadedPages(new Set());
    setPageCache(new Map());
    pageLoadPromises.current.clear();
    
    // Create promises that resolve when pages actually render
    const loadPromises = [];
    for (let pageNum = 1; pageNum <= totalPages; pageNum++) {
      const pagePromise = new Promise((resolve) => {
        pageLoadPromises.current.set(pageNum, resolve);
      });
      loadPromises.push(pagePromise);
    }
    
    try {
      setLoadingMessage(`Rendering ${totalPages} pages...`);
      
      // Add timeout fallback (45 seconds for very large PDFs)
      const timeoutPromise = new Promise((_, reject) => {
        setTimeout(() => reject(new Error('Page loading timeout')), 45000);
      });
      
      // Wait for all pages to render or timeout
      await Promise.race([
        Promise.all(loadPromises),
        timeoutPromise
      ]);
      
    } catch (error) {
      console.error('❌ Error during page preloading:', error);
      const currentLoaded = loadedPages.size;
      setIsLoadingPdf(false);
      
      if (error.message === 'Page loading timeout') {
        setLoadingMessage(`Loaded ${currentLoaded}/${totalPages} pages. Others will load as needed.`);
      } else {
        setLoadingMessage('Loading error. Some pages may load slower.');
      }
      setTimeout(() => setLoadingMessage(''), 4000);
    }
  };

  const zoomIn = () => {
    setScale(prevScale => Math.min(prevScale + 0.2, 3.0));
  };

  const zoomOut = () => {
    setScale(prevScale => Math.max(prevScale - 0.2, 0.5));
  };

  const handleTextSelection = useCallback(() => {
    const selection = window.getSelection();
    let selectedText = selection.toString().trim();
    
    // Fix spacing issues in selected text from PDF
    if (selectedText) {
      // Remove strange characters that might come from PDF parsing
      selectedText = selectedText.replace(/[♠♣♥♦]/g, ' ');
      // Add spaces before capital letters that follow lowercase letters
      selectedText = selectedText.replace(/([a-z])([A-Z])/g, '$1 $2');
      // Add spaces before numbers when they follow letters
      selectedText = selectedText.replace(/([a-zA-Z])(\d)/g, '$1 $2');
      // Add spaces after numbers when they're followed by letters
      selectedText = selectedText.replace(/(\d)([a-zA-Z])/g, '$1 $2');
      // Fix common mathematical terms that get concatenated
      selectedText = selectedText.replace(/([a-z])(cm|mm|m|kg|g|°|π)/g, '$1 $2');
      selectedText = selectedText.replace(/(cm|mm|m|kg|g|°|π)([a-zA-Z])/g, '$1 $2');
      // Add space before "and", "of", "the", "is", "to", etc. when they're concatenated
      selectedText = selectedText.replace(/([a-z])(and|of|the|is|to|in|by|with|for)/g, '$1 $2');
      // Clean up multiple spaces and trim
      selectedText = selectedText.replace(/\s+/g, ' ').trim();
    }
    
    if (selectedText && selection.rangeCount > 0) {
      const range = selection.getRangeAt(0);
      const rect = range.getBoundingClientRect();
      
      if (rect.width > 0 && rect.height > 0) {
        setSelectedText(selectedText);
        // Use viewport coordinates (fixed positioning)
        setSelectionPosition({
          x: rect.left + rect.width / 2,
          y: rect.top - 60 // Position above the selection
        });
      }
    } else {
      setSelectedText('');
    }
  }, []);

  useEffect(() => {
    let selectionTimeout;
    
    const handleSelectionChange = () => {
      // Clear previous timeout
      if (selectionTimeout) {
        clearTimeout(selectionTimeout);
      }
      
      // Debounce the selection handling
      selectionTimeout = setTimeout(() => {
        handleTextSelection();
      }, 100); // 100ms delay
    };

    document.addEventListener('selectionchange', handleSelectionChange);
    
    // Also handle mouseup events on the PDF container for better responsiveness
    const handleMouseUp = () => {
      setTimeout(handleTextSelection, 50);
    };
    
    const container = containerRef.current;
    if (container) {
      container.addEventListener('mouseup', handleMouseUp);
    }
    
    return () => {
      document.removeEventListener('selectionchange', handleSelectionChange);
      if (container) {
        container.removeEventListener('mouseup', handleMouseUp);
      }
      if (selectionTimeout) {
        clearTimeout(selectionTimeout);
      }
    };
  }, [handleTextSelection]);

  // Check backend status on component mount
  useEffect(() => {
    const checkBackend = async () => {
      try {
        const status = await mathVideoAPI.checkSetup();
        console.log('🔍 Backend health check:', status);
        
        if (status.status === 'healthy' && status.services) {
          setBackendStatus(status.services.manim ? 'ready' : 'error');
        } else {
          setBackendStatus('error');
        }
      } catch (error) {
        setBackendStatus('offline');
        console.error('Backend is offline:', error);
      }
    };
    
    const checkOcrBackend = async () => {
      try {
        const status = await ocrAPI.checkStatus();
        console.log('🔍 OCR health check:', status);
        
        // Backend returns { status: 'healthy', services: { ocr: true } }
        if (status.status === 'healthy' && status.services && status.services.ocr) {
          setOcrBackendStatus('ready');
          console.log('✅ OCR backend is ready!');
        } else {
          setOcrBackendStatus('error');
          console.warn('⚠️ OCR backend setup issue:', status);
        }
      } catch (error) {
        setOcrBackendStatus('offline');
        console.error('❌ OCR backend is offline:', error);
      }
    };
    
    checkBackend();
    checkOcrBackend();
  }, []);

  const handleVisualize = async (options = {}) => {
    if (!selectedText.trim()) return;
    
    console.log('Starting video generation for:', selectedText);
    
    try {
      setIsGenerating(true);
      setGenerationProgress(0);
      setGenerationMessage('Initializing video generation...');
      
      // Clear selection
      window.getSelection().removeAllRanges();
      
      // Start video generation
      const response = await mathVideoAPI.generateVideo(selectedText, options);
      setCurrentTaskId(response.task_id);
      
      // Poll for status updates
      pollGenerationStatus(response.task_id);
      
    } catch (error) {
      console.error('Error starting video generation:', error);
      setIsGenerating(false);
      setGenerationMessage('Failed to start video generation');
      
      // Show error notification
      alert('Failed to start video generation. Please make sure the backend is running.');
    }
  };

  const pollGenerationStatus = async (taskId) => {
    try {
      const status = await mathVideoAPI.checkStatus(taskId);
      
      setGenerationProgress(status.progress || 0);
      setGenerationMessage(status.message || 'Processing...');
      
      if (status.status === 'completed' && (status.video_url || status.video_path)) {
        // Generation completed successfully
        setIsGenerating(false);
        
        // Check if it's a video file or explanation file
        if ((status.video_url && status.video_url.endsWith('.mp4')) || (status.video_path && status.video_path.endsWith('.mp4'))) {
          // It's a video file
          const pathPart = status.video_url ? status.video_url : `/api/videos/${encodeURIComponent(status.video_path.split('/').pop())}`;
          setCurrentVideoUrl(`http://localhost:5000${pathPart}`);
          setCurrentVideoTitle(selectedText.substring(0, 50) + (selectedText.length > 50 ? '...' : ''));
          setShowVideoPlayer(true);
        } else if (status.video_path && status.video_path.endsWith('.json')) {
          // It's an explanation file
          try {
            const pathPart = status.video_url ? status.video_url : `/api/videos/${encodeURIComponent(status.video_path.split('/').pop())}`;
            const response = await fetch(`http://localhost:5000${pathPart}`);
            const explanationData = await response.json();
            setCurrentExplanation(explanationData.explanation);
            setCurrentExplanationTitle(explanationData.topic);
            setShowExplanationViewer(true);
          } catch (error) {
            console.error('Error loading explanation:', error);
            alert('Error loading explanation');
          }
        }
        setSelectedText('');
        
      } else if (status.status === 'failed') {
        // Generation failed
        setIsGenerating(false);
        alert('Generation failed: ' + status.message);
        
      } else if (status.status === 'generating') {
        // Still generating, continue polling
        setTimeout(() => pollGenerationStatus(taskId), 2000);
        
      } else {
        // Unknown status or not found
        setIsGenerating(false);
        alert('Unknown error occurred during generation');
      }
      
    } catch (error) {
      console.error('Error checking generation status:', error);
      setIsGenerating(false);
      alert('Error checking generation status');
    }
  };

  const handleCancelGeneration = () => {
    setIsGenerating(false);
    setCurrentTaskId(null);
    setGenerationProgress(0);
    setGenerationMessage('');
  };

  const handleContainerClick = (e) => {
    // If clicking outside of selected text, clear selection
    if (!e.target.closest('button')) {
      setTimeout(() => {
        const selection = window.getSelection();
        if (!selection.toString().trim()) {
          setSelectedText('');
        }
      }, 10);
    }
  };

  const getCurrentPageNumber = () => {
    if (!containerRef.current || !numPages) return 1;
    
    const container = containerRef.current;
    const scrollTop = container.scrollTop;
    const containerHeight = container.clientHeight;
    
    // Estimate which page is currently visible based on scroll position
    const pageHeight = containerHeight / scale;
    const currentPage = Math.floor(scrollTop / pageHeight) + 1;
    
    return Math.min(Math.max(currentPage, 1), numPages);
  };

  // OCR functionality states
  const [lastSelectionData, setLastSelectionData] = useState(null);

  // OCR functionality
  const toggleOcrMode = () => {
    console.log('🔄 OCR Mode Toggle:', !ocrMode ? 'ENABLING' : 'DISABLING');
    setOcrMode(!ocrMode);
    if (ocrMode) {
      // Exiting OCR mode - clear all OCR results and buttons
      setOcrResults([]);
      setLastSelectionData(null);
      console.log('❌ OCR Mode DISABLED - Clearing all OCR buttons');
    } else {
      console.log('✅ OCR Mode ENABLED - Overlay should be visible');
    }
  };

  const performOcrExtraction = async (selectionData, preprocessingLevel = 'moderate') => {
    console.log('🔍 Starting OCR extraction...', {
      hasImageData: !!selectionData?.imageData,
      preprocessingLevel,
      selectionCoords: selectionData?.coordinates,
      selectionRect: selectionData?.selectionRect
    });
    
    if (!selectionData.imageData) {
      console.error('❌ No image data provided to OCR extraction');
      return;
    }
    
    // Disable OCR overlay and show loading state
    setOcrMode(false);
    setOcrLoading(true);
    
    try {
      console.log('📡 Sending request to OCR API...');
      const results = await ocrAPI.extractContent(selectionData.imageData, preprocessingLevel);
      console.log('📥 OCR API Response:', results);
      
      // Check if we got any results
      if (!results.success) {
        console.error('❌ OCR extraction failed:', results.error);
        setError({
          message: 'OCR Extraction Failed',
          suggestions: [
            results.error || 'Unknown error occurred',
            'Try selecting a clearer area',
            'Ensure the image contains mathematical content'
          ]
        });
        setOcrLoading(false);
        return;
      }
      
      // Check if we have formulas
      const hasFormulas = results.formulas && results.formulas.length > 0;
      const hasLatex = results.latex && results.latex.trim().length > 0;
      
      if (!hasFormulas && !hasLatex) {
        console.warn('⚠️ OCR extraction returned empty result');
        setError({
          message: 'No Mathematical Content Detected',
          suggestions: [
            'The selected area may not contain clear mathematical notation',
            'Try selecting a different area with equations or formulas',
            'Ensure the image is not too blurry or small'
          ]
        });
        setOcrLoading(false);
        return;
      }
      
      // Use formulas array if available, otherwise wrap latex in array
      const formulasArray = hasFormulas ? results.formulas : (hasLatex ? [results.latex] : []);
      
      if (formulasArray.length > 0) {
        console.log('✅ OCR extraction successful:', {
          formulas: formulasArray.length,
          textBlocks: results.text_content?.length || 0,
          firstFormula: formulasArray[0]?.substring(0, 100) || '(empty)'
        });
        
        // Calculate center position of selection for button placement
        // Use viewport selectionRect mapped to container-relative coordinates for absolute positioning
        let centerX;
        let centerY;
        try {
          const containerEl = containerRef.current;
          const containerRect = containerEl ? containerEl.getBoundingClientRect() : { left: 0, top: 0 };
          const sel = selectionData.selectionRect || { x: 0, y: 0, width: 0, height: 0 };
          centerX = (sel.x - containerRect.left) + (sel.width / 2);
          centerY = (sel.y - containerRect.top) + (sel.height / 2);
        } catch (e) {
          console.warn('⚠️ Failed to compute container-relative position, falling back to canvas coords', e);
          centerX = selectionData.coordinates.x + (selectionData.coordinates.width / 2);
          centerY = selectionData.coordinates.y + (selectionData.coordinates.height / 2);
        }
        
        // Create OCR result objects with positions and unique IDs
        const newOcrResults = formulasArray.map((formula, index) => ({
          id: `ocr-${Date.now()}-${index}`,
          latexContent: typeof formula === 'string' ? formula : formula.latex,
          position: { 
            x: centerX + (index * 20), // Slight offset for multiple formulas 
            y: centerY + (index * 20) 
          },
          // Also store viewport-based position for a fixed fallback
          viewportPosition: (() => {
            const sel = selectionData.selectionRect || { x: 0, y: 0, width: 0, height: 0 };
            return { x: sel.x + sel.width / 2, y: sel.y + sel.height / 2 };
          })(),
          coordinates: selectionData.coordinates,
          selectionRect: selectionData.selectionRect,
          confidence: typeof formula === 'object' ? formula.confidence : null,
          type: typeof formula === 'object' ? formula.type : null
        }));
        
        // Add new OCR results to existing ones
        setOcrResults(prev => [...prev, ...newOcrResults]);
        console.log(`✅ Added ${newOcrResults.length} inline OCR buttons`);
        
        // Show OCR panel with the latest result
        setLatestOcrResult({
          latex: formulasArray[0],
          timestamp: new Date().toLocaleTimeString(),
          confidence: results.confidence,
          rawResult: results.raw_result
        });
        setShowOcrPanel(true);
        setOcrPanelMinimized(false);
        
      }
    } catch (error) {
      console.error('💥 OCR API error:', error);
      setError({
        message: 'OCR Processing Error',
        suggestions: [
          error.message || 'Failed to communicate with OCR service',
          'Check that the backend is running',
          'Try again with a different selection'
        ]
      });
    } finally {
      setOcrLoading(false);
    }
  };

  const handleOcrSelection = async (selectionData) => {
    console.log('🎯 handleOcrSelection called with:', {
      hasImageData: !!selectionData?.imageData,
      imageDataLength: selectionData?.imageData?.length,
      coordinates: selectionData?.coordinates
    });
    
    // Check if we actually got image data
    if (!selectionData || !selectionData.imageData) {
      console.error('❌ No image data in selection! Selection might be too small or failed to capture.');
      alert('Failed to capture selection. Please try selecting a larger area.');
      return;
    }
    
    setLastSelectionData(selectionData);
    
    console.log('📞 About to call performOcrExtraction...');
    await performOcrExtraction(selectionData, 'moderate');
    console.log('✅ performOcrExtraction completed');
  };

  const handleRemoveOcrButton = (ocrId) => {
    console.log('�️ Removing OCR button:', ocrId);
    setOcrResults(prev => prev.filter(result => result.id !== ocrId));
  };

  return (
    <div className="h-screen flex flex-col bg-gray-100">
      <Toolbar 
        onFileChange={handleFileChange}
        onZoomIn={zoomIn}
        onZoomOut={zoomOut}
        currentPage={getCurrentPageNumber()}
        totalPages={numPages || 0}
        scale={scale}
        backendStatus={backendStatus}
        ocrMode={ocrMode}
        onToggleOcr={toggleOcrMode}
        ocrBackendStatus={ocrBackendStatus}
        onShowVideos={async () => {
          setLoadingVideos(true);
          setShowVideosGallery(true);
          try {
            const result = await ocrAPI.listVideos();
            if (result.success) {
              setVideosList(result.videos);
            }
          } catch (error) {
            console.error('Error loading videos:', error);
          } finally {
            setLoadingVideos(false);
          }
        }}
      />
      
      <div 
        ref={containerRef}
        className="flex-1 overflow-auto bg-gray-200 relative"
        style={{ scrollBehavior: 'smooth', position: 'relative' }}
        onClick={handleContainerClick}
      >
        {file ? (
          <>
            {/* Enhanced Loading Progress Overlay - Windscribe Style */}
            {isLoadingPdf && (
              <div className="fixed inset-0 bg-black bg-opacity-60 z-50 flex items-center justify-center backdrop-blur-sm">
                <div className="bg-white p-8 rounded-xl shadow-2xl max-w-lg w-full mx-4 transform transition-all duration-300 scale-100">
                  <div className="text-center">
                    {/* Enhanced Loading Animation */}
                    <div className="relative mb-6">
                      <div className="animate-spin rounded-full h-16 w-16 border-4 border-blue-100 border-t-blue-500 mx-auto"></div>
                      <div className="absolute inset-0 flex items-center justify-center">
                        <div className="animate-pulse text-blue-500 text-xl font-bold">📄</div>
                      </div>
                    </div>
                    
                    <h3 className="text-xl font-bold text-gray-800 mb-3">Optimizing PDF for Fast Viewing</h3>
                    <p className="text-sm text-gray-600 mb-6">{loadingMessage}</p>
                    
                    {/* Enhanced Progress Bar */}
                    <div className="relative w-full bg-gray-200 rounded-full h-3 mb-3 overflow-hidden">
                      <div 
                        className="bg-gradient-to-r from-blue-400 to-blue-600 h-full rounded-full transition-all duration-500 ease-out shadow-inner"
                        style={{ width: `${loadingProgress}%` }}
                      ></div>
                      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white to-transparent opacity-20 animate-pulse"></div>
                    </div>
                    
                    <div className="flex justify-between items-center text-xs mb-4">
                      <span className="text-gray-600">{loadingProgress}% Complete</span>
                      {numPages && (
                        <span className="text-gray-500">
                          {loadedPages.size} / {numPages} pages
                        </span>
                      )}
                    </div>
                    
                    {/* Performance Stats in Modal */}
                    {loadingStats.startTime && (
                      <div className="text-xs text-gray-500 mb-4 bg-gray-50 p-2 rounded">
                        <div>⚡ Loading Time: {((Date.now() - loadingStats.startTime) / 1000).toFixed(1)}s</div>
                        {numPages > 0 && (
                          <div>📊 Avg Speed: {((Date.now() - loadingStats.startTime) / loadedPages.size / 1000).toFixed(2)}s/page</div>
                        )}
                      </div>
                    )}
                    
                    {/* Skip Loading Option */}
                    <div className="flex space-x-3 mt-6">
                      <button
                        onClick={() => {
                          console.log('⏭️ User skipped preloading');
                          setIsLoadingPdf(false);
                          setLoadingMessage('Preloading skipped. Pages will load as needed.');
                          setTimeout(() => setLoadingMessage(''), 2000);
                        }}
                        className="flex-1 px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors duration-200 text-sm font-medium"
                      >
                        Skip & View Now
                      </button>
                      <button
                        onClick={() => {
                          console.log('⏹️ User cancelled loading');
                          setIsLoadingPdf(false);
                          setLoadingMessage('');
                          setFile(null);
                          setNumPages(0);
                          setLoadedPages(new Set());
                        }}
                        className="px-4 py-2 bg-red-100 hover:bg-red-200 text-red-700 rounded-lg transition-colors duration-200 text-sm font-medium"
                      >
                        Cancel
                      </button>
                    </div>
                    
                    {/* Loading Tips */}
                    <div className="mt-4 text-xs text-gray-400 bg-blue-50 p-2 rounded">
                      💡 Tip: We're loading all pages for instant scrolling. Large PDFs may take a moment.
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Success Message */}
            {loadingMessage && !isLoadingPdf && (
              <div className="fixed top-4 right-4 bg-green-500 text-white px-4 py-2 rounded-lg shadow-lg z-40">
                {loadingMessage}
              </div>
            )}
            
            {/* Error Display */}
            {error && (
              <div className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-red-50 border-2 border-red-200 rounded-xl p-6 shadow-2xl z-50 max-w-md mx-4">
                <div className="text-center">
                  <div className="text-red-500 text-5xl mb-3">🚨</div>
                  <h3 className="text-xl font-bold text-red-800 mb-2">PDF Loading Error</h3>
                  <p className="text-red-700 mb-4">{error.message}</p>
                  
                  {error.suggestions && error.suggestions.length > 0 && (
                    <div className="text-left bg-red-100 p-3 rounded-lg mb-4">
                      <div className="font-semibold text-red-800 mb-2">💡 Suggestions:</div>
                      <ul className="text-sm text-red-700 space-y-1">
                        {error.suggestions.map((suggestion, index) => (
                          <li key={index}>• {suggestion}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  
                  <div className="flex space-x-3">
                    <button
                      onClick={() => {
                        setError(null);
                        setFile(null);
                        setNumPages(0);
                      }}
                      className="flex-1 px-5 py-3 bg-gradient-to-r from-red-600 to-red-700 hover:from-red-500 hover:to-red-600 text-white rounded-xl transition-all duration-200 font-semibold shadow-lg hover:shadow-xl transform hover:scale-105"
                    >
                      Try Another File
                    </button>
                    <button
                      onClick={() => setError(null)}
                      className="px-5 py-3 bg-gradient-to-r from-slate-700 to-slate-800 hover:from-slate-600 hover:to-slate-700 text-white rounded-xl transition-all duration-200 font-semibold shadow-lg hover:shadow-xl transform hover:scale-105"
                    >
                      Dismiss
                    </button>
                  </div>
                </div>
              </div>
            )}
            
            {/* Warning Messages */}
            {warningMessage && !error && (
              <div className="fixed top-4 left-1/2 transform -translate-x-1/2 bg-yellow-50 border border-yellow-200 rounded-lg px-4 py-3 shadow-lg z-40 max-w-md">
                <div className="flex items-center">
                  <div className="text-yellow-500 mr-2">⚠️</div>
                  <div className="text-sm text-yellow-800">{warningMessage}</div>
                  <button
                    onClick={() => setWarningMessage('')}
                    className="ml-2 text-yellow-500 hover:text-yellow-700"
                  >
                    ×
                  </button>
                </div>
              </div>
            )}
            
            {/* Memory Warning */}
            {memoryWarning && (
              <div className="fixed bottom-4 right-4 bg-orange-50 border border-orange-200 rounded-lg p-3 shadow-lg z-40 max-w-xs">
                <div className="flex items-start">
                  <div className="text-orange-500 mr-2 mt-0.5">🧠</div>
                  <div className="text-sm text-orange-800">
                    <div className="font-semibold">High Memory Usage</div>
                    <div>Consider closing other tabs or using a smaller PDF.</div>
                    <button
                      onClick={() => setMemoryWarning(false)}
                      className="text-orange-600 hover:text-orange-800 text-xs mt-1"
                    >
                      Dismiss
                    </button>
                  </div>
                </div>
              </div>
            )}
            
            {/* Performance Stats */}
            {numPages && !isLoadingPdf && loadingStats.startTime && (
              <div className="fixed bottom-4 left-4 bg-blue-50 border border-blue-200 rounded-lg p-3 shadow-lg z-30 max-w-xs">
                <div className="text-xs text-blue-700">
                  <div className="font-semibold mb-1">📊 Performance Stats</div>
                  <div>Pages: {numPages}</div>
                  <div>Loaded: {loadedPages.size}</div>
                  {loadingStats.startTime && (
                    <div>
                      Load Time: {((Date.now() - loadingStats.startTime) / 1000).toFixed(1)}s
                    </div>
                  )}
                  <div>Scale: {(scale * 100).toFixed(0)}%</div>
                </div>
              </div>
            )}
            
            {/* Document Container - relative positioning for OCR overlay */}
            <div className="relative flex-1">
              <div className="flex flex-col items-center py-8">
                <Document
                  file={file}
                  onLoadSuccess={onDocumentLoadSuccess}
                  onLoadError={onDocumentLoadError}
                  className="max-w-full"
                  loading={
                    <div className="flex items-center justify-center p-8">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
                      <span className="ml-3 text-gray-600">Initializing PDF...</span>
                    </div>
                  }
                  error={
                    <div className="flex items-center justify-center p-8 bg-red-50 border border-red-200 rounded-lg">
                      <div className="text-center">
                        <div className="text-red-500 text-4xl mb-2">⚠️</div>
                        <div className="text-red-700 font-semibold">Failed to load PDF</div>
                        <div className="text-red-600 text-sm mt-1">Please check the file and try again</div>
                      </div>
                    </div>
                  }
                >
                {numPages && Array.from(new Array(numPages), (el, index) => {
                  const pageNum = index + 1;
                  const isPageLoaded = loadedPages.has(pageNum);
                  
                  return (
                    <div key={`page_${pageNum}`} className="mb-4 shadow-lg relative">
                      {!isPageLoaded && (
                        <div className="absolute inset-0 bg-gray-100 flex items-center justify-center z-10 rounded border border-gray-300">
                          <div className="text-center">
                            <div className="animate-pulse bg-gray-300 h-4 w-4 rounded-full mx-auto mb-2"></div>
                            <span className="text-sm text-gray-500">Loading Page {pageNum}...</span>
                          </div>
                        </div>
                      )}
                      
                      <Page 
                        pageNumber={pageNum}
                        scale={scale}
                        className={`border border-gray-300 bg-white transition-opacity duration-300 ${
                          isPageLoaded ? 'opacity-100' : 'opacity-50'
                        }`}
                        renderTextLayer={!ocrMode && isPageLoaded}
                        renderAnnotationLayer={!ocrMode && isPageLoaded}
                        onLoadSuccess={() => handlePageLoadSuccess(pageNum)}
                        onLoadError={(error) => {
                          console.error(`❌ Error loading page ${pageNum}:`, error);
                          handlePageLoadSuccess(pageNum);
                        }}
                        loading={
                          <div className="flex items-center justify-center p-4 bg-gray-50 border border-gray-200 rounded">
                            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500"></div>
                            <span className="ml-2 text-sm text-gray-600">Rendering page {pageNum}...</span>
                          </div>
                        }
                      />
                      
                      {isPageLoaded && (
                        <div className="absolute top-2 right-2 bg-green-500 text-white text-xs px-2 py-1 rounded opacity-75">
                          ✓ Ready
                        </div>
                      )}
                    </div>
                  );
                })}
              </Document>
            </div>

              {/* OCR Selection Overlay - positioned over the document container */}
              {ocrMode && (
                <OCRSelectionOverlay
                  isActive={ocrMode}
                  onSelection={handleOcrSelection}
                  containerRef={containerRef}
                  scale={scale}
                />
              )}
            </div>

            {/* OCR Loading Indicator */}
            {ocrLoading && (
              <div className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 z-50">
                <div className="bg-white rounded-lg shadow-2xl p-6 border-2 border-blue-200">
                  <div className="flex items-center space-x-3">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
                    <span className="text-gray-700 font-medium">Processing mathematical content...</span>
                  </div>
                </div>
              </div>
            )}

            {/* Inline OCR Buttons */}
            {ocrResults.length > 0 && ocrResults.map((ocrResult) => (
              <InlineOcrButton
                key={ocrResult.id}
                position={ocrResult.position}
                viewportPosition={ocrResult.viewportPosition}
                latexContent={ocrResult.latexContent}
                onRemove={() => handleRemoveOcrButton(ocrResult.id)}
              />
            ))}
          </>
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-center text-gray-500">
              <div className="text-6xl mb-4">📄</div>
              <p className="text-xl mb-2">No PDF selected</p>
              <p className="text-sm">Use the "Open PDF" button to load a document</p>
                
                {/* Debug button for testing OCR API */}
              {backendStatus === 'offline' && (
                <div className="mt-4 p-3 bg-red-100 border border-red-200 rounded-md max-w-md mx-auto">
                  <p className="text-sm text-red-800">
                    ⚠️ Backend is offline. Start the Flask server to enable video generation.
                  </p>
                </div>
              )}
              
              {backendStatus === 'error' && (
                <div className="mt-4 p-3 bg-yellow-100 border border-yellow-200 rounded-md max-w-md mx-auto">
                  <p className="text-sm text-yellow-800">
                    ⚠️ Backend configuration issue. Check your environment setup.
                  </p>
                </div>
              )}
              
              {ocrBackendStatus === 'offline' && (
                <div className="mt-4 p-3 bg-red-100 border border-red-200 rounded-md max-w-md mx-auto">
                  <p className="text-sm text-red-800">
                    ⚠️ OCR Backend is offline. Start the OCR server to enable mathematical extraction.
                  </p>
                </div>
              )}
              
              {ocrBackendStatus === 'ready' && (
                <div className="mt-4 p-3 bg-green-100 border border-green-200 rounded-md max-w-md mx-auto">
                  <p className="text-sm text-green-800">
                    ✅ Mathematical OCR is ready!
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
        

      </div>
      
      {/* Loading Modal for Video Generation */}
      <LoadingModal
        isVisible={isGenerating}
        progress={generationProgress}
        message={generationMessage}
        onCancel={handleCancelGeneration}
      />
      
      {/* Video Player Modal */}
      {showVideoPlayer && (
        <VideoPlayer
          videoUrl={currentVideoUrl}
          title={currentVideoTitle}
          onClose={() => setShowVideoPlayer(false)}
        />
      )}
      
      {/* Explanation Viewer Modal */}
      {showExplanationViewer && (
        <ExplanationViewer
          explanation={currentExplanation}
          title={currentExplanationTitle}
          onClose={() => setShowExplanationViewer(false)}
        />
      )}
      
      {/* OCR Results Panel */}
      {showOcrPanel && latestOcrResult && (
        <div 
          className={`fixed bg-white rounded-lg shadow-2xl border border-gray-300 transition-all duration-300 ${
            ocrPanelMinimized ? 'w-64' : 'w-96'
          }`}
          style={{ 
            left: `${panelPosition.x}px`,
            top: `${panelPosition.y}px`,
            maxHeight: ocrPanelMinimized ? '48px' : '400px',
            zIndex: 9999,
            cursor: isDraggingPanel ? 'grabbing' : 'auto'
          }}
        >
          {/* Panel Header */}
          <div 
            className="flex items-center justify-between bg-gradient-to-r from-blue-600 to-blue-700 text-white px-4 py-2 rounded-t-lg cursor-grab active:cursor-grabbing select-none"
            onMouseDown={(e) => {
              if (e.button !== 0) return; // Only left click
              e.preventDefault();
              dragOffsetRef.current = {
                x: e.clientX - panelPosition.x,
                y: e.clientY - panelPosition.y
              };
              setIsDraggingPanel(true);
            }}
          >
            <div className="flex items-center space-x-2">
              <span className="text-sm font-semibold">📐 OCR Result</span>
              <span className="text-xs opacity-75">{latestOcrResult.timestamp}</span>
            </div>
            <div className="flex items-center space-x-1">
              {/* Minimize/Maximize Button */}
              <button
                onClick={() => setOcrPanelMinimized(!ocrPanelMinimized)}
                className="hover:bg-blue-800 p-1 rounded transition-colors"
                title={ocrPanelMinimized ? "Maximize" : "Minimize"}
              >
                {ocrPanelMinimized ? (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                  </svg>
                ) : (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
                  </svg>
                )}
              </button>
              {/* Close Button */}
              <button
                onClick={() => setShowOcrPanel(false)}
                className="hover:bg-red-600 p-1 rounded transition-colors"
                title="Close"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>
          
          {/* Panel Content */}
          {!ocrPanelMinimized && (
            <div className="p-4 overflow-y-auto" style={{ maxHeight: '340px' }}>
              {/* Confidence Badge */}
              {latestOcrResult.confidence && (
                <div className="mb-3">
                  <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-green-100 text-green-800">
                    Confidence: {(latestOcrResult.confidence * 100).toFixed(0)}%
                  </span>
                </div>
              )}
              
              {/* LaTeX Result */}
              <div className="mb-3">
                <label className="block text-xs font-semibold text-gray-700 mb-1">LaTeX:</label>
                <div className="bg-gray-50 rounded p-3 font-mono text-sm text-gray-800 border border-gray-200 overflow-x-auto">
                  {latestOcrResult.latex}
                </div>
              </div>
              
              {/* Raw Result (if available) */}
              {latestOcrResult.rawResult && latestOcrResult.rawResult !== latestOcrResult.latex && (
                <div className="mb-3">
                  <label className="block text-xs font-semibold text-gray-700 mb-1">Raw Output:</label>
                  <div className="bg-gray-50 rounded p-3 font-mono text-xs text-gray-600 border border-gray-200 overflow-x-auto max-h-32 overflow-y-auto">
                    {latestOcrResult.rawResult}
                  </div>
                </div>
              )}
              
              {/* Action Buttons */}
              <div className="flex flex-col gap-2 mt-4">
                <div className="flex gap-2">
                  <button
                    onClick={async () => {
                      try {
                        console.log('🎬 Starting LaTeX visualization...');
                        setIsGenerating(true);
                        setGenerationProgress(0);
                        setGenerationMessage('Generating Manim animation from LaTeX...');
                        
                        const result = await mathVideoAPI.generateFromLatex(latestOcrResult.latex, { quality: 'medium' });
                        
                        console.log('📦 Generation result:', result);
                        
                        if (result.success) {
                          setCurrentTaskId(result.task_id || result.scene_name);
                          setGenerationMessage('Video generated successfully!');
                          setGenerationProgress(100);
                          
                          setTimeout(() => {
                            setIsGenerating(false);
                            // Construct proper video URL
                            const videoUrl = result.video_path.startsWith('http') 
                              ? result.video_path 
                              : `http://localhost:5000${result.video_path.startsWith('/') ? result.video_path : '/api/videos/' + encodeURIComponent(result.video_path.split(/[\\/]/).pop())}`;
                            console.log('📺 Setting video URL:', videoUrl);
                            setCurrentVideoUrl(videoUrl);
                            setCurrentVideoTitle('LaTeX Visualization');
                            setShowVideoPlayer(true);
                          }, 500);
                        } else {
                          throw new Error(result.error || 'Video generation failed');
                        }
                      } catch (error) {
                        console.error('❌ Video generation error:', error);
                        setError({
                          message: 'Video Generation Failed',
                          suggestions: [
                            error.message || 'Unknown error',
                            'Check that the backend is running',
                            'Verify the LaTeX syntax is correct'
                          ]
                        });
                        setIsGenerating(false);
                      }
                    }}
                    className="flex-1 px-3 py-2 bg-green-600 text-white text-sm rounded hover:bg-green-700 transition-colors font-medium"
                  >
                    🎬 Visualize
                  </button>
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(latestOcrResult.latex);
                      // Show temporary feedback
                      const btn = event.target.closest('button');
                      const originalText = btn.textContent;
                      btn.textContent = '✓ Copied!';
                      setTimeout(() => { btn.textContent = originalText; }, 1500);
                    }}
                    className="flex-1 px-3 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 transition-colors font-medium"
                  >
                    📋 Copy
                  </button>
                </div>
                <button
                  onClick={() => setShowOcrPanel(false)}
                  className="w-full px-3 py-2 bg-gray-200 text-gray-700 text-sm rounded hover:bg-gray-300 transition-colors font-medium"
                >
                  Close
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Generated Videos Gallery Modal */}
      {showVideosGallery && (
        <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-2xl max-w-4xl w-full mx-4 max-h-[90vh] flex flex-col">
            {/* Header */}
            <div className="flex items-center justify-between bg-gradient-to-r from-purple-600 to-purple-700 text-white px-6 py-4 rounded-t-lg">
              <h2 className="text-xl font-bold">🎬 Generated Videos</h2>
              <button
                onClick={() => setShowVideosGallery(false)}
                className="hover:bg-purple-800 p-2 rounded transition-colors"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Content */}
            <div className="p-6 overflow-y-auto flex-1">
              {loadingVideos ? (
                <div className="flex items-center justify-center py-12">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600"></div>
                  <span className="ml-3 text-gray-600">Loading videos...</span>
                </div>
              ) : videosList.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <div className="text-6xl mb-4">🎥</div>
                  <p className="text-lg">No videos generated yet</p>
                  <p className="text-sm mt-2">Use OCR to extract LaTeX and generate visualizations</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {videosList.map((video, index) => (
                    <div
                      key={index}
                      className="border border-gray-200 rounded-lg p-4 hover:shadow-lg transition-shadow cursor-pointer bg-gray-50"
                      onClick={() => {
                        setCurrentVideoUrl(`http://localhost:5000${video.path}`);
                        setCurrentVideoTitle(video.filename);
                        setShowVideoPlayer(true);
                        setShowVideosGallery(false);
                      }}
                    >
                      <div className="flex items-start space-x-3">
                        <div className="flex-shrink-0 text-3xl">🎬</div>
                        <div className="flex-1 min-w-0">
                          <h3 className="text-sm font-semibold text-gray-800 truncate">
                            {video.filename}
                          </h3>
                          <div className="mt-1 text-xs text-gray-500 space-y-1">
                            <div>Size: {(video.size / 1024 / 1024).toFixed(2)} MB</div>
                            <div>Modified: {new Date(video.modified * 1000).toLocaleDateString()}</div>
                          </div>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              window.open(`http://localhost:5000${video.path}`, '_blank');
                            }}
                            className="mt-2 text-xs text-purple-600 hover:text-purple-800 font-medium"
                          >
                            Download ↓
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="px-6 py-4 bg-gray-50 rounded-b-lg border-t border-gray-200">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">
                  {videosList.length} video{videosList.length !== 1 ? 's' : ''} found
                </span>
                <button
                  onClick={() => setShowVideosGallery(false)}
                  className="px-4 py-2 bg-gray-300 hover:bg-gray-400 text-gray-700 rounded-md text-sm font-medium transition-colors"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};

export default PdfViewer;
