import React, { useState } from 'react';
import toast from 'react-hot-toast';
import { auth } from '../firebase';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://127.0.0.1:8000';

const CreateTestCaseModal = ({ isOpen, onClose, onSave }) => {
    const [title, setTitle] = useState('');
    const [type, setType] = useState('Positive');
    const [priority, setPriority] = useState('Medium');
    const [steps, setSteps] = useState('');
    const [productName, setProductName] = useState('');
    const [requirementId, setRequirementId] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const handleSave = async () => {
        if (!title || !steps) {
            toast.error('Title and Steps are required.');
            return;
        }

        setIsLoading(true);

        try {
            const user = auth.currentUser;
            if (!user) {
                toast.error("You must be logged in to create test cases.");
                setIsLoading(false);
                return;
            }
            const token = await user.getIdToken();

            const response = await fetch(`${BACKEND_URL}/api/generate-manual-test-case-details`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify({
                    title,
                    steps,
                    product_name: productName,
                    requirement_id: requirementId,
                }),
            });

            if (!response.ok) {
                throw new Error((await response.json()).detail || 'Failed to generate test case details.');
            }

            const aiGeneratedDetails = await response.json();

            const newTestCase = {
                test_case_id: aiGeneratedDetails.test_case_id,
                title,
                type,
                priority,
                steps,
                compliance_tag: aiGeneratedDetails.compliance_tag,
                traceability_id: aiGeneratedDetails.traceability_id,
                domain: aiGeneratedDetails.domain, // Include the AI-generated domain
            };

            onSave(newTestCase, productName); // Pass productName to onSave
            onClose(); // Close modal after saving
            // Reset form
            setTitle('');
            setType('Positive');
            setPriority('Medium');
            setSteps('');
            setProductName('');
            setRequirementId('');
        } catch (error) {
            toast.error(`Error saving test case: ${error.message}`);
        } finally {
            setIsLoading(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50">
            <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-2xl w-full max-w-2xl shadow-2xl flex flex-col max-h-[90vh]">
                <div className="flex items-center justify-between p-5 border-b border-gray-200 dark:border-gray-700">
                    <h3 className="text-lg font-bold text-gray-900 dark:text-white">Create New Test Case</h3>
                    <button onClick={onClose} className="text-gray-400 hover:text-gray-800 dark:hover:text-white text-2xl">&times;</button>
                </div>
                
                <div className="flex-1 overflow-y-auto p-6 space-y-4">
                    <div>
                        <label htmlFor="tc-title" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Title <span className="text-red-500">*</span></label>
                        <input id="tc-title" type="text" value={title} onChange={(e) => setTitle(e.target.value)} className="w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg p-3 text-sm focus:ring-cyan-500 focus:border-cyan-500" placeholder="e.g., Verify user can change password" />
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <label htmlFor="tc-type" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Type</label>
                            <select id="tc-type" value={type} onChange={(e) => setType(e.target.value)} className="w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg p-3 text-sm text-gray-800 dark:text-gray-200 focus:ring-cyan-500 focus:border-cyan-500">
                                <option>Positive</option>
                                <option>Negative</option>
                            </select>
                        </div>
                        <div>
                            <label htmlFor="tc-priority" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Priority</label>
                            <select id="tc-priority" value={priority} onChange={(e) => setPriority(e.target.value)} className="w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg p-3 text-sm text-gray-800 dark:text-gray-200 focus:ring-cyan-500 focus:border-cyan-500">
                                <option>Critical</option>
                                <option>High</option>
                                <option>Medium</option>
                                <option>Low</option>
                            </select>
                        </div>
                    </div>

                    <div>
                        <label htmlFor="tc-steps" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Steps <span className="text-red-500">*</span></label>
                        <textarea id="tc-steps" rows="8" value={steps} onChange={(e) => setSteps(e.target.value)} className="w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg p-3 text-base focus:ring-cyan-500 focus:border-cyan-500" placeholder="e.g.,
1. Navigate to login page
2. Enter valid credentials
3. Click login button"></textarea>
                    </div>

                    <div>
                        <label htmlFor="tc-product-name" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Product Name (Optional)</label>
                        <input id="tc-product-name" type="text" value={productName} onChange={(e) => setProductName(e.target.value)} className="w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg p-3 text-sm focus:ring-cyan-500 focus:border-cyan-500" placeholder="e.g., HealthRecord Pro" />
                    </div>

                    <div>
                        <label htmlFor="tc-requirement-id" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Requirement ID (Optional)</label>
                        <input id="tc-requirement-id" type="text" value={requirementId} onChange={(e) => setRequirementId(e.target.value)} className="w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg p-3 text-sm focus:ring-cyan-500 focus:border-cyan-500" placeholder="e.g., PROJ-REQ-123" />
                    </div>
                </div>

                <div className="p-5 bg-gray-50 dark:bg-gray-900/80 border-t border-gray-200 dark:border-gray-700 flex justify-end items-center space-x-3 rounded-b-2xl">
                    <button onClick={onClose} className="px-4 py-2 text-sm font-semibold text-gray-700 dark:text-gray-300 bg-transparent border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700">
                        Cancel
                    </button>
                    <button onClick={handleSave} disabled={isLoading} className="px-5 py-2.5 text-sm font-semibold text-white bg-cyan-600 rounded-lg hover:opacity-90 disabled:bg-slate-400 dark:disabled:bg-slate-600 disabled:cursor-not-allowed">
                        {isLoading ? 'Saving...' : 'Save Test Case'}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default CreateTestCaseModal;
