
import React from 'react';

const ConfirmationModal = ({ isOpen, onClose, onConfirm, title, message }) => {
    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50">
            <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-2xl w-full max-w-md shadow-2xl">
                <div className="p-8 space-y-4">
                    <h2 className="text-xl font-bold text-gray-900 dark:text-white text-center">{title}</h2>
                    <p className="text-sm text-gray-600 dark:text-gray-400 text-center">{message}</p>
                </div>
                <div className="p-4 bg-gray-50 dark:bg-gray-900/80 border-t border-gray-200 dark:border-gray-700 flex justify-end space-x-3">
                    <button 
                        onClick={onClose} 
                        className="px-4 py-2 text-sm font-semibold text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                    >
                        Cancel
                    </button>
                    <button 
                        onClick={onConfirm} 
                        className="px-4 py-2 text-sm font-semibold text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
                    >
                        Confirm
                    </button>
                </div>
            </div>
        </div>
    );
};

export default ConfirmationModal;
