
import React from 'react';

const ErrorMessage = ({ error }) => {
  if (!error) return null;

  let title = 'An Error Occurred';
  let message = error;

  if (error.includes('AI response was empty or blocked')) {
    title = 'AI Content Safety Block';
    message = 'The AI model blocked the response due to content safety filters. This can happen if the input requirement is too sensitive or violates usage policies. Please try rephrasing your requirement.';
  } else if (error.includes('Failed to parse AI response')) {
    title = 'AI Response Format Error';
    message = 'The AI returned data in an unexpected format. This is often a temporary issue. Please try generating again. If the problem persists, the AI model might be producing an invalid structure.';
  } else if (error.includes('An error occurred while generating test cases')) {
    title = 'Generation Failed';
    message = 'The server could not generate test cases. Please check your network connection and try again. If the issue continues, the backend service may be down.';
  }

  return (
    <div className="mt-8 bg-red-100 dark:bg-red-900/50 border border-red-400 dark:border-red-700 text-red-700 dark:text-red-300 px-4 py-3 rounded-lg">
      <h3 className="font-bold">{title}</h3>
      <p>{message}</p>
    </div>
  );
};

export default ErrorMessage;
