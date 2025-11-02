import React, { useState, useEffect } from 'react';
import { UploadIcon, DownloadIcon, ChevronDownIcon } from './icons';
import TestCaseTable from './TestCaseTable';
import SkeletonLoader from '../SkeletonLoader';
import { auth } from '../firebase';
import toast from 'react-hot-toast';
import { config } from '../config';

const BACKEND_URL = config.BACKEND_URL;

const AiModal = ({ isOpen, onClose, onFinalize, getAuthToken }) => {
    const [isLoading, setIsLoading] = useState(false);
    const [generatedResult, setGeneratedResult] = useState(null); // Will store { product_name, domains: [...] }
    const [expandedRows, setExpandedRows] = useState(new Set());
    const [openDomains, setOpenDomains] = useState(new Set());
    const [copiedId, setCopiedId] = useState(null);
    const [requirement, setRequirement] = useState(() => localStorage.getItem('requirement') || '');
    const [requirementId, setRequirementId] = useState("");
    const [productName, setProductName] = useState("");
    const [selectedFile, setSelectedFile] = useState(null);
    const [refinementPrompt, setRefinementPrompt] = useState("");
    const [imagePreview, setImagePreview] = useState(null);

    useEffect(() => {
        if (!isOpen) {
            setGeneratedResult(null);
            setExpandedRows(new Set());
            setOpenDomains(new Set());
            setIsLoading(false);
            setSelectedFile(null);
            setProductName("");
            setRequirementId("");
            setRefinementPrompt("");
            setImagePreview(null);
        }
    }, [isOpen]);

    useEffect(() => {
        try {
            localStorage.setItem('requirement', requirement);
        } catch (error) {
            console.error("Failed to save requirement to localStorage", error);
        }
    }, [requirement]);

    const handleFileChange = (event) => {
        const file = event.target.files[0];
        if (file) {
            setSelectedFile(file);
            setRequirement(`File selected: ${file.name}`);
            if (file.type.startsWith('image/')) {
                const reader = new FileReader();
                reader.onloadend = () => {
                    setImagePreview(reader.result);
                };
                reader.readAsDataURL(file);
            }
        }
    };

    const handleGenerate = async () => {
        const user = auth.currentUser;
        if (!user) {
            toast.error("You must be logged in to generate test cases.");
            return;
        }

        setIsLoading(true);
        setGeneratedResult(null);

        try {
            const token = await user.getIdToken();
            let requestBody = {};

            if (selectedFile) {
                if (selectedFile.type.startsWith('image/')) {
                    const reader = new FileReader();
                    reader.readAsDataURL(selectedFile);
                    reader.onloadend = async () => {
                        const base64Image = reader.result;
                        requestBody = { 
                            requirement: requirement,
                            image_data: base64Image, 
                            product_name: productName, 
                            requirement_id: requirementId 
                        };
                        await sendGenerateRequest(token, requestBody);
                    };
                } else {
                    const formData = new FormData();
                    formData.append('file', selectedFile);
                    toast.loading("Uploading and parsing document...");
                    const uploadResponse = await fetch(`${BACKEND_URL}/api/upload`, { method: 'POST', headers: { 'Authorization': `Bearer ${token}` }, body: formData });
                    if (!uploadResponse.ok) throw new Error((await uploadResponse.json()).detail || 'Failed to upload file.');
                    const uploadData = await uploadResponse.json();
                    requestBody = { document_text: uploadData.text, product_name: productName, requirement_id: requirementId };
                    await sendGenerateRequest(token, requestBody);
                }
            } else {
                requestBody = { 
                    requirement, 
                    product_name: productName, 
                    requirement_id: requirementId 
                };
                if (refinementPrompt && generatedResult) {
                    const test_cases_for_refinement = generatedResult.domains.flatMap(d => d.test_cases);
                    if (test_cases_for_refinement.length > 0) {
                        requestBody.refinement_prompt = refinementPrompt;
                        requestBody.test_cases = test_cases_for_refinement;
                    }
                }
                await sendGenerateRequest(token, requestBody);
            }

        } catch (err) {
            console.error(err);
            toast.error(`Error: ${err.message}`);
            toast.dismiss();
            setIsLoading(false);
        }
    };

    const sendGenerateRequest = async (token, requestBody) => {
        toast.dismiss();
        toast.loading(refinementPrompt ? "Refining test cases..." : "Generating test cases with AI...");
        const generateResponse = await fetch(`${BACKEND_URL}/api/generate`, { method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` }, body: JSON.stringify(requestBody) });
        if (!generateResponse.ok) throw new Error((await generateResponse.json()).detail || 'An error occurred.');
        
        const data = await generateResponse.json();
        setGeneratedResult(data);
        // Automatically open all domains by default
        setOpenDomains(new Set(data.domains.map(d => d.domain)));

        toast.dismiss();
        toast.success("Test cases generated successfully!");
        setIsLoading(false);
    };

    const handleFinalize = () => {
        onFinalize({ ...generatedResult, requirement });
        onClose();
    };

    const toggleRow = (id) => {
        const newExpandedRows = new Set(expandedRows);
        if (newExpandedRows.has(id)) newExpandedRows.delete(id); else newExpandedRows.add(id);
        setExpandedRows(newExpandedRows);
    };

    const toggleDomain = (domainName) => {
        const newOpenDomains = new Set(openDomains);
        if (newOpenDomains.has(domainName)) newOpenDomains.delete(domainName); else newOpenDomains.add(domainName);
        setOpenDomains(newOpenDomains);
    };

    const handleCopy = (tc) => {
        navigator.clipboard.writeText(JSON.stringify(tc, null, 2)).then(() => {
            setCopiedId(tc.test_case_id);
            toast.success("Copied to clipboard!");
        });
    };

    const handleDownload = (format) => {
        if (!generatedResult || generatedResult.domains.length === 0) {
            toast.error("No test cases to download.");
            return;
        }
        let dataStr = "";
        let mimeType = "";

        if (format === 'json') {
            dataStr = JSON.stringify(generatedResult, null, 2);
            mimeType = "application/json";
        } else if (format === 'xml') {
            let xmlContent = '<?xml version="1.0" encoding="UTF-8"?>\n<testCases>\n';
            xmlContent += `  <productName>${generatedResult.product_name}</productName>\n`;
            generatedResult.domains.forEach(domainGroup => {
                xmlContent += `  <domain name="${domainGroup.domain}">\n`;
                domainGroup.test_cases.forEach(tc => {
                    xmlContent += '    <testCase>\n';
                    xmlContent += `      <testCaseId>${tc.test_case_id}</testCaseId>\n`;
                    xmlContent += `      <title>${tc.title}</title>\n`;
                    xmlContent += `      <type>${tc.type}</type>\n`;
                    xmlContent += `      <priority>${tc.priority}</priority>\n`;
                    xmlContent += '      <steps>\n';
                    if (Array.isArray(tc.steps)) {
                        tc.steps.forEach(step => {
                            xmlContent += '        <step>\n';
                            xmlContent += `          <stepNumber>${step.step}</stepNumber>\n`;
                            xmlContent += `          <action>${step.action}</action>\n`;
                            xmlContent += `          <expectedResult>${step.expected_result}</expectedResult>\n`;
                            xmlContent += '        </step>\n';
                        });
                    } else {
                        xmlContent += `        <action>${tc.steps}</action>\n`;
                    }
                    xmlContent += '      </steps>\n';
                    xmlContent += `      <complianceTag>${tc.compliance_tag}</complianceTag>\n`;
                    xmlContent += '    </testCase>\n';
                });
                xmlContent += '  </domain>\n';
            });
            xmlContent += '</testCases>';
            dataStr = xmlContent;
            mimeType = "application/xml";
        } else if (format === 'md') {
            let mdContent = `# Test Cases for ${generatedResult.product_name}\n\n`;
            generatedResult.domains.forEach(domainGroup => {
                mdContent += `## Domain: ${domainGroup.domain}\n\n`;
                domainGroup.test_cases.forEach(tc => {
                    mdContent += `### ${tc.test_case_id}: ${tc.title}\n\n`;
                    mdContent += `*   **Type:** ${tc.type}\n`;
                    mdContent += `*   **Priority:** ${tc.priority}\n`;
                    mdContent += `*   **Compliance Tag:** ${tc.compliance_tag}\n\n`;
                    mdContent += `**Steps:**\n\n`;
                    if (Array.isArray(tc.steps)) {
                        mdContent += '| Step | Action | Expected Result |\n';
                        mdContent += '|------|--------|-----------------|\n';
                        tc.steps.forEach(step => {
                            mdContent += `| ${step.step} | ${step.action} | ${step.expected_result} |\n`;
                        });
                    } else {
                        mdContent += `${tc.steps}\n`;
                    }
                    mdContent += '\n';
                });
            });
            dataStr = mdContent;
            mimeType = "text/markdown";
        }

        const blob = new Blob([dataStr], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `test-cases-${generatedResult.product_name}.${format}`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        toast.success(`Downloaded as ${format.toUpperCase()}`);
    };

    useEffect(() => {
        if (copiedId) {
            const timer = setTimeout(() => setCopiedId(null), 2000);
            return () => clearTimeout(timer);
        } 
    }, [copiedId]);

    if (!isOpen) return null;

    const isGenerateDisabled = () => {
        if (isLoading) return true;
        if (selectedFile) return false;
        return !requirement || requirement.trim() === '';
    };

    const hasGeneratedContent = generatedResult && generatedResult.domains.length > 0;

    return (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50" data-testid="ai-modal">
            <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-2xl w-full max-w-5xl shadow-2xl flex flex-col max-h-[90vh]">
                <div className="flex items-center justify-between p-5 border-b border-gray-200 dark:border-gray-700">
                    <h3 className="text-lg font-bold text-gray-900 dark:text-white">Generate with AI</h3>
                    <button onClick={onClose} className="text-gray-400 hover:text-gray-800 dark:hover:text-white text-2xl">&times;</button>
                </div>
                
                <div className="flex-1 overflow-y-auto p-6 space-y-4">
                    {!isLoading && !hasGeneratedContent && (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div className="space-y-4">
                                <div>
                                    <label htmlFor="ai-prompt" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Requirement Prompt</label>
                                    <textarea id="ai-prompt" rows="8" className="w-full bg-gray-100 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg p-3 text-sm text-gray-800 dark:text-gray-200 focus:outline-none focus:ring-2 focus:ring-cyan-500" placeholder="Enter a single requirement OR select a file to upload." value={requirement} onChange={(e) => setRequirement(e.target.value)} disabled={!!selectedFile} />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Upload Specification</label>
                                    <label htmlFor="file-upload" className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed rounded-lg cursor-pointer bg-gray-50 dark:bg-gray-800/50 hover:bg-gray-100 dark:hover:bg-gray-700/50">
                                        <UploadIcon />
                                        <p className="text-sm text-gray-500 dark:text-gray-400"><span className="font-semibold text-cyan-600">Click to upload</span> or drag and drop</p>
                                        <p className="text-xs text-gray-500">{selectedFile ? selectedFile.name : 'PDF, DOCX, TXT, PNG, JPG'}</p>
                                        <input id="file-upload" type="file" className="hidden" onChange={handleFileChange} accept=".pdf,.docx,.txt,image/png,image/jpeg" />
                                    </label>
                                    {imagePreview && <img src={imagePreview} alt="Preview" className="mt-4 w-full h-auto rounded-lg" />}
                                    {selectedFile && <button onClick={() => {setSelectedFile(null); setRequirement(''); setImagePreview(null);}} className="text-xs text-red-500 mt-1 hover:underline">Clear selection</button>}
                                </div>
                            </div>
                            <div className="space-y-4">
                                <div>
                                    <label htmlFor="product-name" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Product Name (Optional)</label>
                                    <input id="product-name" type="text" placeholder="e.g., HealthRecord Pro" value={productName} onChange={(e) => setProductName(e.target.value)} className="w-full bg-gray-100 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg p-3 text-sm text-gray-800 dark:text-gray-200" />
                                </div>
                                <div>
                                    <label htmlFor="requirement-id" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Requirement ID (Optional)</label>
                                    <input id="requirement-id" type="text" placeholder="e.g., PROJ-REQ-123" value={requirementId} onChange={(e) => setRequirementId(e.target.value)} className="w-full bg-gray-100 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg p-3 text-sm text-gray-800 dark:text-gray-200" />
                                </div>
                            </div>
                        </div>
                    )}

                    {isLoading && <SkeletonLoader />}
                    
                    {!isLoading && hasGeneratedContent && (
                        <div className='space-y-2'>
                            <h4 className='text-lg font-semibold text-gray-800 dark:text-gray-200'>Generated Test Cases for: <span className='text-cyan-600'>{generatedResult.product_name}</span></h4>
                            {generatedResult.domains.map((domainGroup) => (
                                <div key={domainGroup.domain} className="border border-gray-200 dark:border-gray-700 rounded-lg">
                                    <button onClick={() => toggleDomain(domainGroup.domain)} className='w-full flex justify-between items-center p-4 bg-gray-50 dark:bg-gray-800/50 hover:bg-gray-100 dark:hover:bg-gray-800'>
                                        <span className='font-semibold text-gray-800 dark:text-gray-200'>{domainGroup.domain} ({domainGroup.test_cases.length} cases)</span>
                                        <ChevronDownIcon className={`w-5 h-5 transform transition-transform text-gray-500 dark:text-gray-400 ${openDomains.has(domainGroup.domain) ? 'rotate-180' : ''}`} />
                                    </button>
                                    {openDomains.has(domainGroup.domain) && (
                                        <div className='p-4'>
                                            <TestCaseTable testCases={domainGroup.test_cases} expandedRows={expandedRows} toggleRow={toggleRow} copiedId={copiedId} handleCopy={handleCopy} requirement={requirement} getAuthToken={getAuthToken} backendUrl={BACKEND_URL} />
                                        </div>
                                    )}
                                </div>
                            ))}
                            <div className="pt-4">
                                <label htmlFor="refinement-prompt" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Refinement Prompt (Optional)</label>
                                <textarea id="refinement-prompt" rows="3" className="w-full bg-gray-100 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg p-3 text-sm text-gray-800 dark:text-gray-200 focus:outline-none focus:ring-2 focus:ring-cyan-500" placeholder="e.g., Add more edge cases for the login functionality." value={refinementPrompt} onChange={(e) => setRefinementPrompt(e.target.value)} />
                            </div>
                        </div>
                    )}
                </div>

                <div className="p-5 bg-gray-50 dark:bg-gray-900/80 border-t border-gray-200 dark:border-gray-700 flex justify-end items-center space-x-3 rounded-b-2xl">
                    {hasGeneratedContent && !isLoading && (
                        <div className="group relative">
                            <button className="px-4 py-2 text-sm font-semibold text-white bg-green-600 rounded-lg hover:bg-green-700 flex items-center">
                                <DownloadIcon />
                                <span className="ml-2">Download</span>
                            </button>
                            <div className="absolute bottom-full mb-2 w-32 bg-white dark:bg-gray-800 border dark:border-gray-700 rounded-md shadow-lg opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                                <button type="button" onClick={() => handleDownload('json')} className="block w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer">JSON</button>
                                <button type="button" onClick={() => handleDownload('xml')} className="block w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer">XML</button>
                                <button type="button" onClick={() => handleDownload('md')} className="block w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer">Markdown</button>
                            </div>
                        </div>
                    )}
                    <button onClick={handleGenerate} disabled={isGenerateDisabled()} className="px-5 py-2.5 text-sm font-semibold text-white bg-cyan-600 rounded-lg hover:opacity-90 disabled:bg-slate-400 dark:disabled:bg-slate-600 disabled:cursor-not-allowed">
                        {isLoading ? 'Generating...' : (hasGeneratedContent ? 'Refine' : 'Generate Test Cases')}
                    </button>
                    {hasGeneratedContent && !isLoading && (
                        <button onClick={handleFinalize} className="px-5 py-2.5 text-sm font-semibold text-white bg-blue-600 rounded-lg hover:opacity-90">
                            Finalize
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
};

export default AiModal;
