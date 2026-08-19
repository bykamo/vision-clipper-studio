import React from 'react';
import { SimpleClipperDashboard } from './components/SimpleClipperDashboard';

export default function App() {
  return (
    <div className="min-h-screen bg-[#09090b] text-neutral-100 antialiased selection:bg-amber-500 selection:text-black">
      <SimpleClipperDashboard />
    </div>
  );
}
