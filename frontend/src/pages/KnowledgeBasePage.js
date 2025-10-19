import React, { useState, useEffect } from 'react';

const KnowledgeBasePage = () => {
    const [documents, setDocuments] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [selectedDocuments, setSelectedDocuments] = useState(new Set());

    useEffect(() => {
        // Fetch documents from the backend
        const fetchDocuments = async () => {
            try {
                // Replace with your actual API call
                const response = await fetch('/api/knowledge-base/documents');
                if (!response.ok) {
                    throw new Error('Failed to fetch documents');
                }
                const data = await response.json();
                setDocuments(data);
            } catch (error) {
                console.error(error);
            } finally {
                setIsLoading(false);
            }
        };

        fetchDocuments();
    }, []);

    const handleFileUpload = async (event) => {
        const file = event.target.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);

        try {
            // Replace with your actual API call
            const response = await fetch('/api/knowledge-base/documents', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                throw new Error('Failed to upload document');
            }

            // Refresh the document list
            const newDoc = await response.json();
            setDocuments([...documents, newDoc]);
        } catch (error) {
            console.error(error);
        }
    };

    const handleDelete = async (documentId) => {
        try {
            // Replace with your actual API call
            const response = await fetch(`/api/knowledge-base/documents/${documentId}`, {
                method: 'DELETE',
            });

            if (!response.ok) {
                throw new Error('Failed to delete document');
            }

            // Refresh the document list
            setDocuments(documents.filter(doc => doc.id !== documentId));
        } catch (error) {
            console.error(error);
        }
    };

    const handleDeleteSelected = async () => {
        const promises = Array.from(selectedDocuments).map(id => handleDelete(id));
        await Promise.all(promises);
        setSelectedDocuments(new Set());
    };

    const handleSelectDocument = (id) => {
        const newSelectedDocuments = new Set(selectedDocuments);
        if (newSelectedDocuments.has(id)) {
            newSelectedDocuments.delete(id);
        } else {
            newSelectedDocuments.add(id);
        }
        setSelectedDocuments(newSelectedDocuments);
    };

    const handleSelectAll = (event) => {
        if (event.target.checked) {
            const newSelectedDocuments = new Set(documents.map(doc => doc.id));
            setSelectedDocuments(newSelectedDocuments);
        } else {
            setSelectedDocuments(new Set());
        }
    };

    return (
        <div className="p-6 bg-gray-100 dark:bg-gray-900 text-gray-900 dark:text-gray-100">
            <div className="flex justify-between items-center mb-4">
                <h1 className="text-2xl font-bold">Knowledge Base</h1>
                <div className="flex items-center space-x-2">
                    {selectedDocuments.size > 0 && (
                        <button onClick={handleDeleteSelected} className="bg-red-500 text-white px-4 py-2 rounded-lg hover:bg-red-700">Delete Selected</button>
                    )}
                    <label className="bg-cyan-600 text-white px-4 py-2 rounded-lg hover:bg-cyan-700 cursor-pointer">
                        Browse Files
                        <input type="file" onChange={handleFileUpload} className="hidden" />
                    </label>
                </div>
            </div>

            {isLoading ? (
                <p>Loading documents...</p>
            ) : (
                <table className="w-full bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-2xl shadow-sm">
                    <thead>
                        <tr className="border-b dark:border-gray-700">
                            <th className="p-4 text-left w-10">
                                <input type="checkbox" onChange={handleSelectAll} checked={selectedDocuments.size === documents.length && documents.length > 0} />
                            </th>
                            <th className="p-4 text-left">Filename</th>
                            <th className="p-4 text-left">Upload Date</th>
                            <th className="p-4 text-right">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {documents.map(doc => (
                            <tr key={doc.id} className="border-b dark:border-gray-700">
                                <td className="p-4">
                                    <input type="checkbox" onChange={() => handleSelectDocument(doc.id)} checked={selectedDocuments.has(doc.id)} />
                                </td>
                                <td className="p-4">{doc.filename}</td>
                                <td className="p-4">{new Date(doc.upload_date).toLocaleDateString()}</td>
                                <td className="p-4 text-right">
                                    <button onClick={() => handleDelete(doc.id)} className="text-red-500 hover:text-red-700">Delete</button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            )}
        </div>
    );
};

export default KnowledgeBasePage;
