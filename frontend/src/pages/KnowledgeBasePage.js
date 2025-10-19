import React, { useState, useEffect } from 'react';

const KnowledgeBasePage = () => {
    const [documents, setDocuments] = useState([]);
    const [isLoading, setIsLoading] = useState(true);

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

    return (
        <div className="p-6 bg-gray-100 dark:bg-gray-900 text-gray-900 dark:text-gray-100">
            <h1 className="text-2xl font-bold mb-4">Knowledge Base</h1>

            <div className="mb-4">
                <label className="bg-cyan-600 text-white px-4 py-2 rounded-lg hover:bg-cyan-700 cursor-pointer">
                    Browse Files
                    <input type="file" onChange={handleFileUpload} className="hidden" />
                </label>
            </div>

            {isLoading ? (
                <p>Loading documents...</p>
            ) : (
                <ul className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-2xl shadow-sm">
                    {documents.map(doc => (
                        <li key={doc.id} className="flex justify-between items-center p-4 border-b dark:border-gray-700">
                            <span>{doc.filename}</span>
                            <button onClick={() => handleDelete(doc.id)} className="text-red-500 hover:text-red-700">Delete</button>
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
};

export default KnowledgeBasePage;
