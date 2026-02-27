import { createBrowserRouter } from 'react-router-dom';
import Landing from '../pages/Landing';
import Dashboard from '../pages/Dashboard';
import Analysis from '../pages/Analysis';
import History from '../pages/History';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Landing />,
  },
  {
    path: '/dashboard',
    element: <Dashboard />,
  },
  {
    path: '/analysis',
    element: <Analysis />,
  },
  {
    path: '/history',
    element: <History />,
  },
]);
