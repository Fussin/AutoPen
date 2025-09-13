import React from 'react';
import ScanResults from './components/ScanResults';

function App() {
  return (
    <div className="bg-slate-900 text-white min-h-screen p-8">
      <h1 className="text-4xl font-bold text-cyan-400 tracking-wider mb-10">CyberHunter 3D</h1>
      <ScanResults scanId={1} />
    </div>
  );
}

export default App;
