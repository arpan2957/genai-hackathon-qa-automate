import React, { useState, useEffect, useMemo, useCallback } from 'react';
// GEMINI_FIX_ATTEMPT: 2023-10-27 10:00 - Minimal test comment
import Sidebar from '../components/Sidebar';
import Header from '../components/Header';
import TestCaseTable from '../components/TestCaseTable';
import AiModal from '../components/AiModal';
import LoginModal from '../components/LoginModal';
import CreateTestCaseModal from '../components/CreateTestCaseModal';
import ConfirmationModal from '../components/ConfirmationModal';
import EmptyState from '../components/EmptyState';
import { auth } from '../firebase';
import { onAuthStateChanged } from 'firebase/auth';
import { ChevronDownIcon, EmptyStateIcon, SearchIcon } from '../components/icons';
import toast from 'react-hot-toast';

import KnowledgeBasePage from './KnowledgeBasePage';
import ReportingPage from './ReportingPage';
import AdminPage from './AdminPage';
import AdminReportingPage from './AdminReportingPage';
import FineTuningPage from './FineTuningPage';
import SettingsPage from './SettingsPage';
import { config } from '../config';

const BACKEND_URL = config.BACKEND_URL;

// GEMINI_TEST_COMMENT
const AppPage = () => {
    const [isMobileSidebarOpen, setMobileSidebarOpen] = useState(false);
    const [isSidebarPinned, setSidebarPinned] = useState(false);
    const [isAiModalOpen, setAiModalOpen] = useState(false);
    const [isCreateModalOpen, setCreateModalOpen] = useState(false);
    const [isLoginModalOpen, setLoginModalOpen] = useState(false);
    const [user, setUser] = useState(null);
    const [isAdmin, setIsAdmin] = useState(false);
    const [adminVerified, setAdminVerified] = useState(false);
    const [adminVerifying, setAdminVerifying] = useState(false);
    const [finalizedDocs, setFinalizedDocs] = useState([]); // Will hold [{id, product_name, domains}] from DB
    const [searchQuery, setSearchQuery] = useState("");
    const [openDomains, setOpenDomains] = useState(new Set());
    const [isConfirmModalOpen, setConfirmModalOpen] = useState(false);
    const [confirmModalProps, setConfirmModalProps] = useState({});
    const [itemToDelete, setItemToDelete] = useState(null);
    const [isLoadingCases, setIsLoadingCases] = useState(true); // New loading state
    const [selectedProduct, setSelectedProduct] = useState(null);
    const [expandedRows, setExpandedRows] = useState(new Set());
    const [currentPage, setCurrentPage] = useState('testcases');
    const [prefilledFilters, setPrefilledFilters] = useState({});

    const [copiedId, setCopiedId] = useState(null);

    const handleCopy = (tc) => {
        navigator.clipboard.writeText(JSON.stringify(tc, null, 2)).then(() => {
            setCopiedId(tc.test_case_id);
            toast.success("Copied to clipboard!");
            setTimeout(() => setCopiedId(null), 2000);
        });
    };

    const handleCreateALMIssue = async (testCase, alm) => {
        if (!auth.currentUser) return;
        try {
            const token = await auth.currentUser.getIdToken();
            const response = await fetch(`${BACKEND_URL}/api/integrations/${alm}/create-issue`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify({
                    test_case: testCase,
                    project_key: 'PROJ', // Replace with a dynamic project key if needed
                }),
            });
            if (!response.ok) throw new Error((await response.json()).detail || `Failed to create ${alm} issue.`);
            const data = await response.json();
            toast.success(<span>{alm} issue <a href={data.url} target="_blank" rel="noopener noreferrer" className="underline">{data.issue_key}</a> created!</span>);
        } catch (error) {
            toast.error(`Error creating ${alm} issue: ${error.message}`);
        }
    };

    // --- Admin Verification ---
    const verifyAdminStatus = useCallback(async () => {
        if (!auth.currentUser || adminVerifying) return;
        
        setAdminVerifying(true);
        try {
            const token = await auth.currentUser.getIdToken();
            const response = await fetch(`${BACKEND_URL}/api/admin/verify-status`, {
                headers: { 'Authorization': `Bearer ${token}` },
            });
            
            if (response.ok) {
                setAdminVerified(true);
                return true;
            } else {
                // Get the error details from the response
                let errorDetail = 'Unknown error';
                try {
                    const errorData = await response.json();
                    errorDetail = errorData.detail || `HTTP ${response.status}`;
                } catch (e) {
                    errorDetail = `HTTP ${response.status} - ${response.statusText}`;
                }
                
                console.error('Admin verification failed:', {
                    status: response.status,
                    statusText: response.statusText,
                    detail: errorDetail
                });
                
                setIsAdmin(false);
                setAdminVerified(false);
                if (currentPage.startsWith('admin')) {
                    setCurrentPage('testcases');
                    toast.error(`Access denied: ${errorDetail}`);
                }
                return false;
            }
        } catch (error) {
            console.error('Error verifying admin status:', error);
            
            // Try to get more detailed error information
            if (error.response) {
                console.error('Response status:', error.response.status);
                console.error('Response data:', error.response.data);
            }
            
            setIsAdmin(false);
            setAdminVerified(false);
            if (currentPage.startsWith('admin')) {
                setCurrentPage('testcases');
                toast.error(`Failed to verify admin access: ${error.message || 'Network error'}`);
            }
            return false;
        } finally {
            setAdminVerifying(false);
        }
    }, [adminVerifying, currentPage]);

    // --- Data Fetching and Persistence ---
    const fetchFinalizedCases = async () => {
        if (!auth.currentUser) return;
        setIsLoadingCases(true);
        try {
            const token = await auth.currentUser.getIdToken();
            const response = await fetch(`${BACKEND_URL}/api/finalized-cases`, {
                headers: { 'Authorization': `Bearer ${token}` },
            });
            if (!response.ok) {
                throw new Error('Failed to fetch test cases.');
            }
            const data = await response.json();
            setFinalizedDocs(data);
        } catch (error) {
            toast.error(`Error fetching data: ${error.message}`);
        } finally {
            setIsLoadingCases(false);
        }
    };

    useEffect(() => {
        const unsubscribe = onAuthStateChanged(auth, async (currentUser) => {
            setUser(currentUser);
            if (currentUser) {
                const idTokenResult = await currentUser.getIdTokenResult();
                setIsAdmin(idTokenResult.claims.admin === true);
                setLoginModalOpen(false);
                fetchFinalizedCases();
            } else {
                setLoginModalOpen(true);
                setIsAdmin(false);
                setFinalizedDocs([]); // Clear data on logout
            }
        });
        return () => unsubscribe();
    }, []);

    useEffect(() => {
        setOpenDomains(new Set()); // Clear open domains when product or data changes
    }, [selectedProduct, finalizedDocs]);

    // Verify admin status when accessing admin pages
    useEffect(() => {
        if (currentPage.startsWith('admin') && isAdmin && !adminVerified && !adminVerifying) {
            verifyAdminStatus();
        }
    }, [currentPage, isAdmin, adminVerified, adminVerifying, verifyAdminStatus]);

    // --- Event Handlers ---

    const handleFinalize = async (generatedResult) => {
        if (!auth.currentUser) return;
        try {
            const token = await auth.currentUser.getIdToken();

            // Check if a document for this product_name already exists
            const existingDocIndex = finalizedDocs.findIndex(
                (doc) => doc.product_name === generatedResult.product_name
            );

            if (existingDocIndex !== -1) {
                // Product already exists, merge new domains/test cases
                const existingDoc = finalizedDocs[existingDocIndex];
                const updatedDomains = [...existingDoc.domains];

                generatedResult.domains.forEach(newDomainGroup => {
                    const existingDomainIndex = updatedDomains.findIndex(
                        d => d.domain === newDomainGroup.domain
                    );

                    if (existingDomainIndex !== -1) {
                        // Domain exists, merge test cases
                        updatedDomains[existingDomainIndex].test_cases = [
                            ...updatedDomains[existingDomainIndex].test_cases,
                            ...newDomainGroup.test_cases,
                        ];
                    } else {
                        // New domain, add it
                        updatedDomains.push(newDomainGroup);
                    }
                });

                const updatedDoc = { product_name: existingDoc.product_name, domains: updatedDomains, requirement: generatedResult.requirement };

                // Update the existing document in the backend
                await fetch(`${BACKEND_URL}/api/finalized-cases/${existingDoc.id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                    body: JSON.stringify(updatedDoc),
                });
                toast.success(`Product "${generatedResult.product_name}" updated!`);

            } else {
                // Product does not exist, create a new one
                await fetch(`${BACKEND_URL}/api/finalized-cases`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                    body: JSON.stringify(generatedResult),
                });
                toast.success(`Product "${generatedResult.product_name}" saved!`);
            }

            await fetchFinalizedCases(); // Refresh list to reflect changes
        } catch (error) {
            toast.error(`Error saving: ${error.message}`);
        }
    };

    const handleSaveManually = async (newTestCase, productName) => {
        if (!auth.currentUser) return;
        try {
            const token = await auth.currentUser.getIdToken();

            const targetProductName = productName || 'Manual Entries';
            let targetDoc = finalizedDocs.find(d => d.product_name === targetProductName);

            if (targetDoc) {
                // Target product doc exists, update it
                const newDomains = [...targetDoc.domains];
                let targetDomainGroup = newDomains.find(d => d.domain === newTestCase.domain);

                if (targetDomainGroup) {
                    // Target domain exists, add test case to it
                    targetDomainGroup.test_cases.push(newTestCase);
                } else {
                    // Target domain does not exist, create it and add test case
                    newDomains.push({ domain: newTestCase.domain, test_cases: [newTestCase] });
                }

                const updatedDoc = { product_name: targetDoc.product_name, domains: newDomains };

                await fetch(`${BACKEND_URL}/api/finalized-cases/${targetDoc.id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                    body: JSON.stringify(updatedDoc),
                });
                toast.success('Manual test case added!');

            } else {
                // Target product doc does not exist, create a new one
                await fetch(`${BACKEND_URL}/api/finalized-cases`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                    body: JSON.stringify({ product_name: targetProductName, domains: [{ domain: newTestCase.domain, test_cases: [newTestCase] }] }),
                });
                toast.success(`Product "${targetProductName}" created and test case added!`);
            }
            await fetchFinalizedCases(); // Refresh list
        } catch (error) {
            toast.error(`Error saving manual test case: ${error.message}`);
        }
    };

    const handleDeleteTestCase = (caseId, docId) => {
        setItemToDelete({ caseId, docId });
        setConfirmModalProps({
            title: "Delete Test Case",
            message: "Are you sure you want to delete this test case? This action cannot be undone.",
            onConfirm: executeDelete,
        });
        setConfirmModalOpen(true);
    };

    const executeDelete = async () => {
        if (!itemToDelete) return;

        const { caseId, docId } = itemToDelete;

        // Optimistic UI update
        const originalDocs = [...finalizedDocs];
        const doc = originalDocs.find(d => d.id === docId);
        if (!doc) return;

        const newDomains = doc.domains.map(domainGroup => ({
            ...domainGroup,
            test_cases: domainGroup.test_cases.filter(tc => tc.test_case_id !== caseId),
        })).filter(domainGroup => domainGroup.test_cases.length > 0);

        const updatedDoc = { ...doc, domains: newDomains };

        setFinalizedDocs(prevDocs => {
            if (updatedDoc.domains.length === 0) {
                return prevDocs.filter(d => d.id !== docId);
            } else {
                return prevDocs.map(d => d.id === docId ? updatedDoc : d);
            }
        });

        try {
            const token = await auth.currentUser.getIdToken();
            const response = await fetch(`${BACKEND_URL}/api/test-cases/${docId}/${caseId}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` },
            });

            if (!response.ok) {
                // Revert UI on failure
                setFinalizedDocs(originalDocs);
                const errorData = await response.json();
                toast.error(errorData.detail || 'Failed to delete test case.');
            } else {
                toast.success('Test case deleted successfully.');
            }
        } catch (error) {
            // Revert UI on failure
            setFinalizedDocs(originalDocs);
            toast.error(`Error: ${error.message}`);
        } finally {
            setConfirmModalOpen(false);
            setItemToDelete(null);
        }
    };

    const toggleDomain = (identifier) => {
        const newOpenDomains = new Set(openDomains);
        if (newOpenDomains.has(identifier)) newOpenDomains.delete(identifier); else newOpenDomains.add(identifier);
        setOpenDomains(newOpenDomains);
    };

    const toggleRow = (testCaseId) => {
        const newExpandedRows = new Set(expandedRows);
        if (newExpandedRows.has(testCaseId)) {
            newExpandedRows.delete(testCaseId);
        } else {
            newExpandedRows.add(testCaseId);
        }
        setExpandedRows(newExpandedRows);
    };

    // --- Memoized Filtering ---
    const filteredDomainGroups = useMemo(() => {
        let allTestCases = [];

        finalizedDocs.forEach(doc => {
            doc.domains.forEach(domainGroup => {
                domainGroup.test_cases.forEach(testCase => {
                    allTestCases.push({
                        ...testCase,
                        product_name: doc.product_name,
                        domain: domainGroup.domain || 'Default',
                        docId: doc.id,
                        requirement: doc.requirement
                    });
                });
            });
        });

        // Filter by selected product first
        let casesToProcess = allTestCases;
        if (selectedProduct) {
            casesToProcess = allTestCases.filter(tc => tc.product_name === selectedProduct);
        }

        // Apply search query filtering
        let filteredCases = casesToProcess;
        if (searchQuery) {
            const lowercasedQuery = searchQuery.toLowerCase();
            filteredCases = casesToProcess.filter(tc =>
                tc.title.toLowerCase().includes(lowercasedQuery) ||
                tc.test_case_id.toLowerCase().includes(lowercasedQuery) ||
                (tc.traceability_id && tc.traceability_id.toLowerCase().includes(lowercasedQuery)) ||
                tc.compliance_tag.toLowerCase().includes(lowercasedQuery) ||
                tc.product_name.toLowerCase().includes(lowercasedQuery) ||
                tc.domain.toLowerCase().includes(lowercasedQuery)
            );
        }

        // Group by domain
        const groupedByDomain = filteredCases.reduce((acc, testCase) => {
            const domainName = testCase.domain || 'General';
            if (!acc[domainName]) {
                acc[domainName] = { domain: domainName, test_cases: [] };
            }
            acc[domainName].test_cases.push(testCase);
            return acc;
        }, {});

        return Object.values(groupedByDomain).sort((a, b) => a.domain.localeCompare(b.domain));
    }, [searchQuery, finalizedDocs, selectedProduct]);

    const groupedByProductAndDomain = useMemo(() => {
        if (!selectedProduct) return []; // Only group by product if a product is selected

        const casesForSelectedProduct = finalizedDocs.filter(doc => doc.product_name === selectedProduct)
            .flatMap(doc => doc.domains.flatMap(domainGroup => domainGroup.test_cases.map(testCase => ({
                ...testCase,
                product_name: doc.product_name,
                domain: domainGroup.domain || 'Default',
                docId: doc.id,
                requirement: doc.requirement
            }))));

        let filteredCases = casesForSelectedProduct;
        if (searchQuery) {
            const lowercasedQuery = searchQuery.toLowerCase();
            filteredCases = casesForSelectedProduct.filter(tc =>
                tc.title.toLowerCase().includes(lowercasedQuery) ||
                tc.test_case_id.toLowerCase().includes(lowercasedQuery) ||
                tc.compliance_tag.toLowerCase().includes(lowercasedQuery) ||
                tc.product_name.toLowerCase().includes(lowercasedQuery) ||
                tc.domain.toLowerCase().includes(lowercasedQuery)
            );
        }

        const groupedByDomain = filteredCases.reduce((acc, testCase) => {
            const domainName = testCase.domain || 'General';
            if (!acc[domainName]) {
                acc[domainName] = { domain: domainName, test_cases: [] };
            }
            acc[domainName].test_cases.push(testCase);
            return acc;
        }, {});

        return Object.values(groupedByDomain).sort((a, b) => a.domain.localeCompare(b.domain));
    }, [searchQuery, finalizedDocs, selectedProduct]);

    const uniqueProducts = useMemo(() => {
        const products = new Set();
        finalizedDocs.forEach(doc => products.add(doc.product_name));
        return Array.from(products).sort();
    }, [finalizedDocs]);

    return (
        <div className={`flex h-screen bg-gray-100 dark:bg-gray-900`}>
            <Sidebar isMobileOpen={isMobileSidebarOpen} setMobileOpen={setMobileSidebarOpen} isPinned={isSidebarPinned} uniqueProducts={uniqueProducts} selectedProduct={selectedProduct} setSelectedProduct={setSelectedProduct} isLoadingCases={isLoadingCases} currentPage={currentPage} setCurrentPage={setCurrentPage} isAdmin={isAdmin} />
            <div className={`flex-1 flex flex-col transition-all duration-300`}>
                <Header setMobileSidebarOpen={setMobileSidebarOpen} setSidebarPinned={setSidebarPinned} isSidebarPinned={isSidebarPinned} setAiModalOpen={setAiModalOpen} setCreateModalOpen={setCreateModalOpen} user={user} searchQuery={searchQuery} setSearchQuery={setSearchQuery} />
                <main className="flex-1 p-6 overflow-y-auto">
                    {currentPage === 'knowledgebase' ? (
                        <KnowledgeBasePage />
                    ) : currentPage === 'reporting' ? (
                        <ReportingPage />
                    ) : currentPage === 'admin' && isAdmin ? (
                        adminVerified ? (
                            <AdminPage setCurrentPage={setCurrentPage} setPrefilledFilters={setPrefilledFilters} />
                        ) : (
                            <div className="flex items-center justify-center h-full">
                                <div className="text-center">
                                    <div className="animate-spin h-8 w-8 text-gray-500 mx-auto mb-4">
                                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                        </svg>
                                    </div>
                                    <p className="text-gray-600 dark:text-gray-400">Verifying admin access...</p>
                                </div>
                            </div>
                        )
                    ) : currentPage === 'admin-reporting' && isAdmin ? (
                        adminVerified ? (
                            <AdminReportingPage prefilledFilters={prefilledFilters} />
                        ) : (
                            <div className="flex items-center justify-center h-full">
                                <div className="text-center">
                                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto mb-4"></div>
                                    <p className="text-gray-600 dark:text-gray-400">Verifying admin access...</p>
                                </div>
                            </div>
                        )
                    ) : currentPage === 'fine-tuning' && isAdmin ? (
                        adminVerified ? (
                            <FineTuningPage />
                        ) : (
                            <div className="flex items-center justify-center h-full">
                                <div className="text-center">
                                    <div className="animate-spin h-8 w-8 text-gray-500 mx-auto mb-4">
                                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                        </svg>
                                    </div>
                                    <p className="text-gray-600 dark:text-gray-400">Verifying admin access...</p>
                                </div>
                            </div>
                        )
                    ) : currentPage === 'settings' ? (
                        <SettingsPage />
                    ) : (
                        <>
                            {isLoadingCases ? (
                                <div className="text-center py-20">
                                    <svg className="animate-spin h-8 w-8 text-gray-500 dark:text-gray-400 mx-auto" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                    </svg>
                                    <h3 className="mt-2 text-2xl font-semibold text-gray-700 dark:text-gray-300">Loading test cases...</h3>
                                    <p className="mt-2 text-gray-500 dark:text-gray-400">Please wait while we fetch your data.</p>
                                </div>
                            ) : finalizedDocs.length > 0 && (selectedProduct ? groupedByProductAndDomain.length > 0 : filteredDomainGroups.length > 0) ? (
                                <div className='space-y-6'>
                                    {(selectedProduct ? groupedByProductAndDomain : filteredDomainGroups).map(domainGroup => (
                                        <div key={domainGroup.domain} className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-2xl shadow-sm">
                                            <button onClick={() => toggleDomain(domainGroup.domain)} className='w-full flex justify-between items-center p-5 text-left'>
                                                <span className='text-lg font-semibold text-gray-900 dark:text-gray-100'>{domainGroup.domain} <span className='text-base font-normal text-gray-500 dark:text-gray-400'>({domainGroup.test_cases.length} cases)</span></span>
                                                <ChevronDownIcon className={`w-5 h-5 transform transition-transform text-gray-500 dark:text-gray-400 ${openDomains.has(domainGroup.domain) ? 'rotate-180' : ''}`} />
                                            </button>
                                            {openDomains.has(domainGroup.domain) && (
                                                <div className='p-5 border-t border-gray-200 dark:border-gray-700'>
                                                    <TestCaseTable 
                                                        testCases={domainGroup.test_cases} 
                                                        handleDelete={(caseId, docId) => handleDeleteTestCase(caseId, docId)}
                                                        expandedRows={expandedRows}
                                                        toggleRow={toggleRow}
                                                        copiedId={copiedId}
                                                        handleCopy={handleCopy}
                                                        handleCreateALMIssue={handleCreateALMIssue}
                                                        requirement={domainGroup.test_cases[0].requirement} getAuthToken={() => auth.currentUser.getIdToken()}                                                    
                                                        backendUrl={BACKEND_URL}
                                                    />
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            ) : finalizedDocs.length > 0 && searchQuery ? (
                                <EmptyState 
                                    icon={<SearchIcon />} 
                                    title="No results found" 
                                    message={`Your search for "${searchQuery}" did not match any test cases.`} 
                                />
                            ) : (
                                <EmptyState 
                                    icon={<EmptyStateIcon />} 
                                    title="No test cases finalized yet" 
                                    message="Click 'Generate with AI' or 'Create Test Case' to start."
                                />
                            )}
                        </>
                    )}
                </main>
            </div>

            {isAiModalOpen && <AiModal 
                isOpen={isAiModalOpen} 
                onClose={() => setAiModalOpen(false)} 
                onFinalize={handleFinalize} 
                getAuthToken={() => auth.currentUser.getIdToken()} 
            />}
            {isCreateModalOpen && <CreateTestCaseModal 
                isOpen={isCreateModalOpen} 
                onClose={() => setCreateModalOpen(false)} 
                onSave={handleSaveManually} 
            />}
            {isConfirmModalOpen && <ConfirmationModal
                isOpen={isConfirmModalOpen}
                onClose={() => setConfirmModalOpen(false)}
                {...confirmModalProps}
            />}
            <LoginModal isOpen={isLoginModalOpen} />
        </div>
    )
}

export default AppPage;
