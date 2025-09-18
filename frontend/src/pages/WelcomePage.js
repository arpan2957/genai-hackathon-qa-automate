
import React, { useState } from 'react';
import { LogoIcon } from '../components/icons';
import LoginModal from '../components/LoginModal';

const WelcomePage = () => {
    const [isModalOpen, setModalOpen] = useState(false);
    const [modalMode, setModalMode] = useState('login'); // 'login' or 'signup'

    const openModal = (mode) => {
        setModalMode(mode);
        setModalOpen(true);
    };

    return (
        <>
            <div className="flex flex-col items-center justify-center min-h-screen bg-gray-50 dark:bg-gray-900 text-center p-4">
                <div className="mb-8">
                    <LogoIcon className="w-24 h-24 text-cyan-500 mx-auto" />
                </div>
                <h1 className="text-4xl md:text-5xl font-bold text-gray-800 dark:text-white mb-4">
                    Welcome to QA Automate
                </h1>
                <p className="text-lg md:text-xl text-gray-600 dark:text-gray-300 max-w-2xl mb-10">
                    The next-generation tool for accelerating your quality assurance workflow. Generate comprehensive test cases from software requirements in seconds.
                </p>
                <div className="flex flex-col sm:flex-row gap-4">
                    <button
                        onClick={() => openModal('login')}
                        className="px-8 py-4 text-lg font-semibold text-white bg-cyan-600 dark:bg-cyan-500 rounded-lg hover:opacity-90 transition-all duration-300 shadow-lg hover:shadow-cyan-500/50 transform hover:-translate-y-1"
                    >
                        Login
                    </button>
                    <button
                        onClick={() => openModal('signup')}
                        className="px-8 py-4 text-lg font-semibold text-cyan-600 dark:text-cyan-500 bg-white dark:bg-gray-800 border border-cyan-600 dark:border-cyan-500 rounded-lg hover:bg-cyan-50 dark:hover:bg-gray-700 transition-all duration-300 shadow-lg hover:shadow-cyan-500/30 transform hover:-translate-y-1"
                    >
                        Sign Up
                    </button>
                </div>
            </div>
            <LoginModal 
                isOpen={isModalOpen} 
                onClose={() => setModalOpen(false)} 
                initialMode={modalMode}
            />
        </>
    );
};

export default WelcomePage;
