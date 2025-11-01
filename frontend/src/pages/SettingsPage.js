import React, { useState, useEffect } from 'react';
import { useTheme } from '../contexts/ThemeContext';
import { auth } from '../firebase';
import toast from 'react-hot-toast';
import { 
    UserIcon, 
    CogIcon, 
    BellIcon, 
    ShieldCheckIcon, 
    DocumentTextIcon,
    KeyIcon,
    GlobeAltIcon,
    ExclamationTriangleIcon,
    CheckCircleIcon,
    XMarkIcon
} from '../components/icons';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://127.0.0.1:8000';

const SettingsPage = () => {
    const { theme, toggleTheme } = useTheme();
    const [user, setUser] = useState(null);
    const [activeTab, setActiveTab] = useState('profile');
    const [isLoading, setIsLoading] = useState(false);
    const [userProfile, setUserProfile] = useState({
        displayName: '',
        email: '',
        preferences: {
            emailNotifications: true,
            pushNotifications: false,
            weeklyReports: true,
            testCaseUpdates: true
        }
    });
    const [integrations, setIntegrations] = useState({
        jira: { enabled: false, url: '', username: '', token: '' },
        azure: { enabled: false, url: '', token: '' },
        slack: { enabled: false, webhook: '' }
    });
    const [systemSettings, setSystemSettings] = useState({
        aiModel: 'gpt-4',
        maxTestCases: 50,
        autoSave: true,
        dataRetention: 90
    });

    useEffect(() => {
        const unsubscribe = auth.onAuthStateChanged((currentUser) => {
            if (currentUser) {
                setUser(currentUser);
                setUserProfile(prev => ({
                    ...prev,
                    displayName: currentUser.displayName || '',
                    email: currentUser.email || ''
                }));
                loadUserSettings(currentUser);
            }
        });
        return () => unsubscribe();
    }, []);

    const loadUserSettings = async (currentUser) => {
        try {
            const token = await currentUser.getIdToken();
            const response = await fetch(`${BACKEND_URL}/api/user/settings`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            
            if (response.ok) {
                const settings = await response.json();
                if (settings.preferences) setUserProfile(prev => ({ ...prev, preferences: settings.preferences }));
                if (settings.integrations) setIntegrations(settings.integrations);
                if (settings.system) setSystemSettings(settings.system);
            }
        } catch (error) {
            console.log('Settings not found, using defaults');
        }
    };

    const saveSettings = async (section, data) => {
        if (!user) return;
        
        setIsLoading(true);
        try {
            const token = await user.getIdToken();
            const response = await fetch(`${BACKEND_URL}/api/user/settings`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ [section]: data })
            });

            if (response.ok) {
                toast.success('Settings saved successfully!');
            } else {
                throw new Error('Failed to save settings');
            }
        } catch (error) {
            toast.error('Failed to save settings');
        } finally {
            setIsLoading(false);
        }
    };

    const testIntegration = async (type) => {
        if (!user) return;
        
        setIsLoading(true);
        try {
            const token = await user.getIdToken();
            const response = await fetch(`${BACKEND_URL}/api/integrations/${type}/test`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(integrations[type])
            });

            if (response.ok) {
                toast.success(`${type.toUpperCase()} connection successful!`);
            } else {
                throw new Error(`${type.toUpperCase()} connection failed`);
            }
        } catch (error) {
            toast.error(`${type.toUpperCase()} connection failed`);
        } finally {
            setIsLoading(false);
        }
    };

    const TabButton = ({ id, label, icon, isActive, onClick }) => (
        <button
            onClick={() => onClick(id)}
            className={`flex items-center px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                isActive 
                    ? 'bg-indigo-100 dark:bg-indigo-900 text-indigo-700 dark:text-indigo-300' 
                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800'
            }`}
        >
            {React.cloneElement(icon, { className: 'w-5 h-5 mr-2' })}
            {label}
        </button>
    );

    const SettingCard = ({ title, description, children }) => (
        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm border border-gray-200 dark:border-gray-700">
            <div className="mb-4">
                <h3 className="text-lg font-medium text-gray-900 dark:text-white">{title}</h3>
                {description && (
                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">{description}</p>
                )}
            </div>
            {children}
        </div>
    );

    const Toggle = ({ enabled, onChange, label }) => (
        <label className="flex items-center justify-between cursor-pointer">
            <span className="text-sm text-gray-700 dark:text-gray-300">{label}</span>
            <div className="relative">
                <input
                    type="checkbox"
                    checked={enabled}
                    onChange={onChange}
                    className="sr-only"
                />
                <div className={`w-11 h-6 rounded-full transition-colors ${
                    enabled ? 'bg-indigo-600' : 'bg-gray-300 dark:bg-gray-600'
                }`}>
                    <div className={`w-5 h-5 bg-white rounded-full shadow transform transition-transform ${
                        enabled ? 'translate-x-5' : 'translate-x-0.5'
                    } mt-0.5`} />
                </div>
            </div>
        </label>
    );

    const renderProfileTab = () => (
        <div className="space-y-6">
            <SettingCard 
                title="Profile Information" 
                description="Update your personal information and account details"
            >
                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            Display Name
                        </label>
                        <input
                            type="text"
                            value={userProfile.displayName}
                            onChange={(e) => setUserProfile(prev => ({ ...prev, displayName: e.target.value }))}
                            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                            placeholder="Enter your display name"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            Email Address
                        </label>
                        <input
                            type="email"
                            value={userProfile.email}
                            disabled
                            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-gray-50 dark:bg-gray-800 text-gray-500 dark:text-gray-400"
                        />
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                            Email cannot be changed. Contact admin if needed.
                        </p>
                    </div>
                    <button
                        onClick={() => saveSettings('profile', userProfile)}
                        disabled={isLoading}
                        className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {isLoading && (
                            <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                        )}
                        {isLoading ? 'Saving...' : 'Save Profile'}
                    </button>
                </div>
            </SettingCard>

            <SettingCard 
                title="Notification Preferences" 
                description="Choose what notifications you want to receive"
            >
                <div className="space-y-4">
                    <Toggle
                        enabled={userProfile.preferences.emailNotifications}
                        onChange={(e) => setUserProfile(prev => ({
                            ...prev,
                            preferences: { ...prev.preferences, emailNotifications: e.target.checked }
                        }))}
                        label="Email Notifications"
                    />
                    <Toggle
                        enabled={userProfile.preferences.weeklyReports}
                        onChange={(e) => setUserProfile(prev => ({
                            ...prev,
                            preferences: { ...prev.preferences, weeklyReports: e.target.checked }
                        }))}
                        label="Weekly Reports"
                    />
                    <Toggle
                        enabled={userProfile.preferences.testCaseUpdates}
                        onChange={(e) => setUserProfile(prev => ({
                            ...prev,
                            preferences: { ...prev.preferences, testCaseUpdates: e.target.checked }
                        }))}
                        label="Test Case Updates"
                    />
                    <button
                        onClick={() => saveSettings('preferences', userProfile.preferences)}
                        disabled={isLoading}
                        className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {isLoading && (
                            <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                        )}
                        {isLoading ? 'Saving...' : 'Save Preferences'}
                    </button>
                </div>
            </SettingCard>
        </div>
    );

    const renderIntegrationsTab = () => (
        <div className="space-y-6">
            <SettingCard 
                title="JIRA Integration" 
                description="Connect with JIRA to sync test cases and issues"
            >
                <div className="space-y-4">
                    <Toggle
                        enabled={integrations.jira.enabled}
                        onChange={(e) => setIntegrations(prev => ({
                            ...prev,
                            jira: { ...prev.jira, enabled: e.target.checked }
                        }))}
                        label="Enable JIRA Integration"
                    />
                    {integrations.jira.enabled && (
                        <>
                            <input
                                type="url"
                                placeholder="JIRA URL (e.g., https://company.atlassian.net)"
                                value={integrations.jira.url}
                                onChange={(e) => setIntegrations(prev => ({
                                    ...prev,
                                    jira: { ...prev.jira, url: e.target.value }
                                }))}
                                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                            />
                            <input
                                type="text"
                                placeholder="Username"
                                value={integrations.jira.username}
                                onChange={(e) => setIntegrations(prev => ({
                                    ...prev,
                                    jira: { ...prev.jira, username: e.target.value }
                                }))}
                                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                            />
                            <input
                                type="password"
                                placeholder="API Token"
                                value={integrations.jira.token}
                                onChange={(e) => setIntegrations(prev => ({
                                    ...prev,
                                    jira: { ...prev.jira, token: e.target.value }
                                }))}
                                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                            />
                            <div className="flex space-x-2">
                                <button
                                    onClick={() => testIntegration('jira')}
                                    disabled={isLoading}
                                    className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-indigo-700 bg-indigo-100 hover:bg-indigo-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 dark:bg-indigo-700 dark:text-white dark:hover:bg-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    {isLoading && (
                                        <svg className="animate-spin -ml-1 mr-2 h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                        </svg>
                                    )}
                                    Test Connection
                                </button>
                                <button
                                    onClick={() => saveSettings('integrations', integrations)}
                                    disabled={isLoading}
                                    className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    {isLoading && (
                                        <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                        </svg>
                                    )}
                                    Save
                                </button>
                            </div>
                        </>
                    )}
                </div>
            </SettingCard>

            <SettingCard 
                title="Azure DevOps Integration" 
                description="Connect with Azure DevOps for work item management"
            >
                <div className="space-y-4">
                    <Toggle
                        enabled={integrations.azure.enabled}
                        onChange={(e) => setIntegrations(prev => ({
                            ...prev,
                            azure: { ...prev.azure, enabled: e.target.checked }
                        }))}
                        label="Enable Azure DevOps Integration"
                    />
                    {integrations.azure.enabled && (
                        <>
                            <input
                                type="url"
                                placeholder="Azure DevOps URL (e.g., https://dev.azure.com/organization)"
                                value={integrations.azure.url}
                                onChange={(e) => setIntegrations(prev => ({
                                    ...prev,
                                    azure: { ...prev.azure, url: e.target.value }
                                }))}
                                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                            />
                            <input
                                type="password"
                                placeholder="Personal Access Token"
                                value={integrations.azure.token}
                                onChange={(e) => setIntegrations(prev => ({
                                    ...prev,
                                    azure: { ...prev.azure, token: e.target.value }
                                }))}
                                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                            />
                            <div className="flex space-x-2">
                                <button
                                    onClick={() => testIntegration('azure')}
                                    disabled={isLoading}
                                    className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-indigo-700 bg-indigo-100 hover:bg-indigo-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 dark:bg-indigo-700 dark:text-white dark:hover:bg-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    {isLoading && (
                                        <svg className="animate-spin -ml-1 mr-2 h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                        </svg>
                                    )}
                                    Test Connection
                                </button>
                                <button
                                    onClick={() => saveSettings('integrations', integrations)}
                                    disabled={isLoading}
                                    className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    {isLoading && (
                                        <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                        </svg>
                                    )}
                                    Save
                                </button>
                            </div>
                        </>
                    )}
                </div>
            </SettingCard>
        </div>
    );

    const renderSystemTab = () => (
        <div className="space-y-6">
            <SettingCard 
                title="AI Model Settings" 
                description="Configure AI model preferences for test case generation"
            >
                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            AI Model
                        </label>
                        <select
                            value={systemSettings.aiModel}
                            onChange={(e) => setSystemSettings(prev => ({ ...prev, aiModel: e.target.value }))}
                            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                        >
                            <option value="gpt-4">GPT-4 (Recommended)</option>
                            <option value="gpt-3.5-turbo">GPT-3.5 Turbo (Faster)</option>
                            <option value="claude-3">Claude 3 (Alternative)</option>
                        </select>
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            Max Test Cases per Generation
                        </label>
                        <input
                            type="number"
                            min="10"
                            max="100"
                            value={systemSettings.maxTestCases}
                            onChange={(e) => setSystemSettings(prev => ({ ...prev, maxTestCases: parseInt(e.target.value) }))}
                            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                        />
                    </div>
                    <Toggle
                        enabled={systemSettings.autoSave}
                        onChange={(e) => setSystemSettings(prev => ({ ...prev, autoSave: e.target.checked }))}
                        label="Auto-save generated test cases"
                    />
                </div>
            </SettingCard>

            <SettingCard 
                title="Appearance" 
                description="Customize the look and feel of the application"
            >
                <div className="space-y-4">
                    <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-700 dark:text-gray-300">Theme</span>
                        <button
                            onClick={toggleTheme}
                            className="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md shadow-sm text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                        >
                            {theme === 'dark' ? 'Switch to Light' : 'Switch to Dark'}
                        </button>
                    </div>
                </div>
            </SettingCard>

            <SettingCard 
                title="Data Management" 
                description="Configure data retention and storage settings"
            >
                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            Data Retention (days)
                        </label>
                        <select
                            value={systemSettings.dataRetention}
                            onChange={(e) => setSystemSettings(prev => ({ ...prev, dataRetention: parseInt(e.target.value) }))}
                            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                        >
                            <option value={30}>30 days</option>
                            <option value={90}>90 days</option>
                            <option value={180}>180 days</option>
                            <option value={365}>1 year</option>
                            <option value={-1}>Forever</option>
                        </select>
                    </div>
                    <button
                        onClick={() => saveSettings('system', systemSettings)}
                        disabled={isLoading}
                        className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {isLoading && (
                            <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                        )}
                        {isLoading ? 'Saving...' : 'Save System Settings'}
                    </button>
                </div>
            </SettingCard>
        </div>
    );

    const tabs = [
        { id: 'profile', label: 'Profile', icon: <UserIcon />, content: renderProfileTab },
        { id: 'integrations', label: 'Integrations', icon: <GlobeAltIcon />, content: renderIntegrationsTab },
        { id: 'system', label: 'System', icon: <CogIcon />, content: renderSystemTab }
    ];

    return (
        <div className="max-w-6xl mx-auto">
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Settings</h1>
                <p className="text-gray-600 dark:text-gray-400 mt-2">
                    Manage your account settings, integrations, and preferences
                </p>
            </div>

            <div className="flex flex-col lg:flex-row gap-6">
                {/* Sidebar */}
                <div className="lg:w-64 flex-shrink-0">
                    <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700">
                        <nav className="space-y-2">
                            {tabs.map((tab) => (
                                <TabButton
                                    key={tab.id}
                                    id={tab.id}
                                    label={tab.label}
                                    icon={tab.icon}
                                    isActive={activeTab === tab.id}
                                    onClick={setActiveTab}
                                />
                            ))}
                        </nav>
                    </div>
                </div>

                {/* Main Content */}
                <div className="flex-1">
                    {tabs.find(tab => tab.id === activeTab)?.content()}
                </div>
            </div>
        </div>
    );
};

export default SettingsPage;
