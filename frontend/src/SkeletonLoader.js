
import React from 'react';

const SkeletonLoader = () => {
  const rows = Array.from({ length: 5 });
  const columns = Array.from({ length: 6 });

  return (
    <div className="mt-12 bg-white dark:bg-slate-800 rounded-lg shadow-lg overflow-x-auto w-full">
      <div className="animate-pulse">
        <table className="min-w-full" data-testid="skeleton-table">
          <thead className="bg-slate-50 dark:bg-slate-700">
            <tr>
              {columns.map((_, i) => (
                <th key={i} className="px-6 py-3">
                  <div className="h-4 bg-slate-200 dark:bg-slate-600 rounded"></div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
            {rows.map((_, i) => (
              <tr key={i}>
                {columns.map((_, j) => (
                  <td key={j} className="px-6 py-4">
                    <div className="h-4 bg-slate-200 dark:bg-slate-600 rounded"></div>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default SkeletonLoader;
