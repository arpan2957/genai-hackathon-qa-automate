
import React from 'react';

const EmptyState = ({ icon, title, message }) => {
    return (
        <div className="text-center py-20">
            <div className="mx-auto h-12 w-12 text-gray-400">{icon}</div>
            <h3 className="mt-2 text-2xl font-semibold text-gray-700 dark:text-gray-300">{title}</h3>
            <p className="mt-2 text-gray-500 dark:text-gray-400">{message}</p>
        </div>
    );
};

export default EmptyState;
