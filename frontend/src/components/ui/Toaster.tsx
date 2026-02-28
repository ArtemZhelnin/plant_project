import React from 'react';

interface ToastProps {
  message: string;
  type: 'success' | 'error' | 'info';
}

const Toaster: React.FC = () => {
  return <div id="toast-container" />;
};

export const showToast = ({ message, type }: ToastProps) => {
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  
  document.getElementById('toast-container')?.appendChild(toast);
  
  setTimeout(() => {
    toast.remove();
  }, 3000);
};

export default Toaster;
