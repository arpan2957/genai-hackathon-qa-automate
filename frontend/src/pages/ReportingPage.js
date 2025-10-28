import React, { useState, useEffect, useCallback } from 'react';
import { auth } from '../firebase';
import toast from 'react-hot-toast';
import { DownloadIcon } from '../components/icons';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://127.0.0.1:8000';

const ReportingPage = () => {
    const [auditLogs, setAuditLogs] = useState([]);
    const [auditSummary, setAuditSummary] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [filters, setFilters] = useState({
        eventType: '',
        startDate: '',
        endDate: ''
    });

    const fetchAuditData = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const token = await auth.currentUser.getIdToken();
            const headers = { 'Authorization': `Bearer ${token}` };

            // Fetch logs
            let logsUrl = `${BACKEND_URL}/api/reports/audit-logs?`;
            if (filters.eventType) logsUrl += `event_type=${filters.eventType}&`;
            if (filters.startDate) logsUrl += `start_date=${filters.startDate}&`;
            if (filters.endDate) logsUrl += `end_date=${filters.endDate}&`;
            const logsResponse = await fetch(logsUrl, { headers });
            if (!logsResponse.ok) throw new Error('Failed to fetch audit logs');
            const logsData = await logsResponse.json();
            setAuditLogs(logsData);

            // Fetch summary
            let summaryUrl = `${BACKEND_URL}/api/reports/summary?`;
            if (filters.startDate) summaryUrl += `start_date=${filters.startDate}&`;
            if (filters.endDate) summaryUrl += `end_date=${filters.endDate}&`;
            const summaryResponse = await fetch(summaryUrl, { headers });
            if (!summaryResponse.ok) throw new Error('Failed to fetch audit summary');
            const summaryData = await summaryResponse.json();
            setAuditSummary(summaryData);

        } catch (err) {
            setError(err.message);
            toast.error(`Error: ${err.message}`);
        } finally {
            setLoading(false);
        }
    }, [filters, setAuditLogs, setAuditSummary, setLoading, setError]);

    useEffect(() => {
        if (auth.currentUser) {
            fetchAuditData();
        }
    }, [fetchAuditData, filters]);

    const handleFilterChange = (e) => {
        setFilters({
            ...filters,
            [e.target.name]: e.target.value
        });
    };

    const downloadReport = (format) => {
        let data = '';
        let filename = `audit_report_${new Date().toISOString()}`; 

        if (format === 'json') {
            data = JSON.stringify({ logs: auditLogs, summary: auditSummary }, null, 2);
            filename += '.json';
        } else if (format === 'csv') {
            // Basic CSV conversion for logs
            const headers = Object.keys(auditLogs[0] || {});
            const csvRows = [
                headers.join(','),
                ...auditLogs.map(row => headers.map(fieldName => JSON.stringify(row[fieldName])).join(','))
            ];
            data = csvRows.join('\n');
            filename += '.csv';
        } else {
            return;
        }

        const blob = new Blob([data], { type: `text/${format}` });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        toast.success(`Report downloaded as ${filename}`);
    };

    if (loading) {
        return (
            <div className="text-center py-20">
                <svg className="animate-spin h-8 w-8 text-gray-500 dark:text-gray-400 mx-auto" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <h3 className="mt-2 text-2xl font-semibold text-gray-700 dark:text-gray-300">Loading audit data...</h3>
            </div>
        );
    }

    if (error) {
        return <div className="text-red-500 text-center py-20">Error: {error}</div>;
    }

    return (
        <div className="p-6 bg-white dark:bg-gray-900 rounded-lg shadow-md">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">Audit & Reporting</h2>

            {/* Filters */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <div>
                    <label htmlFor="eventType" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Event Type</label>
                    <input
                        type="text"
                        name="eventType"
                        id="eventType"
                        value={filters.eventType}
                        onChange={handleFilterChange}
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white px-3 py-2 text-sm"
                        placeholder="e.g., user_login"
                    />
                </div>
                <div>
                    <label htmlFor="startDate" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Start Date</label>
                    <input
                        type="datetime-local"
                        name="startDate"
                        id="startDate"
                        value={filters.startDate}
                        onChange={handleFilterChange}
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white px-3 py-2 text-sm"
                    />
                </div>
                <div>
                    <label htmlFor="endDate" className="block text-sm font-medium text-gray-700 dark:text-gray-300">End Date</label>
                    <input
                        type="datetime-local"
                        name="endDate"
                        id="endDate"
                        value={filters.endDate}
                        onChange={handleFilterChange}
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white px-3 py-2 text-sm"
                    />
                </div>
            </div>

            {/* Download Buttons */}
            <div className="flex justify-end space-x-2 mb-6">
                <button
                    onClick={() => downloadReport('json')}
                    className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                >
                    <DownloadIcon className="-ml-1 mr-2 h-5 w-5" />
                    Download JSON
                </button>
                <button
                    onClick={() => downloadReport('csv')}
                    className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-indigo-700 bg-indigo-100 hover:bg-indigo-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 dark:bg-indigo-700 dark:text-white dark:hover:bg-indigo-600"
                >
                    <DownloadIcon className="-ml-1 mr-2 h-5 w-5" />
                    Download CSV
                </button>
            </div>

            {/* Summary */}
            <div className="mb-8">
                <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">Audit Summary</h3>
                {auditSummary.length > 0 ? (
                    <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                        {auditSummary.map((item, index) => (
                            <p key={index} className="text-gray-700 dark:text-gray-300"><strong>{item.event_type}:</strong> {item.count}</p>
                        ))}
                    </div>
                ) : (
                    <p className="text-gray-500 dark:text-gray-400">No summary data available.</p>
                )}
            </div>

            {/* Audit Logs Table */}
            <div>
                <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">Detailed Audit Logs</h3>
                {auditLogs.length > 0 ? (
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                            <thead className="bg-gray-50 dark:bg-gray-800">
                                <tr>
                                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Timestamp</th>
                                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">User ID</th>
                                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Event Type</th>
                                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Details</th>
                                </tr>
                            </thead>
                            <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
                                {auditLogs.map((log, index) => (
                                    <tr key={index}>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-300">{new Date(log.timestamp).toLocaleString()}</td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-300">{log.user_id}</td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-300">{log.event_type}</td>
                                        <td className="px-6 py-4 text-sm text-gray-900 dark:text-gray-300">
                                            {Object.entries(log).map(([key, value]) => {
                                                if (!['timestamp', 'user_id', 'event_type'].includes(key)) {
                                                    return <div key={key}><span className="font-semibold">{key}:</span> {JSON.stringify(value)}</div>;
                                                }
                                                return null;
                                            })}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                ) : (
                    <p className="text-gray-500 dark:text-gray-400">No audit logs available for the selected filters.</p>
                )}
            </div>
        </div>
    );
};

export default ReportingPage;
