import React from 'react';
import { MenuIcon, SearchIcon, SparklesIcon, SunIcon, MoonIcon } from './icons';
import { useTheme } from '../contexts/ThemeContext';
import { auth } from '../firebase';
import toast from 'react-hot-toast';

const Header = ({ setMobileSidebarOpen, setSidebarPinned, isSidebarPinned, setAiModalOpen, setCreateModalOpen, user, searchQuery, setSearchQuery }) => {
    const { theme, toggleTheme } = useTheme();

    const handleLogout = async () => {
        try {
            await auth.signOut();
            toast.success('You have been logged out!');
        } catch (error) {
            console.error("Error signing out: ", error);
        }
    };

    return (
        <header className="flex-shrink-0 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 p-4 h-16 z-10 transition-all duration-300">
            <div className="flex items-center justify-between h-full">
                <div className="flex items-center px-2">
                    <button onClick={() => setSidebarPinned(!isSidebarPinned)} className="hidden lg:block p-2 rounded-md text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800 mr-2 relative group">
                        <MenuIcon className="w-6 h-6" />
                        <span className="absolute left-full ml-4 px-2 py-1 bg-gray-800 text-white text-xs rounded-md opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
                            {isSidebarPinned ? 'Unpin sidebar' : 'Pin sidebar'}
                        </span>
                    </button>
                     <button onClick={() => setMobileSidebarOpen(true)} className="lg:hidden p-2 rounded-md text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800 mr-2">
                        <MenuIcon className="w-6 h-6" />
                    </button>
                    <div className="relative ml-4 flex-grow">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none"><SearchIcon className="w-5 h-5 text-gray-400 dark:text-gray-500"/></div>
                        <input type="text" placeholder="Search..." className="w-full max-w-full sm:max-w-xs bg-gray-100 dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg pl-10 pr-4 py-2 text-sm text-gray-800 dark:text-gray-200 focus:outline-none focus:ring-2 focus:ring-cyan-500" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} />
                    </div>
                </div>
                <div className="flex items-center space-x-2 md:space-x-3 flex-shrink-0">
                    <button onClick={() => setCreateModalOpen(true)} className="px-3 md:px-4 py-2 text-sm font-semibold text-gray-700 dark:text-white bg-transparent border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800/70 transition-colors whitespace-nowrap">Create Test Case</button>
                    <button onClick={() => setAiModalOpen(true)} className="px-3 md:px-4 py-2 text-sm font-semibold text-white bg-cyan-600 dark:bg-cyan-500 rounded-lg hover:opacity-90 transition-opacity flex items-center space-x-2 whitespace-nowrap">
                        <SparklesIcon className="w-5 h-5" /> <span>Generate with AI</span>
                    </button>
                    
                    {user && (
                        <div className="flex items-center">
                            <span className="text-slate-500 dark:text-slate-400 mr-2 md:mr-4 hidden sm:inline">{user.displayName ? user.displayName.split(' ')[0] : user.email}</span>
                            <button
                                onClick={handleLogout}
                                className="bg-red-600 hover:bg-red-700 text-white font-bold py-2 px-3 md:px-4 rounded-lg transition duration-300 shadow-md hover:shadow-lg"
                            >
                                Logout
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </header>
    );
};

export default Header;