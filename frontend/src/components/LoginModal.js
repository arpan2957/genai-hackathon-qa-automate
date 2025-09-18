
import React, { useState, useEffect, useMemo } from 'react';
import { auth } from '../firebase';
import { GoogleAuthProvider, signInWithPopup, signInWithEmailAndPassword, createUserWithEmailAndPassword } from "firebase/auth";
import { CheckCircleIcon, XCircleIcon } from './icons'; // Assuming you have these icons

const PasswordRequirement = ({ meets, text }) => (
    <div className="flex items-center text-sm">
        {meets ? (
            <CheckCircleIcon className="w-4 h-4 text-green-500 mr-2" />
        ) : (
            <XCircleIcon className="w-4 h-4 text-gray-400 mr-2" />
        )}
        <span className={meets ? 'text-gray-800 dark:text-gray-200' : 'text-gray-500 dark:text-gray-400'}>{text}</span>
    </div>
);

const LoginModal = ({ isOpen, onClose, initialMode = 'login' }) => {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState(null);
    const [mode, setMode] = useState(initialMode);

    const passwordCriteria = useMemo(() => {
        const criteria = {
            length: password.length >= 8,
            uppercase: /[A-Z]/.test(password),
            lowercase: /[a-z]/.test(password),
            number: /[0-9]/.test(password),
            specialChar: /[!@#$%^&*(),.?":{}|<>]/.test(password),
        };
        return criteria;
    }, [password]);

    const isPasswordValid = useMemo(() => Object.values(passwordCriteria).every(Boolean), [passwordCriteria]);

    useEffect(() => {
        setMode(initialMode);
        // Reset state on mode change or modal close
        setEmail('');
        setPassword('');
        setError(null);
    }, [initialMode, isOpen]);

    if (!isOpen) return null;

    const handleGoogleLogin = async () => {
        const provider = new GoogleAuthProvider();
        try {
            await signInWithPopup(auth, provider);
            onClose();
        } catch (error) {
            console.error("Error during Google sign-in: ", error);
            setError("Failed to sign in with Google. Please try again.");
        }
    };

    const handleEmailSubmit = async (e) => {
        e.preventDefault();
        setError(null);

        if (mode === 'signup' && !isPasswordValid) {
            setError("Password does not meet all the requirements.");
            return;
        }

        try {
            if (mode === 'login') {
                await signInWithEmailAndPassword(auth, email, password);
            } else {
                await createUserWithEmailAndPassword(auth, email, password);
            }
            onClose();
        } catch (error) {
            console.error(`Error during email ${mode}: `, error);
            setError(error.message);
        }
    };

    const toggleMode = () => {
        setMode(prevMode => prevMode === 'login' ? 'signup' : 'login');
        setError(null);
        setPassword(''); // Clear password on mode toggle
    };

    return (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50">
            <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-2xl w-full max-w-md shadow-2xl">
                <div className="p-8 space-y-6">
                    <h2 className="text-2xl font-bold text-gray-900 dark:text-white text-center">
                        {mode === 'login' ? 'Welcome Back' : 'Create an Account'}
                    </h2>
                    
                    {error && <p className="text-red-500 text-sm text-center bg-red-100 dark:bg-red-500/20 p-3 rounded-lg">{error}</p>}

                    <form onSubmit={handleEmailSubmit} className="space-y-4">
                        <div>
                            <label htmlFor="email" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Email Address</label>
                            <input
                                id="email"
                                name="email"
                                type="email"
                                autoComplete="email"
                                required
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                className="mt-1 w-full bg-gray-100 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg p-3 text-sm text-gray-800 dark:text-gray-200 focus:outline-none focus:ring-2 focus:ring-cyan-500"
                            />
                        </div>
                        <div>
                            <label htmlFor="password" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Password</label>
                            <input
                                id="password"
                                name="password"
                                type="password"
                                autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                                required
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                className="mt-1 w-full bg-gray-100 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg p-3 text-sm text-gray-800 dark:text-gray-200 focus:outline-none focus:ring-2 focus:ring-cyan-500"
                            />
                        </div>

                        {mode === 'signup' && password.length > 0 && (
                            <div className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg space-y-2">
                                <PasswordRequirement meets={passwordCriteria.length} text="At least 8 characters" />
                                <PasswordRequirement meets={passwordCriteria.uppercase} text="Contains an uppercase letter" />
                                <PasswordRequirement meets={passwordCriteria.lowercase} text="Contains a lowercase letter" />
                                <PasswordRequirement meets={passwordCriteria.number} text="Contains a number" />
                                <PasswordRequirement meets={passwordCriteria.specialChar} text="Contains a special character (!@#...)" />
                            </div>
                        )}

                        <button 
                            type="submit"
                            disabled={mode === 'signup' && !isPasswordValid}
                            className="w-full py-3 px-4 font-semibold text-white bg-cyan-600 dark:bg-cyan-500 rounded-lg hover:opacity-90 transition-opacity disabled:bg-slate-400 dark:disabled:bg-slate-600 disabled:cursor-not-allowed"
                        >
                            {mode === 'login' ? 'Sign In' : 'Sign Up'}
                        </button>
                    </form>

                    <div className="relative">
                        <div className="absolute inset-0 flex items-center">
                            <div className="w-full border-t border-gray-300 dark:border-gray-600" />
                        </div>
                        <div className="relative flex justify-center text-sm">
                            <span className="px-2 bg-white dark:bg-gray-900 text-gray-500 dark:text-gray-400">Or continue with</span>
                        </div>
                    </div>

                    <button 
                        onClick={handleGoogleLogin} 
                        className="w-full flex items-center justify-center gap-3 py-3 px-4 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 dark:bg-gray-800 dark:border-gray-600 dark:hover:bg-gray-700 transition-colors"
                    >
                        <svg className="w-5 h-5" viewBox="0 0 48 48">
                            <path fill="#FFC107" d="M43.611 20.083H42V20H24v8h11.303c-1.649 4.657-6.08 8-11.303 8c-6.627 0-12-5.373-12-12s5.373-12 12-12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4C12.955 4 4 12.955 4 24s8.955 20 20 20s20-8.955 20-20c0-1.341-.138-2.65-.389-3.917z"></path>
                            <path fill="#FF3D00" d="M6.306 14.691l6.571 4.819C14.655 15.108 18.961 12 24 12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4C16.318 4 9.656 8.337 6.306 14.691z"></path>
                            <path fill="#4CAF50" d="M24 44c5.166 0 9.86-1.977 13.409-5.192l-6.19-5.238A7.94 7.94 0 0 1 24 36c-5.225 0-9.554-3.443-11.303-8H2.394v8C5.494 40.663 13.866 44 24 44z"></path>
                            <path fill="#1976D2" d="M43.611 20.083H42V20H24v8h11.303c-.792 2.237-2.231 4.166-4.087 5.571l6.19 5.238C42.612 35.845 44 30.138 44 24c0-1.341-.138-2.65-.389-3.917z"></path>
                        </svg>
                        <span>Sign in with Google</span>
                    </button>
                </div>
                <div className="p-4 bg-gray-50 dark:bg-gray-900/80 border-t border-gray-200 dark:border-gray-700 text-center">
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                        {mode === 'login' ? "Don't have an account? " : "Already have an account? "}
                        <button onClick={toggleMode} className="font-medium text-cyan-600 hover:underline">
                            {mode === 'login' ? 'Sign Up' : 'Sign In'}
                        </button>
                         <span className="mx-2 text-gray-300 dark:text-gray-600">|</span>
                        <button onClick={onClose} className="font-medium text-cyan-600 hover:underline">Cancel</button>
                    </p>
                </div>
            </div>
        </div>
    );
};

export default LoginModal;
