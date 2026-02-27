import { createBrowserRouter, Navigate } from 'react-router-dom';
import Analysis from '../pages/Analysis.tsx';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Navigate to="/analysis" replace />,
  },
  {
    path: '/dashboard',
    element: <Navigate to="/analysis" replace />,
  },
  {
    path: '/analysis',
    element: <Analysis />,
  },
  {
    path: '/history',
    element: <Navigate to="/analysis" replace />,
  },
]);
