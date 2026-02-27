import React from 'react';
import { RouterProvider } from 'react-router-dom';
import { router } from './router.tsx';
import Toaster from '../components/ui/Toaster.tsx';

function App() {
  return (
    <div className="App">
      <RouterProvider router={router} />
      <Toaster />
    </div>
  );
}

export default App;
