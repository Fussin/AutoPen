import React, { useState, useEffect } from 'react';

const ScanResults = ({ scanId }) => {
    const [results, setResults] = useState([]);
    const [status, setStatus] = useState('Loading...');
    const [error, setError] = useState(null);

    useEffect(() => {
        if (!scanId) return;

        const fetchResults = async () => {
            try {
                const response = await fetch(`/api/v1/scans/${scanId}/results`);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const data = await response.json();
                setResults(data.assets || []);
                setStatus('Completed');
            } catch (e) {
                setError(e.message);
                setStatus('Error');
            }
        };

        fetchResults();
    }, [scanId]);

    const renderStatus = () => {
        if (status === 'Error') {
            return <p className="text-center p-6 text-red-400 animate-pulse">Error fetching results: {error}</p>;
        }
        return (
            <div className="text-center p-6 text-slate-500">
                <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-r-transparent align-[-0.125em] text-neon-cyan motion-reduce:animate-[spin_1.5s_linear_infinite]" role="status">
                    <span className="!absolute !-m-px !h-px !w-px !overflow-hidden !whitespace-nowrap !border-0 !p-0 ![clip:rect(0,0,0,0)]">Loading...</span>
                </div>
                <p className="mt-4">{status}...</p>
            </div>
        );
    };

    return (
        <div className="border border-neon-cyan/30 bg-slate-900/50 rounded-lg shadow-lg shadow-neon-cyan/10 backdrop-blur-sm">
            <div className="p-4 sm:p-6 border-b border-neon-cyan/20">
                <h2 className="text-2xl font-bold text-neon-cyan">Scan Results</h2>
                <p className="text-slate-400 text-sm">Target ID: {scanId}</p>
            </div>

            <div className="overflow-x-auto">
                <table className="w-full text-left">
                    <thead className="text-slate-400 uppercase text-xs">
                        <tr>
                            <th className="p-3 sm:p-4">Asset Type</th>
                            <th className="p-3 sm:p-4">Value</th>
                            <th className="p-3 sm:p-4">First Seen</th>
                        </tr>
                    </thead>
                    <tbody>
                        {results.length > 0 ? (
                            results.map(asset => (
                                <tr key={asset.id} className="border-t border-slate-800 hover:bg-neon-cyan/5 transition-colors duration-300">
                                    <td className="p-3 sm:p-4 font-medium capitalize">{asset.type.replace('_', ' ')}</td>
                                    <td className="p-3 sm:p-4 font-mono text-neon-cyan">{asset.value}</td>
                                    <td className="p-3 sm:p-4 text-slate-500">{new Date(asset.first_seen).toLocaleString()}</td>
                                </tr>
                            ))
                        ) : (
                            <tr>
                                <td colSpan="3">{renderStatus()}</td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default ScanResults;
