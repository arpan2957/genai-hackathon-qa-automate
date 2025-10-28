import React, { useState, useEffect } from 'react';
import { auth } from '../firebase';
import toast from 'react-hot-toast';
import { DeleteIcon } from '../components/icons';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://127.0.0.1:8000';

const AdminPage = () => {
    const [users, setUsers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const fetchUsers = async () => {
        setLoading(true);
        setError(null);
        try {
            const token = await auth.currentUser.getIdToken();
            const response = await fetch(`${BACKEND_URL}/api/admin/users`, {
                headers: { 'Authorization': `Bearer ${token}` },
            });
            if (!response.ok) throw new Error((await response.json()).detail || 'Failed to fetch users');
            const data = await response.json();
            setUsers(data);
        } catch (err) {
            setError(err.message);
            toast.error(`Error: ${err.message}`);
        } finally {
            setLoading(false);
        }
    };

    const handleDeleteUser = async (userId) => {
        if (!window.confirm(`Are you sure you want to delete user ${userId} and all their data? This action cannot be undone.`)) {
            return;
        }
        try {
            const token = await auth.currentUser.getIdToken();
            const response = await fetch(`${BACKEND_URL}/api/admin/users/${userId}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` },
            });
            if (!response.ok) throw new Error((await response.json()).detail || 'Failed to delete user');
            toast.success(`User ${userId} deleted successfully.`);
            fetchUsers(); // Refresh the list
        } catch (err) {
            toast.error(`Error deleting user: ${err.message}`);
        }
    };

    useEffect(() => {
        if (auth.currentUser) {
            fetchUsers();
        }
    }, []);

    if (loading) {
        return (
            <div className="text-center py-20">
                <svg className="animate-spin h-8 w-8 text-gray-500 dark:text-gray-400 mx-auto" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <h3 className="mt-2 text-2xl font-semibold text-gray-700 dark:text-gray-300">Loading users...</h3>
            </div>
        );
    }

    if (error) {
        return <div className="text-red-500 text-center py-20">Error: {error}</div>;
    }

    return (
        <div className="p-6 bg-white dark:bg-gray-900 rounded-lg shadow-md">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">Admin Panel - User Management</h2>

            {users.length > 0 ? (
                <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                        <thead className="bg-gray-50 dark:bg-gray-800">
                            <tr>
                                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">UID</th>
                                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Email</th>
                                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Display Name</th>
                                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Created At</th>
                                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
                            {users.map((userProfile) => (
                                <tr key={userProfile.uid}>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-300">{userProfile.uid}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-300">{userProfile.email}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-300">{userProfile.display_name || 'N/A'}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-300">{new Date(userProfile.created_at).toLocaleString()}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                        <button
                                            onClick={() => handleDeleteUser(userProfile.uid)}
                                            className="text-red-600 hover:text-red-900 dark:text-red-500 dark:hover:text-red-400"
                                        >
                                            <DeleteIcon className="h-5 w-5" />
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            ) : (
                <p className="text-gray-500 dark:text-gray-400">No users found.</p>
            )}
        </div>
    );
};

export default AdminPage;
