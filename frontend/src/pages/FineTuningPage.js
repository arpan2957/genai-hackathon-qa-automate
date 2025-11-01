import React, { useState } from 'react';
import { auth } from '../firebase';
import toast from 'react-hot-toast';
import { SparklesIcon, ExclamationTriangleIcon, CheckCircleIcon, XCircleIcon, ClockIcon, InformationCircleIcon } from '../components/icons';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://127.0.0.1:8000';

const FineTuningPage = () => {
    const [fineTuningStatus, setFineTuningStatus] = useState({
        status: 'idle', // idle, loading, success, error, warning
        message: '',
        details: '',
        lastAttempt: null,
        canRetry: false
    });
    const [isLoading, setIsLoading] = useState(false);
    const [showConfirmModal, setShowConfirmModal] = useState(false);
    const [confirmAction, setConfirmAction] = useState(null);

    const handleFineTune = async ({ force = false } = {}) => {
        if (!auth.currentUser) return;
        
        setIsLoading(true);
        setFineTuningStatus({
            status: 'loading',
            message: 'Initiating fine-tuning job...',
            details: 'Please wait while we prepare your fine-tuning job.',
            lastAttempt: new Date(),
            canRetry: false
        });

        try {
            const token = await auth.currentUser.getIdToken();
            const response = await fetch(`${BACKEND_URL}/api/admin/trigger-finetuning?force=${force}`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` },
            });

            const data = await response.json();

            if (response.ok) {
                setFineTuningStatus({
                    status: 'success',
                    message: 'Fine-tuning job started successfully!',
                    details: data.message,
                    lastAttempt: new Date(),
                    canRetry: false
                });
                toast.success('Fine-tuning job started successfully!');
            } else if (response.status === 428) { // Precondition Required
                setFineTuningStatus({
                    status: 'warning',
                    message: 'Insufficient training data',
                    details: data.detail,
                    lastAttempt: new Date(),
                    canRetry: true
                });
                setConfirmAction(() => () => handleFineTune({ force: true }));
                setShowConfirmModal(true);
            } else if (response.status === 409) { // Conflict - pipeline already running
                setFineTuningStatus({
                    status: 'warning',
                    message: 'Fine-tuning job already in progress',
                    details: data.detail || "A fine-tuning job is already running. Please wait for it to complete before starting a new one.",
                    lastAttempt: new Date(),
                    canRetry: true
                });
            } else if (response.status === 403) { // Forbidden
                setFineTuningStatus({
                    status: 'error',
                    message: 'Permission denied',
                    details: data.detail || "You don't have permission to trigger fine-tuning. Please contact your administrator.",
                    lastAttempt: new Date(),
                    canRetry: false
                });
            } else if (response.status === 404) { // Not Found
                setFineTuningStatus({
                    status: 'error',
                    message: 'Configuration error',
                    details: data.detail || "Required resources not found. Please check your configuration.",
                    lastAttempt: new Date(),
                    canRetry: true
                });
            } else if (response.status === 503) { // Service Unavailable
                setFineTuningStatus({
                    status: 'error',
                    message: 'Service temporarily unavailable',
                    details: data.detail || "Google Cloud services are temporarily unavailable. Please try again later.",
                    lastAttempt: new Date(),
                    canRetry: true
                });
            } else if (response.status === 500) { // Server error
                setFineTuningStatus({
                    status: 'error',
                    message: 'Server error',
                    details: data.detail || "Internal server error occurred while starting fine-tuning.",
                    lastAttempt: new Date(),
                    canRetry: true
                });
            } else {
                // Generic error fallback
                const errorMsg = data.detail || `Request failed with status ${response.status}`;
                setFineTuningStatus({
                    status: 'error',
                    message: 'Fine-tuning failed',
                    details: errorMsg,
                    lastAttempt: new Date(),
                    canRetry: true
                });
            }
        } catch (error) {
            // Network or parsing errors
            let errorMessage = "Failed to communicate with server";
            let details = "";
            
            if (error.name === 'TypeError' && error.message.includes('fetch')) {
                errorMessage = "Network error";
                details = "Unable to connect to server. Please check your internet connection.";
            } else if (error.name === 'SyntaxError') {
                errorMessage = "Server response error";
                details = "Invalid response format received from server.";
            } else if (error.message) {
                errorMessage = "Connection error";
                details = error.message;
            }
            
            setFineTuningStatus({
                status: 'error',
                message: errorMessage,
                details: details,
                lastAttempt: new Date(),
                canRetry: true
            });
        } finally {
            setIsLoading(false);
        }
    };

    const handleRetry = () => {
        handleFineTune();
    };

    const handleConfirmForce = () => {
        setShowConfirmModal(false);
        if (confirmAction) {
            confirmAction();
        }
    };

    const getStatusIcon = () => {
        switch (fineTuningStatus.status) {
            case 'loading':
                return <ClockIcon className="w-6 h-6 text-blue-500 animate-spin" />;
            case 'success':
                return <CheckCircleIcon className="w-6 h-6 text-green-500" />;
            case 'warning':
                return <ExclamationTriangleIcon className="w-6 h-6 text-yellow-500" />;
            case 'error':
                return <XCircleIcon className="w-6 h-6 text-red-500" />;
            default:
                return <InformationCircleIcon className="w-6 h-6 text-gray-500" />;
        }
    };

    const getStatusColor = () => {
        switch (fineTuningStatus.status) {
            case 'loading':
                return 'border-blue-200 bg-blue-50 dark:bg-blue-900/20 dark:border-blue-800';
            case 'success':
                return 'border-green-200 bg-green-50 dark:bg-green-900/20 dark:border-green-800';
            case 'warning':
                return 'border-yellow-200 bg-yellow-50 dark:bg-yellow-900/20 dark:border-yellow-800';
            case 'error':
                return 'border-red-200 bg-red-50 dark:bg-red-900/20 dark:border-red-800';
            default:
                return 'border-gray-200 bg-gray-50 dark:bg-gray-800 dark:border-gray-700';
        }
    };

    const getTextColor = () => {
        switch (fineTuningStatus.status) {
            case 'loading':
                return 'text-blue-800 dark:text-blue-200';
            case 'success':
                return 'text-green-800 dark:text-green-200';
            case 'warning':
                return 'text-yellow-800 dark:text-yellow-200';
            case 'error':
                return 'text-red-800 dark:text-red-200';
            default:
                return 'text-gray-800 dark:text-gray-200';
        }
    };

    return (
        <div className="p-6 bg-white dark:bg-gray-900 rounded-lg shadow-md">
            <div className="flex items-center gap-3 mb-6">
                <SparklesIcon className="w-8 h-8 text-purple-500" />
                <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Model Fine-Tuning</h2>
            </div>

            {/* Information Section */}
            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 mb-6">
                <div className="flex items-start gap-3">
                    <InformationCircleIcon className="w-5 h-5 text-blue-500 mt-0.5 flex-shrink-0" />
                    <div>
                        <h3 className="font-semibold text-blue-800 dark:text-blue-200 mb-2">About Fine-Tuning</h3>
                        <p className="text-blue-700 dark:text-blue-300 text-sm mb-2">
                            Fine-tuning improves the AI model's performance by training it on your specific feedback data. 
                            The system uses corrected test cases from user feedback to create better, more accurate test cases.
                        </p>
                        <p className="text-blue-700 dark:text-blue-300 text-sm">
                            <strong>Minimum requirement:</strong> 100 feedback examples are recommended for effective fine-tuning.
                        </p>
                    </div>
                </div>
            </div>

            {/* Status Display */}
            {fineTuningStatus.status !== 'idle' && (
                <div className={`border rounded-lg p-4 mb-6 ${getStatusColor()}`}>
                    <div className="flex items-start gap-3">
                        {getStatusIcon()}
                        <div className="flex-1">
                            <h3 className={`font-semibold ${getTextColor()} mb-2`}>
                                {fineTuningStatus.message}
                            </h3>
                            <p className={`${getTextColor()} text-sm mb-3`}>
                                {fineTuningStatus.details}
                            </p>
                            {fineTuningStatus.lastAttempt && (
                                <p className={`${getTextColor()} text-xs opacity-75`}>
                                    Last attempt: {fineTuningStatus.lastAttempt.toLocaleString()}
                                </p>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Action Buttons */}
            <div className="flex gap-3">
                <button
                    onClick={() => handleFineTune()}
                    disabled={isLoading}
                    className={`flex items-center gap-2 px-6 py-3 rounded-lg font-medium transition-colors ${
                        isLoading
                            ? 'bg-gray-300 dark:bg-gray-600 text-gray-500 dark:text-gray-400 cursor-not-allowed'
                            : 'bg-purple-600 hover:bg-purple-700 text-white shadow-sm hover:shadow-md'
                    }`}
                >
                    <SparklesIcon className="w-5 h-5" />
                    {isLoading ? 'Starting Fine-Tuning...' : 'Start Fine-Tuning'}
                </button>

                {fineTuningStatus.canRetry && fineTuningStatus.status === 'error' && (
                    <button
                        onClick={handleRetry}
                        disabled={isLoading}
                        className="flex items-center gap-2 px-6 py-3 rounded-lg font-medium border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                    >
                        <ClockIcon className="w-5 h-5" />
                        Retry
                    </button>
                )}
            </div>

            {/* Confirmation Modal */}
            {showConfirmModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4">
                        <div className="flex items-center gap-3 mb-4">
                            <ExclamationTriangleIcon className="w-6 h-6 text-yellow-500" />
                            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                                Confirm Fine-Tuning
                            </h3>
                        </div>
                        <p className="text-gray-700 dark:text-gray-300 mb-6">
                            {fineTuningStatus.details} Do you want to proceed anyway?
                        </p>
                        <div className="flex gap-3 justify-end">
                            <button
                                onClick={() => setShowConfirmModal(false)}
                                className="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleConfirmForce}
                                className="px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-700 text-white transition-colors"
                            >
                                Proceed Anyway
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default FineTuningPage;
