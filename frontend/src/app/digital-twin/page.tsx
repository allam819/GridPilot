'use client';

import { useState, useEffect } from 'react';
import { Play, Activity, Database, History, Trash2, ChevronRight } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import Link from 'next/link';

interface Asset {
  id: number;
  name: string;
  power_capacity_mw: number;
  energy_capacity_mwh: number;
}

interface SimHistory {
  id: number;
  task_id: string;
  created_at: string;
  baseline_config: any;
  target_config: any;
  comparative_analysis: any;
}

export default function DigitalTwinSimulator() {
  const [status, setStatus] = useState<'IDLE' | 'PENDING' | 'SUCCESS' | 'FAILURE'>('IDLE');
  const [results, setResults] = useState<any | null>(null);
  const { token, logout } = useAuth();
  
  const [assets, setAssets] = useState<Asset[]>([]);
  const [loadingAssets, setLoadingAssets] = useState(true);
  
  const [history, setHistory] = useState<SimHistory[]>([]);
  
  // Baseline State
  const [selectedAssetId, setSelectedAssetId] = useState<string>('');
  
  // Target Form State
  const [targetPower, setTargetPower] = useState(10.0);
  const [targetEnergy, setTargetEnergy] = useState(20.0);
  
  // Financials
  const [capex, setCapex] = useState(250000.0); // $250k per MWh

  const fetchHistory = async () => {
    if (!token) return;
    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const res = await fetch(`${API_URL}/api/v1/simulate/history`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setHistory(data);
      }
    } catch (err) {
      console.error("Failed to fetch history:", err);
    }
  };

  const startPolling = (taskId: string) => {
    setStatus('PENDING');
    const poll = setInterval(async () => {
      try {
        const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const pollRes = await fetch(`${API_URL}/api/v1/simulate/tasks/${taskId}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (pollRes.status === 401) { 
          clearInterval(poll); 
          logout(); 
          return; 
        }
        
        const pollData = await pollRes.json();
        if (pollData.status === 'SUCCESS') {
          setStatus('SUCCESS');
          setResults(pollData);
          clearInterval(poll);
          localStorage.removeItem('dt_taskId');
          // Refresh history after a successful run is saved to DB
          fetchHistory();
        } else if (pollData.status === 'FAILURE') {
          setStatus('FAILURE');
          clearInterval(poll);
          localStorage.removeItem('dt_taskId');
        }
      } catch (err) {
        console.error("Polling error:", err);
      }
    }, 2000);
  };

  // Resume polling and load history on mount
  useEffect(() => {
    if (token) {
      fetchHistory();
      const savedTaskId = localStorage.getItem('dt_taskId');
      if (savedTaskId) {
        startPolling(savedTaskId);
      }
    }
  }, [token]);

  useEffect(() => {
    const fetchAssets = async () => {
      if (!token) return;
      try {
        const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const res = await fetch(`${API_URL}/api/v1/assets`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.status === 401) { logout(); return; }
        const data = await res.json();
        setAssets(data);
        if (data.length > 0) {
          setSelectedAssetId(data[0].id.toString());
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoadingAssets(false);
      }
    };
    fetchAssets();
  }, [token, logout]);

  const runSimulation = async () => {
    if (!selectedAssetId) return;
    const baselineAsset = assets.find(a => a.id.toString() === selectedAssetId);
    if (!baselineAsset) return;

    setStatus('PENDING');
    setResults(null);
    
    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const res = await fetch(`${API_URL}/api/v1/simulate/digital-twin`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          baseline_config: {
            name: baselineAsset.name,
            power_capacity_mw: baselineAsset.power_capacity_mw,
            energy_capacity_mwh: baselineAsset.energy_capacity_mwh
          },
          target_config: {
            name: "Target Upgrade",
            power_capacity_mw: targetPower,
            energy_capacity_mwh: targetEnergy
          },
          capex_per_mwh: capex
        })
      });

      if (res.status === 401) { logout(); return; }
      if (!res.ok) throw new Error('Failed to dispatch simulation');
      const data = await res.json();
      const taskId = data.task_id;
      
      localStorage.setItem('dt_taskId', taskId);
      startPolling(taskId);

    } catch (err) {
      console.error(err);
      setStatus('FAILURE');
    }
  };

  const loadHistoricalRun = (sim: SimHistory) => {
    setStatus('SUCCESS');
    setResults({
      baseline_config: sim.baseline_config,
      target_config: sim.target_config,
      comparative_analysis: sim.comparative_analysis
    });
  };

  const deleteHistoricalRun = async (id: number) => {
    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const res = await fetch(`${API_URL}/api/v1/simulate/history/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        setHistory(prev => prev.filter(h => h.id !== id));
      }
    } catch (err) {
      console.error("Failed to delete", err);
    }
  };

  const isLoading = status === 'PENDING';
  const hasNoAssets = !loadingAssets && assets.length === 0;

  return (
    <main className="min-h-screen bg-gray-950 text-white p-8 font-sans flex gap-8">
      
      {/* Main Content Area */}
      <div className="flex-1 space-y-8 max-w-5xl">
        <header className="border-b border-gray-800 pb-4">
          <h1 className="text-4xl font-light text-emerald-400">Digital Twin <span className="font-bold">Simulator</span></h1>
          <p className="text-gray-400 mt-2">What-if scenario modeling for hardware upgrades</p>
        </header>

        <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
          
          {/* Inputs */}
          <div className="space-y-6 bg-gray-900 border border-gray-800 p-6 rounded-xl relative h-fit">
            
            {hasNoAssets && (
              <div className="absolute inset-0 z-10 bg-gray-900/90 backdrop-blur-sm rounded-xl flex flex-col items-center justify-center p-8 text-center border border-gray-700">
                <Database size={48} className="text-gray-500 mb-4" />
                <h3 className="text-xl font-bold text-gray-200 mb-2">No Assets Found</h3>
                <p className="text-gray-400 mb-6">
                  You need to provision at least one battery asset in your portfolio before running a digital twin simulation.
                </p>
                <Link href="/assets" className="bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-3 px-6 rounded-lg transition">
                  Create an Asset
                </Link>
              </div>
            )}

            <h2 className="text-xl font-bold flex items-center gap-2 text-gray-200">
              <Activity size={20} /> Configuration
            </h2>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-4">
                <h3 className="font-semibold text-gray-400">Baseline System</h3>
                <div>
                  <label className="block text-sm mb-1 text-gray-500">Select Asset</label>
                  <select 
                    value={selectedAssetId} 
                    onChange={e => setSelectedAssetId(e.target.value)}
                    className="w-full bg-gray-950 border border-gray-700 rounded p-2 text-white focus:outline-none focus:border-emerald-500"
                    disabled={hasNoAssets || isLoading}
                  >
                    {assets.map(a => (
                      <option key={a.id} value={a.id}>{a.name} ({a.power_capacity_mw}MW / {a.energy_capacity_mwh}MWh)</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="space-y-4">
                <h3 className="font-semibold text-gray-400">Target System Upgrade</h3>
                <div>
                  <label className="block text-sm mb-1 text-gray-500">Power (MW)</label>
                  <input type="number" value={targetPower} onChange={e => setTargetPower(Number(e.target.value))} className="w-full bg-gray-950 border border-gray-700 rounded p-2" disabled={hasNoAssets || isLoading} />
                </div>
                <div>
                  <label className="block text-sm mb-1 text-gray-500">Energy (MWh)</label>
                  <input type="number" value={targetEnergy} onChange={e => setTargetEnergy(Number(e.target.value))} className="w-full bg-gray-950 border border-gray-700 rounded p-2" disabled={hasNoAssets || isLoading} />
                </div>
              </div>
            </div>

            <div className="pt-4 border-t border-gray-800">
              <label className="block text-sm mb-1 text-gray-500">Estimated CapEx per MWh ($)</label>
              <input type="number" value={capex} onChange={e => setCapex(Number(e.target.value))} className="w-full bg-gray-950 border border-gray-700 rounded p-2" disabled={hasNoAssets || isLoading} />
            </div>

            <button 
              onClick={runSimulation}
              disabled={isLoading || hasNoAssets}
              className="w-full bg-blue-600 hover:bg-blue-500 text-white px-6 py-3 rounded-lg flex items-center justify-center gap-2 font-bold transition disabled:opacity-50"
            >
              {isLoading ? <span className="animate-spin text-xl">⟳</span> : <Play size={18} />}
              {isLoading ? 'Simulating Dual MPC Engines...' : 'Run Comparative Analysis'}
            </button>
          </div>

          {/* Results Display */}
          <div className="bg-gray-900 border border-gray-800 p-6 rounded-xl flex flex-col justify-center h-fit min-h-[300px]">
            {status === 'IDLE' && (
              <div className="text-center text-gray-500">
                Run the simulation or load a past run from history.
              </div>
            )}
            
            {status === 'PENDING' && (
              <div className="text-center space-y-4">
                <div className="animate-pulse text-4xl text-blue-500">⟳</div>
                <p className="text-gray-400">Solving mathematical models on background Celery workers...</p>
                <p className="text-sm text-gray-500 mt-2">Feel free to navigate to other pages. This simulation will continue running in the background!</p>
              </div>
            )}
            
            {status === 'SUCCESS' && results && (
              <div className="space-y-6">
                <h3 className="text-2xl font-bold text-gray-200 border-b border-gray-800 pb-2">Financial Outcomes</h3>
                
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div className="bg-gray-950 p-4 rounded border border-gray-800">
                    <p className="text-gray-500 mb-1">Baseline Profit</p>
                    <p className="text-xl font-bold text-gray-300">
                      ${results.baseline_config.profit.toLocaleString(undefined, {maximumFractionDigits: 0})}
                    </p>
                    {results.baseline_config.power_capacity_mw && (
                      <p className="text-xs text-gray-500 mt-2 border-t border-gray-800 pt-2">
                        {results.baseline_config.name || 'System'}: {results.baseline_config.power_capacity_mw}MW / {results.baseline_config.energy_capacity_mwh}MWh
                      </p>
                    )}
                  </div>
                  <div className="bg-gray-950 p-4 rounded border border-gray-800">
                    <p className="text-gray-500 mb-1">Target Profit</p>
                    <p className="text-xl font-bold text-emerald-400">
                      ${results.target_config.profit.toLocaleString(undefined, {maximumFractionDigits: 0})}
                    </p>
                    {results.target_config.power_capacity_mw && (
                      <p className="text-xs text-gray-500 mt-2 border-t border-gray-800 pt-2">
                        {results.target_config.name || 'Upgrade'}: {results.target_config.power_capacity_mw}MW / {results.target_config.energy_capacity_mwh}MWh
                      </p>
                    )}
                  </div>
                </div>

                <div className="bg-gray-950 border border-gray-800 p-6 rounded-lg space-y-4">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-400">Incremental Annual Profit</span>
                    <div className="text-right">
                      <span className="text-xl font-bold text-emerald-400 block">
                        +${results.comparative_analysis.annualized_incremental_profit.toLocaleString(undefined, {maximumFractionDigits: 0})}
                      </span>
                      <span className="text-xs text-gray-500">
                        (30-day difference: +${results.comparative_analysis.incremental_simulated_profit.toLocaleString(undefined, {maximumFractionDigits: 0})} × 365/30 days)
                      </span>
                    </div>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-400">Total Capital Expenditure</span>
                    <div className="text-right">
                      <span className="text-xl font-bold text-red-400 block">
                        -${results.comparative_analysis.total_capex.toLocaleString(undefined, {maximumFractionDigits: 0})}
                      </span>
                      <span className="text-xs text-gray-500">
                        ({results.comparative_analysis.added_capacity_mwh} MWh added × ${capex.toLocaleString()}/MWh)
                      </span>
                    </div>
                  </div>
                  <div className="flex justify-between items-center pt-4 border-t border-gray-800">
                    <span className="text-gray-300 font-medium">CapEx Payback Period</span>
                    <span className="text-4xl font-extrabold text-emerald-600">
                      {results.comparative_analysis.payback_period_years.toFixed(1)} <span className="text-xl">Years</span>
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>

        </div>
      </div>

      {/* Sidebar: Simulation History */}
      <div className="w-80 bg-gray-900 border border-gray-800 rounded-xl p-4 flex flex-col h-[calc(100vh-4rem)] sticky top-8">
        <h2 className="text-lg font-bold flex items-center gap-2 text-gray-200 border-b border-gray-800 pb-3 mb-4">
          <History size={18} /> Simulation History
        </h2>
        
        <div className="flex-1 overflow-y-auto space-y-3 pr-2 custom-scrollbar">
          {history.length === 0 ? (
            <div className="text-sm text-gray-500 text-center py-8">
              No previous simulations found.
            </div>
          ) : (
            history.map(sim => {
              // Append 'Z' so the browser parses the naive ISO string as UTC and converts it to Local Time
              const dateObj = new Date(sim.created_at + (sim.created_at.endsWith('Z') ? '' : 'Z'));
              const dateStr = dateObj.toLocaleDateString();
              const timeStr = dateObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
              const addedMwh = sim.comparative_analysis.added_capacity_mwh;
              
              // Safely extract optional fields (they might be missing in older records)
              const b_power = sim.baseline_config.power_capacity_mw;
              const b_energy = sim.baseline_config.energy_capacity_mwh;
              const t_power = sim.target_config.power_capacity_mw;
              const t_energy = sim.target_config.energy_capacity_mwh;
              const capex = sim.comparative_analysis.capex_per_mwh;
              
              return (
                <div key={sim.id} className="bg-gray-950 border border-gray-800 rounded p-3 group hover:border-emerald-500/50 transition relative">
                  <div 
                    className="cursor-pointer pr-8"
                    onClick={() => loadHistoricalRun(sim)}
                  >
                    <div className="flex justify-between items-start mb-2 border-b border-gray-800 pb-2">
                      <span className="text-xs font-mono text-gray-400">{dateStr} {timeStr}</span>
                      <span className="text-xs font-bold text-emerald-500">+{addedMwh}MWh</span>
                    </div>
                    
                    <div className="space-y-1.5 mb-2">
                      <div className="text-xs text-gray-300">
                        <span className="text-gray-500 font-semibold">Baseline:</span> {sim.baseline_config.name || 'System'}
                        {b_power && b_energy ? ` (${b_power}MW / ${b_energy}MWh)` : ''}
                      </div>
                      <div className="text-xs text-gray-300">
                        <span className="text-gray-500 font-semibold">Target:</span> {sim.target_config.name || 'Upgrade'}
                        {t_power && t_energy ? ` (${t_power}MW / ${t_energy}MWh)` : ''}
                      </div>
                      {capex && (
                        <div className="text-xs text-gray-400 italic">
                          CapEx: ${capex.toLocaleString()}/MWh
                        </div>
                      )}
                    </div>
                    
                    <div className="text-xs text-gray-400 bg-gray-900 rounded p-1.5 border border-gray-800 inline-block">
                      Payback: <span className="font-bold text-emerald-400">{sim.comparative_analysis.payback_period_years.toFixed(1)} yrs</span>
                    </div>
                  </div>
                  
                  <button 
                    onClick={(e) => { e.stopPropagation(); deleteHistoricalRun(sim.id); }}
                    className="absolute right-2 top-2 p-1.5 text-gray-600 hover:text-red-400 hover:bg-gray-900 rounded opacity-0 group-hover:opacity-100 transition"
                    title="Delete historical run"
                  >
                    <Trash2 size={14} />
                  </button>
                  
                  <div className="absolute right-2 bottom-2 text-gray-600 opacity-0 group-hover:opacity-100 pointer-events-none">
                    <ChevronRight size={14} />
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
      
    </main>
  );
}
