import React from 'react';
import ScanResults from './components/ScanResults';

function App() {
  return (
    <div className="min-h-screen p-4 sm:p-8 bg-slate-900">
      <header className="text-center mb-12">
        <h1
          className="text-5xl sm:text-6xl font-bold text-neon-cyan tracking-widest uppercase"
          style={{ textShadow: '0 0 10px #08F7FE, 0 0 20px #08F7FE' }}
        >
          CyberHunter 3D
        </h1>
        <p className="text-slate-400 mt-2 text-sm sm:text-base">Your Futuristic Reconnaissance Dashboard</p>
      </header>
      <main>
        <ScanResults scanId={1} />
      </main>
    </div>
  );
}

export default App;
