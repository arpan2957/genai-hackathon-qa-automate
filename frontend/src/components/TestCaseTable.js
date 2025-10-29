import React, { useState, useEffect } from 'react';
import { EmptyStateIcon, DeleteIcon, ThumbsUpIcon, ThumbsDownIcon, ThumbsUpSolidIcon, JiraIcon, AzureDevOpsIcon, PolarionIcon } from './icons';
import FeedbackModal from './FeedbackModal';
import toast from 'react-hot-toast';

const TestCaseTable = ({ 
    testCases, 
    expandedRows = new Set(), 
    toggleRow = null, 
    copiedId = null, 
    handleCopy = null, 
    handleCreateALMIssue = null, 
    handleDelete = null,
    requirement, // New prop for the requirement text
    getAuthToken, // New prop to get the auth token
    backendUrl
}) => {

    const [isFeedbackModalOpen, setFeedbackModalOpen] = useState(false);
    const [selectedTestCaseForFeedback, setSelectedTestCaseForFeedback] = useState(null);
    const [feedbackSubmittedId, setFeedbackSubmittedId] = useState(null);


    useEffect(() => {
        if (feedbackSubmittedId) {
            const timer = setTimeout(() => setFeedbackSubmittedId(null), 2000);
            return () => clearTimeout(timer);
        }
    }, [feedbackSubmittedId]);

    const handleOpenFeedbackModal = (testCase) => {
        setSelectedTestCaseForFeedback(testCase);
        setFeedbackModalOpen(true);
    };

    const handleCloseFeedbackModal = () => {
        setFeedbackModalOpen(false);
        setSelectedTestCaseForFeedback(null);
    };

    const handleSubmitFeedback = async (testCase, correction) => {
        const token = await getAuthToken();

        const payload = {
            requirement: requirement || testCase.title,
            original_test_case: testCase,
            rating: 'bad',
            corrected_test_case: correction ? { ...testCase, steps: correction } : null
        };

        try {
            const response = await fetch(`${backendUrl}/api/feedback`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(payload)
            });

            if (response.ok) {
                toast.success('Feedback submitted successfully!');
            } else {
                const error = await response.json();
                toast.error(`Failed to submit feedback: ${error.detail}`);
            }
        } catch (error) {
            toast.error(`Failed to submit feedback: ${error.message}`);
        }
    };

    const StatusBadge = ({ type }) => {
        const styles = { 
            'Positive': 'bg-green-100 text-green-800 dark:bg-green-500/20 dark:text-green-300', 
            'Negative': 'bg-red-100 text-red-800 dark:bg-red-500/20 dark:text-red-300' 
        };
        return <span className={`px-2 py-1 text-xs font-medium rounded-full ${styles[type] || 'bg-gray-100 text-gray-800 dark:bg-gray-500/20 dark:text-gray-300'}`}>{type}</span>;
    };

    const PriorityText = ({ priority }) => {
        const styles = { 
            'Critical': 'text-red-700 dark:text-red-500',
            'High': 'text-red-600 dark:text-red-400', 
            'Medium': 'text-orange-600 dark:text-orange-400', 
            'Low': 'text-sky-600 dark:text-sky-400' 
        };
        return <span className={`font-semibold ${styles[priority] || 'text-gray-700 dark:text-gray-300'}`}>{priority}</span>;
    };

    if (!testCases || testCases.length === 0) {
        return (
            <div className="text-center py-16">
                <EmptyStateIcon className="mx-auto h-12 w-12 text-gray-400" />
                <h3 className="mt-2 text-sm font-semibold text-gray-900 dark:text-white">No test cases found</h3>
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">There are no test cases matching your criteria.</p>
            </div>
        );
    }

    return (
        <>
            <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden overflow-x-auto" data-testid="results-table">
                <table className="w-full text-sm text-left">
                    <thead className="text-xs text-gray-500 dark:text-gray-400 uppercase bg-gray-50 dark:bg-gray-900/50">
                        <tr>
                            <th scope="col" className="p-4">ID</th>
                            <th scope="col" className="p-4">Title</th>
                            <th scope="col" className="p-4">Type</th>
                            <th scope="col" className="p-4">Priority</th>
                            <th scope="col" className="p-4">Compliance Tag</th>
                            <th scope="col" className="p-4">Actions</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
                        {testCases.map((tc) => (
                            <React.Fragment key={`${tc.docId}-${tc.test_case_id}`}>
                                <tr className="hover:bg-gray-50 dark:hover:bg-gray-800/60 transition-colors">
                                    <td onClick={() => toggleRow && toggleRow(tc.test_case_id)} className={`p-4 font-medium text-cyan-600 dark:text-cyan-400 whitespace-nowrap ${toggleRow ? 'cursor-pointer' : ''}`}>
                                        {toggleRow && (
                                            <span className="mr-2">
                                                {expandedRows.has(tc.test_case_id) ? '▼' : '►'}
                                            </span>
                                        )}
                                        {tc.test_case_id}
                                    </td>
                                    <td className="p-4 text-gray-700 dark:text-gray-300">{tc.title}</td>
                                    <td className="p-4"><StatusBadge type={tc.type} /></td>
                                    <td className="p-4"><PriorityText priority={tc.priority} /></td>
                                    <td className="p-4"><span className="font-mono px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800 dark:bg-blue-500/20 dark:text-blue-300">{tc.compliance_tag}</span></td>
                                    <td className="p-4 text-right">
                                        <div className="flex items-center justify-end space-x-1 flex-nowrap">
                                            {handleCopy && <button onClick={() => handleCopy(tc)} className="p-2 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md">{copiedId === tc.test_case_id ? 'Copied!' : 'Copy'}</button>}
                                            {handleCreateALMIssue && (
                                                <div className="flex items-center space-x-1">
                                                    <button onClick={() => handleCreateALMIssue(tc, 'jira')} className="p-2 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md" title="Create Jira Ticket">
                                                        <JiraIcon className="h-5 w-5" />
                                                    </button>
                                                    <button onClick={() => handleCreateALMIssue(tc, 'azure_devops')} className="p-2 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md" title="Create Azure DevOps Ticket">
                                                        <AzureDevOpsIcon className="h-5 w-5" />
                                                    </button>
                                                    <button onClick={() => handleCreateALMIssue(tc, 'polarion')} className="p-2 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md" title="Create Polarion Ticket">
                                                        <PolarionIcon className="h-5 w-5" />
                                                    </button>
                                                </div>
                                            )}
                                            <button onClick={() => { handleDelete(tc.test_case_id, tc.docId); }} aria-label="delete" className="p-2 text-red-500 hover:bg-red-100 dark:hover:bg-red-500/20 rounded-md"><DeleteIcon className="h-4 w-4" /></button>
                                        </div>
                                    </td>
                                </tr>
                                {toggleRow && expandedRows.has(tc.test_case_id) && (
                                    <tr className="bg-gray-50/50 dark:bg-gray-800/50">
                                        <td colSpan="6" className="p-4">
                                            <div className="p-4 bg-gray-100 dark:bg-gray-900/80 rounded-lg">
                                                <div className="flex justify-between items-center mb-2">
                                                    <h4 className="font-semibold text-gray-700 dark:text-white">Test Steps:</h4>
                                                    {tc.traceability_id && <p className="text-xs text-gray-500 dark:text-gray-400">Traceability ID: {tc.traceability_id}</p>}
                                                </div>
                                                {Array.isArray(tc.steps) ? (
                                                    <table className="w-full text-sm">
                                                        <thead className="text-xs text-gray-500 dark:text-gray-400 uppercase">
                                                            <tr>
                                                                <th className="p-2 text-left w-16">Step</th>
                                                                <th className="p-2 text-left">Action</th>
                                                                <th className="p-2 text-left">Expected Result</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                                                            {tc.steps.map((step) => (
                                                                <tr key={step.step}>
                                                                    <td className="p-2 align-top text-gray-700 dark:text-gray-300">{step.step}</td>
                                                                    <td className="p-2 align-top text-gray-700 dark:text-gray-300">{step.action}</td>
                                                                    <td className="p-2 align-top text-gray-700 dark:text-gray-300">{step.expected_result}</td>
                                                                </tr>
                                                            ))}
                                                        </tbody>
                                                    </table>
                                                ) : (
                                                    <p className="text-sm text-gray-600 dark:text-gray-300 whitespace-pre-wrap">{tc.steps}</p>
                                                )}
                                                <div className="mt-4">
                                                    <h5 className="font-semibold text-gray-700 dark:text-white mb-2">Feedback</h5>
                                                    <div className="flex items-center space-x-2">
                                                        <button onClick={() => {toast.success('Thanks for your feedback!'); setFeedbackSubmittedId(tc.test_case_id);}} className={`p-2 rounded-md text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700`}>
                                                            {feedbackSubmittedId === tc.test_case_id ? <ThumbsUpSolidIcon className="h-5 w-5 text-green-500" /> : <ThumbsUpIcon className="h-5 w-5" />}
                                                        </button>
                                                        <button onClick={() => handleOpenFeedbackModal(tc)} className={`p-2 rounded-md text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700`}><ThumbsDownIcon className="h-5 w-5" /></button>
                                                    </div>
                                                </div>
                                            </div>
                                        </td>
                                    </tr>
                                )}
                            </React.Fragment>
                        ))}
                    </tbody>
                </table>
            </div>
            {isFeedbackModalOpen && (
                <FeedbackModal
                    isOpen={isFeedbackModalOpen}
                    onClose={handleCloseFeedbackModal}
                    onSubmit={(correction) => {
                        handleSubmitFeedback(selectedTestCaseForFeedback, correction);
                        handleCloseFeedbackModal();
                    }}
                    title="Provide Feedback"
                    message="Please provide details about what's wrong with the test case."
                />
            )}
        </>
    );
};

export default TestCaseTable;
