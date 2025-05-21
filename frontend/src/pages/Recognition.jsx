import React, { useState, useEffect, useRef } from 'react';
import { SignLanguageApi } from '../lib/api';
import { FiCamera, FiRefreshCw, FiPlay, FiPause, FiTrash2, FiSave, FiCheck } from 'react-icons/fi';
import toast from 'react-hot-toast';

const Recognition = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isCapturing, setIsCapturing] = useState(false);
  const [detectedSign, setDetectedSign] = useState('');
  const [recognitionMode, setRecognitionMode] = useState('alphabet');
  const [capturedImages, setCapturedImages] = useState(0);
  const [currentImagePath, setCurrentImagePath] = useState('');
  const [label, setLabel] = useState('');
  const [speechEnabled, setSpeechEnabled] = useState(false);
  
  const recognitionRef = useRef(null);
  const recognitionInterval = useRef(null);

  // Start OpenPose when component mounts
  useEffect(() => {
    const startOpenpose = async () => {
      try {
        setIsLoading(true);
        await SignLanguageApi.startOpenpose();
        toast.success('Ready for recognition');
      } catch (error) {
        toast.error('Failed to start recognition engine');
        console.error(error);
      } finally {
        setIsLoading(false);
      }
    };

    startOpenpose();

    // Cleanup when unmounting
    return () => {
      if (recognitionInterval.current) {
        clearInterval(recognitionInterval.current);
      }
      SignLanguageApi.stopOpenpose().catch(console.error);
    };
  }, []);

  // Start continuous recognition
  const startRecognition = async () => {
    try {
      if (recognitionInterval.current) {
        clearInterval(recognitionInterval.current);
      }
      
      await SignLanguageApi.startOpenpose();
      
      recognitionInterval.current = setInterval(async () => {
        try {
          const result = await SignLanguageApi.infer(recognitionMode, speechEnabled);
          if (result.label) {
            setDetectedSign(result.label);
          }
          if (result.image_path) {
            setCurrentImagePath(result.image_path);
          }
        } catch (error) {
          console.error('Recognition error:', error);
        }
      }, 1000); // Update every second
      
      setIsCapturing(true);
      toast.success('Recognition started');
    } catch (error) {
      toast.error('Failed to start recognition');
      console.error(error);
    }
  };

  // Stop continuous recognition
  const stopRecognition = () => {
    if (recognitionInterval.current) {
      clearInterval(recognitionInterval.current);
      recognitionInterval.current = null;
    }
    setIsCapturing(false);
    toast.success('Recognition paused');
  };

  // Capture images for training
  const captureForTraining = async () => {
    try {
      setIsProcessing(true);
      const result = await SignLanguageApi.capture(3, recognitionMode);
      setCapturedImages(result.files_count || 0);
      toast.success(`Captured ${result.files_count} images`);
    } catch (error) {
      toast.error('Failed to capture images');
      console.error(error);
    } finally {
      setIsProcessing(false);
    }
  };

  // Delete a captured image
  const deleteImage = async (imageId) => {
    try {
      await SignLanguageApi.deleteImage(imageId);
      toast.success(`Image ${imageId} deleted`);
      
      // Refresh count
      const result = await SignLanguageApi.getFileCount();
      setCapturedImages(result.count || 0);
    } catch (error) {
      toast.error('Failed to delete image');
      console.error(error);
    }
  };

  // Save captured images with a label
  const saveWithLabel = async () => {
    if (!label.trim()) {
      toast.error('Please enter a label');
      return;
    }
    
    try {
      setIsProcessing(true);
      await SignLanguageApi.saveLabel(label);
      toast.success(`Saved with label: ${label}`);
      setCapturedImages(0);
      setLabel('');
    } catch (error) {
      toast.error('Failed to save with label');
      console.error(error);
    } finally {
      setIsProcessing(false);
    }
  };

  // Retrain the model
  const retrainModel = async () => {
    try {
      setIsProcessing(true);
      await SignLanguageApi.retrain();
      toast.success('Model retraining started. This may take some time.');
    } catch (error) {
      toast.error('Failed to start retraining');
      console.error(error);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white pt-24">
      <div className="container mx-auto px-4 py-8">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Sign Language Recognition
          </h1>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Use our AI-powered recognition system to detect and interpret sign language in real-time.
          </p>
        </div>

        {/* Mode Selection */}
        <div className="mb-10 max-w-xl mx-auto">
          <div className="flex justify-center space-x-4 mb-6">
            <button
              className={`px-6 py-3 rounded-full ${
                recognitionMode === 'alphabet'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              } transition`}
              onClick={() => setRecognitionMode('alphabet')}
            >
              Alphabet
            </button>
            <button
              className={`px-6 py-3 rounded-full ${
                recognitionMode === 'word'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              } transition`}
              onClick={() => setRecognitionMode('word')}
            >
              Words
            </button>
          </div>
          
          <div className="flex items-center justify-center mb-6">
            <label className="inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={speechEnabled}
                onChange={() => setSpeechEnabled(!speechEnabled)}
                className="sr-only peer"
              />
              <div className="relative w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
              <span className="ml-3 text-sm font-medium text-gray-900">Enable Speech</span>
            </label>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-12">
          {/* Recognition Area */}
          <div className="bg-white p-6 rounded-xl shadow-md">
            <h2 className="text-2xl font-bold mb-6 text-center">Real-time Recognition</h2>
            
            <div 
              ref={recognitionRef} 
              className="h-[400px] bg-gray-100 rounded-lg flex items-center justify-center mb-6 overflow-hidden"
            >
              {currentImagePath ? (
                <img 
                  src={currentImagePath} 
                  alt="Recognition" 
                  className="max-h-full max-w-full object-contain"
                />
              ) : (
                <div className="text-gray-500 flex flex-col items-center">
                  <FiCamera size={48} className="mb-4" />
                  <p>Recognition feed will appear here</p>
                </div>
              )}
            </div>

            <div className="text-center mb-6">
              <div className="text-5xl font-bold text-blue-600 mb-2">
                {detectedSign || '...'}
              </div>
              <p className="text-gray-600">Detected Sign</p>
            </div>

            <div className="flex justify-center space-x-4">
              {!isCapturing ? (
                <button
                  onClick={startRecognition}
                  disabled={isLoading}
                  className="flex items-center justify-center px-6 py-3 bg-blue-600 text-white rounded-full hover:bg-blue-700 transition disabled:opacity-50"
                >
                  <FiPlay className="mr-2" />
                  Start Recognition
                </button>
              ) : (
                <button
                  onClick={stopRecognition}
                  className="flex items-center justify-center px-6 py-3 bg-red-600 text-white rounded-full hover:bg-red-700 transition"
                >
                  <FiPause className="mr-2" />
                  Stop Recognition
                </button>
              )}
            </div>
          </div>

          {/* Training Area */}
          <div className="bg-white p-6 rounded-xl shadow-md">
            <h2 className="text-2xl font-bold mb-6 text-center">Contribute & Train</h2>
            
            <div className="mb-6">
              <p className="text-gray-600 mb-4 text-center">
                Help improve our system by contributing sign language data.
              </p>
              
              <div className="flex justify-center mb-6">
                <button
                  onClick={captureForTraining}
                  disabled={isProcessing}
                  className="flex items-center justify-center px-6 py-3 bg-blue-600 text-white rounded-full hover:bg-blue-700 transition disabled:opacity-50"
                >
                  <FiCamera className="mr-2" />
                  Capture for Training
                </button>
              </div>
              
              {capturedImages > 0 && (
                <div className="mb-6">
                  <div className="text-center mb-4">
                    <span className="bg-blue-100 text-blue-800 text-sm font-semibold px-3 py-1 rounded-full">
                      {capturedImages} frames captured
                    </span>
                  </div>
                  
                  <div className="grid grid-cols-4 gap-2 mb-4">
                    {Array.from({ length: capturedImages }).map((_, i) => (
                      <div key={i} className="relative group">
                        <img
                          src={`/api/static/captured_images/${i + 1}.jpg`}
                          alt={`Captured frame ${i + 1}`}
                          className="w-full h-24 object-cover rounded"
                        />
                        <button
                          onClick={() => deleteImage(i + 1)}
                          className="absolute top-1 right-1 bg-red-500 text-white p-1 rounded-full opacity-0 group-hover:opacity-100 transition"
                        >
                          <FiTrash2 size={14} />
                        </button>
                      </div>
                    ))}
                  </div>
                  
                  <div className="flex items-end space-x-4">
                    <div className="flex-1">
                      <label htmlFor="label" className="block text-sm font-medium text-gray-700 mb-1">
                        Label
                      </label>
                      <input
                        type="text"
                        id="label"
                        value={label}
                        onChange={(e) => setLabel(e.target.value)}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500"
                        placeholder="Enter sign label"
                      />
                    </div>
                    <button
                      onClick={saveWithLabel}
                      disabled={!label.trim() || isProcessing}
                      className="flex items-center px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition disabled:opacity-50"
                    >
                      <FiSave className="mr-2" />
                      Save
                    </button>
                  </div>
                </div>
              )}
            </div>
            
            <div className="border-t pt-6">
              <h3 className="text-lg font-semibold mb-4 text-center">Advanced Options</h3>
              <div className="flex justify-center">
                <button
                  onClick={retrainModel}
                  disabled={isProcessing}
                  className="flex items-center justify-center px-6 py-3 bg-gray-700 text-white rounded-full hover:bg-gray-800 transition disabled:opacity-50"
                >
                  <FiRefreshCw className="mr-2" />
                  Retrain Model
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Recognition;