import React, { useState, useEffect, useCallback } from 'react';
import { auth } from '../firebase';
import toast from 'react-hot-toast';
import { config } from '../config';

const BACKEND_URL = config.BACKEND_URL;

const AdminReportingPage = ({ prefilledFilters = {} }) => {
    const [auditLogs, setAuditLogs] = useState([]);
    const [auditSummary, setAuditSummary] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [filters, setFilters] = useState({
        user_id: prefilledFilters.user_id || '',
        event_type: prefilledFilters.event_type || '',
        start_date: '',
        end_date: ''
    });


    const fetchAuditData = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const token = await auth.currentUser.getIdToken();
            const headers = { 'Authorization': `Bearer ${token}` };

            // Build query params
            const queryParams = new URLSearchParams();
            if (filters.user_id) queryParams.append('user_id', filters.user_id);
            if (filters.event_type) queryParams.append('event_type', filters.event_type);
            
            // Handle date parameters with validation
            if (filters.start_date) {
                try {
                    const startDate = new Date(filters.start_date);
                    if (!isNaN(startDate.getTime())) {
                        queryParams.append('start_date', startDate.toISOString());
                    }
                } catch (e) {
                    console.warn('Invalid start_date format:', filters.start_date, e);
                }
            }
            
            if (filters.end_date) {
                try {
                    const endDate = new Date(filters.end_date);
                    if (!isNaN(endDate.getTime())) {
                        queryParams.append('end_date', endDate.toISOString());
                    }
                } catch (e) {
                    console.warn('Invalid end_date format:', filters.end_date, e);
                }
            }
            const queryString = queryParams.toString();

            // Fetch logs
            const logsResponse = await fetch(`${BACKEND_URL}/api/admin/audit-logs?${queryString}`, { headers });
            if (!logsResponse.ok) {
                const errorData = await logsResponse.json().catch(() => ({ detail: logsResponse.statusText }));
                throw new Error(errorData.detail || `Failed to fetch audit logs: ${logsResponse.statusText}`);
            }
            const logsData = await logsResponse.json();
            setAuditLogs(logsData);

            // Fetch summary
            const summaryResponse = await fetch(`${BACKEND_URL}/api/admin/audit-summary?${queryString}`, { headers });
            if (!summaryResponse.ok) {
                const errorData = await summaryResponse.json().catch(() => ({ detail: summaryResponse.statusText }));
                throw new Error(errorData.detail || `Failed to fetch audit summary: ${summaryResponse.statusText}`);
            }
            const summaryData = await summaryResponse.json();
            setAuditSummary(summaryData);

        } catch (err) {
            console.error('Audit data fetch error:', err);
            setError(err.message);
            
            // Show professional error messages
            if (err.message.includes('BigQuery') || err.message.includes('configuration')) {
                toast.error('Unable to load audit data. Please try again later.', { duration: 6000 });
            } else {
                toast.error(`Error loading audit data: ${err.message}`, { duration: 6000 });
            }
        } finally {
            setLoading(false);
        }
    }, [filters]);

    useEffect(() => {
        if (auth.currentUser) {
            fetchAuditData();
        }
    }, [fetchAuditData]);

    const handleFilterChange = (e) => {
        setFilters({
            ...filters,
            [e.target.name]: e.target.value
        });
    };

    const handleFilterSubmit = (e) => {
        e.preventDefault();
        fetchAuditData();
    }

    return (
        <div className="p-6 bg-white dark:bg-gray-900 rounded-lg shadow-md">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">Admin Audit & Reporting</h2>
            
            <div className="bg-yellow-100 border-l-4 border-yellow-500 text-yellow-700 p-4 mb-6 rounded-md" role="alert">
                <p className="font-bold">Audit Access</p>
                <p>You are accessing sensitive user audit data. All access to this page is logged.</p>
            </div>


            {/* Filters */}
            <form onSubmit={handleFilterSubmit} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-6 p-4 border border-gray-200 dark:border-gray-700 rounded-lg">
                <div>
                    <label htmlFor="user_id" className="block text-sm font-medium text-gray-700 dark:text-gray-300">User ID</label>
                    <input type="text" name="user_id" id="user_id" value={filters.user_id} onChange={handleFilterChange} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white px-3 py-2 text-sm" />
                </div>
                <div>
                    <label htmlFor="event_type" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Event Type</label>
                    <input type="text" name="event_type" id="event_type" value={filters.event_type} onChange={handleFilterChange} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white px-3 py-2 text-sm" />
                </div>
                <div>
                    <label htmlFor="start_date" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Start Date</label>
                    <input type="datetime-local" name="start_date" id="start_date" value={filters.start_date} onChange={handleFilterChange} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white px-3 py-2 text-sm" />
                </div>
                <div>
                    <label htmlFor="end_date" className="block text-sm font-medium text-gray-700 dark:text-gray-300">End Date</label>
                    <input type="datetime-local" name="end_date" id="end_date" value={filters.end_date} onChange={handleFilterChange} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white px-3 py-2 text-sm" />
                </div>
                <div className="flex items-end">
                    <button type="submit" className="w-full inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500">Filter</button>
                </div>
            </form>

            {loading ? (
                <div className="flex items-center justify-center min-h-96">
                    <div className="text-center">
                        <svg className="animate-spin h-12 w-12 text-indigo-600 mx-auto mb-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">Loading Audit Data</h3>
                        <p className="text-gray-600 dark:text-gray-400">Fetching audit logs and summary statistics...</p>
                    </div>
                </div>
            ) : error ? (
                <div className="text-red-500 text-center py-20">Error: {error}</div>
            ) : (
                <>
                    {/* Summary */}
                    <div className="mb-8">
                        <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">Analytics View (Summary)</h3>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            {auditSummary.length > 0 ? auditSummary.map((item, index) => (
                                <div key={index} className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 text-center">
                                    <p className="text-sm font-medium text-gray-500 dark:text-gray-400">{item.event_type}</p>
                                    <p className="text-3xl font-bold text-gray-900 dark:text-white">{item.count}</p>
                                </div>
                            )) : <p className="text-gray-500 dark:text-gray-400">No summary data.</p>}
                        </div>
                    </div>

                    {/* Audit Logs Table */}
                    <div>
                        <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">Audit View (Detailed Logs)</h3>
                        <div className="overflow-x-auto">
                            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                                <thead className="bg-gray-50 dark:bg-gray-800">
                                    <tr>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Timestamp</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">User</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Event</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">IP Address</th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Details</th>
                                    </tr>
                                </thead>
                                <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
                                    {auditLogs.length > 0 ? auditLogs.map((log, index) => (
                                        <tr key={index}>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-300">{new Date(log.timestamp).toLocaleString()}</td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-300">{log.email || log.user_id}</td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-300">{log.event_type}</td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-300">{log.ip_address}</td>
                                            <td className="px-6 py-4 text-sm text-gray-900 dark:text-gray-300 font-mono text-xs">{log.event_details}</td>
                                        </tr>
                                    )) : (
                                        <tr>
                                            <td colSpan="5" className="text-center py-10 text-gray-500 dark:text-gray-400">No audit logs found for the selected filters.</td>
                                        </tr>
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </>
            )}
        </div>
    );
};

export default AdminReportingPage;
