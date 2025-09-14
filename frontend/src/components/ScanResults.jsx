import React, { useState, useEffect } from 'react';

const ScanResults = ({ scanId }) => {
    const [results, setResults] = useState([]);
    const [status, setStatus] = useState('Loading...');
    const [error, setError] = useState(null);

    useEffect(() => {
        if (!scanId) return;

        // Fetch results from our Flask API
        const fetchResults = async () => {
            try {
                // Note: We use a relative path because Nginx is routing for us.
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

    return (
        <div className="bg-slate-800 p-6 rounded-lg shadow-lg mt-8">
            <h2 className="text-2xl font-bold text-cyan-300 mb-4">Scan Results for ID: {scanId}</h2>

            {status === 'Error' && <p className="text-red-400">Error fetching results: {error}</p>}

            <div className="overflow-x-auto">
                <table className="w-full text-left text-slate-300">
                    <thead className="bg-slate-900 text-slate-400 uppercase text-xs">
                        <tr>
                            <th className="p-3">Asset Type</th>
                            <th className="p-3">Value</th>
                            <th className="p-3">First Seen</th>
                        </tr>
                    </thead>
                    <tbody>
                        {results.length > 0 ? (
                            results.map(asset => (
                                <tr key={asset.id} className="border-b border-slate-700 hover:bg-slate-700/50">
                                    <td className="p-3 font-medium capitalize">{asset.type.replace('_', ' ')}</td>
                                    <td className="p-3 font-mono text-cyan-400">{asset.value}</td>
                                    <td className="p-3">{new Date(asset.first_seen).toLocaleString()}</td>
                                </tr>
                            ))
                        ) : (
                            <tr>
                                <td colSpan="3" className="text-center p-6 text-slate-500">{status}...</td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default ScanResults;
