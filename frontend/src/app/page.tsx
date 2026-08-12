'use client';

import { useState, useEffect } from 'react';
import { useBacktestTask } from '@/hooks/useBacktestTask';
import { useAuth } from '@/context/AuthContext';
import { ComposedChart, Area, Line, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import { Play, Battery, DollarSign, TrendingUp, AlertCircle, Activity, ChevronLeft, ChevronRight, Settings } from 'lucide-react';

export default function Dashboard() {
  const { status, metrics, runBacktest } = useBacktestTask();
  const { token } = useAuth();
  const [startDate, setStartDate] = useState('2025-07-01');
  const [endDate, setEndDate] = useState('2025-07-31');
  const [assets, setAssets] = useState<any[]>([]);
  const [selectedAssetIds, setSelectedAssetIds] = useState<number[]>([]);
  const [showAssetSelector, setShowAssetSelector] = useState(false);

  useEffect(() => {
    async function fetchAssets() {
      if (!token) return;
      try {
        const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const res = await fetch(`${API_URL}/api/v1/assets/`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          setAssets(data);
          setSelectedAssetIds([]);
        }
      } catch (err) {
        console.error("Failed to fetch assets", err);
      }
    }
    fetchAssets();
  }, [token]);

  const [activeIndex, setActiveIndex] = useState(0);
  const [viewDayOffset, setViewDayOffset] = useState(0);

  // Reset pagination when new metrics arrive
  useEffect(() => {
    setViewDayOffset(0);
    setActiveIndex(0);
  }, [metrics]);

  const allChartData = metrics?.chart_data || [];
  const maxDays = Math.max(1, Math.ceil(allChartData.length / 96));

  const chartDataToRender = allChartData.length > 0 
    ? allChartData.slice(viewDayOffset * 96, (viewDayOffset + 1) * 96)
    : Array.from({ length: 96 }).map((_, i) => ({
        time: `${Math.floor(i / 4)}:${(i % 4) * 15 === 0 ? '00' : (i % 4) * 15}`,
        price: 0,
        solar: 0,
        dispatch: 0,
        soc: 45.0,
        action: "AWAITING DATA",
        explanation: "Run the optimizer to generate live dispatch recommendations. Hover over the chart below to scrub through time."
      }));

  const activePoint = chartDataToRender[activeIndex] || chartDataToRender[0];
  const isLoading = status === 'PENDING';

  return (
    <main className="min-h-screen bg-gray-950 text-white p-8 font-sans">
      <div className="max-w-7xl mx-auto space-y-8">
        
        <header className="flex justify-between items-end pb-4 border-b border-gray-800">
          <div>
            <h1 className="text-4xl font-light text-emerald-400">GridPilot <span className="font-bold">VPP Aggregator</span></h1>
            <p className="text-gray-400 mt-2">
              Managing Multiple Distributed Energy Assets in Real-time
              {metrics?.["Total Power Capacity (MW)"] && (
                <span className="ml-2 font-bold text-emerald-500">
                  (Simulating {metrics["Total Power Capacity (MW)"]} MW / {metrics["Total Energy Capacity (MWh)"]} MWh Portfolio)
                </span>
              )}
            </p>
          </div>
          <div className="flex gap-4">
            <input 
              type="date" 
              value={startDate} 
              onChange={(e) => setStartDate(e.target.value)}
              className="bg-gray-900 border border-gray-700 rounded px-4 py-2"
            />
            <input 
              type="date" 
              value={endDate} 
              onChange={(e) => setEndDate(e.target.value)}
              className="bg-gray-900 border border-gray-700 rounded px-4 py-2"
            />
            <div className="relative">
              <button 
                onClick={() => setShowAssetSelector(!showAssetSelector)}
                className="bg-gray-900 border border-gray-700 text-gray-300 rounded px-4 py-2 flex items-center gap-2 hover:bg-gray-800 transition"
              >
                <Settings size={16} /> 
                {selectedAssetIds.length} of {assets.length} Selected
              </button>
              
              {showAssetSelector && (
                <div className="absolute right-0 top-12 w-64 bg-gray-900 border border-gray-700 rounded-lg shadow-2xl p-4 z-50">
                  <h4 className="text-sm font-bold text-gray-400 mb-3 border-b border-gray-800 pb-2">Included Assets</h4>
                  <div className="max-h-60 overflow-y-auto flex flex-col gap-2">
                    {assets.map(asset => (
                      <label key={asset.id} className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer">
                        <input 
                          type="checkbox" 
                          className="rounded border-gray-700 text-emerald-500 focus:ring-emerald-500 bg-gray-800"
                          checked={selectedAssetIds.includes(asset.id)}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setSelectedAssetIds([...selectedAssetIds, asset.id]);
                            } else {
                              setSelectedAssetIds(selectedAssetIds.filter(id => id !== asset.id));
                            }
                          }}
                        />
                        {asset.name} <span className="text-gray-600 text-xs">({asset.power_capacity_mw}MW)</span>
                      </label>
                    ))}
                    {assets.length === 0 && <p className="text-xs text-gray-500">No assets provisioned. Go to /assets to create one.</p>}
                  </div>
                </div>
              )}
            </div>

            <button 
              onClick={() => {
                setShowAssetSelector(false);
                runBacktest(startDate, endDate, selectedAssetIds.length > 0 ? selectedAssetIds : undefined);
              }}
              disabled={isLoading || selectedAssetIds.length === 0}
              className="bg-emerald-600 hover:bg-emerald-500 text-white px-6 py-2 rounded flex items-center gap-2 font-medium transition disabled:opacity-50"
            >
              {isLoading ? <span className="animate-spin text-xl">⟳</span> : <Play size={18} />}
              {isLoading ? 'Optimizing...' : 'Run MPC'}
            </button>
          </div>
        </header>

        {/* Explainability Hero */}
        <section className="bg-gradient-to-r from-gray-900 to-gray-800 border border-gray-700 p-8 rounded-xl shadow-2xl relative overflow-hidden">
          <div className="absolute top-0 right-0 w-64 h-64 bg-emerald-500/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />
          <h2 className="text-sm font-bold text-gray-400 uppercase tracking-widest mb-4 flex items-center gap-2">
            <AlertCircle size={16} /> Current Recommendation
          </h2>
          {isLoading ? (
            <div className="animate-pulse flex flex-col gap-4">
              <div className="h-10 bg-gray-700/50 w-1/4 rounded" />
              <div className="h-6 bg-gray-700/50 w-3/4 rounded" />
            </div>
          ) : (
            <div>
              <div className="flex items-center gap-4 mb-2">
                <div className="text-4xl font-bold text-emerald-400">
                  {activePoint.action}
                </div>
                <div className="text-gray-500 font-mono text-xl mt-1">@ {activePoint.time}</div>
              </div>
              <p className="text-xl text-gray-300 mb-6">
                {activePoint.explanation}
              </p>
              
              {selectedAssetIds.length > 0 && (
                <div className="bg-gray-950/50 border border-gray-700/50 rounded-lg p-4">
                  <h3 className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-3 border-b border-gray-800 pb-2">Individual Asset Instructions</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                    {selectedAssetIds.map((id, idx) => {
                      const asset = assets.find(a => a.id === id);
                      const act_mw = activePoint[`asset_${idx}`] || 0;
                      const act_soc = activePoint[`soc_asset_${idx}`] !== undefined 
                        ? activePoint[`soc_asset_${idx}`] 
                        : (asset ? (activePoint.soc || 50) : 0);
                        
                      let actionText = "HOLD (0.0 MW)";
                      if (act_mw > 0) {
                        actionText = `CHARGE (${act_mw.toFixed(1)} MW)`;
                      } else if (act_mw < 0) {
                        actionText = `DISCHARGE (${Math.abs(act_mw).toFixed(1)} MW)`;
                      }
                      
                      return (
                        <div key={idx} className="bg-gray-800/50 rounded border border-gray-700 p-3 flex justify-between items-center">
                          <div className="flex items-center gap-3">
                            <div 
                              className="w-3 h-3 rounded-full" 
                              style={{ backgroundColor: `hsl(${idx * 137 % 360}, 70%, 50%)` }}
                            />
                            <div>
                              <div className="text-sm font-bold text-gray-200">{asset?.name || `Asset ${idx+1}`}</div>
                              <div className="text-xs text-gray-400 font-mono">
                                SOC: <span className="text-gray-200 font-bold">{Number(act_soc).toFixed(1)}%</span> 
                                <span className="text-gray-600 ml-1">({asset ? `${asset.power_capacity_mw}MW / ${asset.energy_capacity_mwh}MWh` : ''})</span>
                              </div>
                            </div>
                          </div>
                          <div className="text-sm font-mono text-emerald-400 bg-gray-900 px-2 py-1 rounded border border-gray-700">
                            {actionText}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          )}
        </section>

        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {[
            { label: 'Total VPP Profit', value: metrics ? `$${metrics['Total Profit ($)']?.toLocaleString(undefined, {maximumFractionDigits:0})}` : '---', icon: DollarSign, color: 'text-emerald-400' },
            { label: 'Energy Arbitrage', value: metrics ? `$${metrics['Energy Revenue ($)']?.toLocaleString(undefined, {maximumFractionDigits:0})}` : '---', icon: TrendingUp, color: 'text-blue-400' },
            { label: 'Ancillary Services', value: metrics ? `$${metrics['Ancillary Revenue ($)']?.toLocaleString(undefined, {maximumFractionDigits:0})}` : '---', icon: Activity, color: 'text-purple-400' },
            { label: 'Aggregate SOC', value: `${activePoint.soc?.toFixed(1)}%`, icon: Battery, color: 'text-amber-400' }
          ].map((kpi, idx) => (
            <div key={idx} className="bg-gray-900 border border-gray-800 p-6 rounded-xl flex items-center gap-4">
              <div className={`p-4 bg-gray-950 rounded-lg ${kpi.color}`}>
                <kpi.icon size={28} />
              </div>
              <div>
                <p className="text-sm text-gray-500 font-medium">{kpi.label}</p>
                <p className={`text-3xl font-bold ${isLoading ? 'animate-pulse text-gray-700' : 'text-white'}`}>
                  {isLoading ? '...' : kpi.value}
                </p>
              </div>
            </div>
          ))}
        </div>

        {/* Schedule Visualizer */}
        <section className="bg-gray-900 border border-gray-800 p-6 rounded-xl h-[450px] flex flex-col">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-lg font-bold text-gray-300">
              24-Hour Optimization Horizon <span className="text-emerald-500 font-mono text-sm ml-2">(Day {viewDayOffset + 1} of {maxDays})</span>
            </h3>
            <div className="flex gap-2">
              <button 
                onClick={() => {
                  setViewDayOffset(d => Math.max(0, d - 1));
                  setActiveIndex(0);
                }}
                disabled={viewDayOffset === 0 || isLoading}
                className="bg-gray-800 hover:bg-gray-700 text-gray-300 px-3 py-1.5 rounded flex items-center gap-1 text-sm disabled:opacity-30 transition"
              >
                <ChevronLeft size={16} /> Prev Day
              </button>
              <button 
                onClick={() => {
                  setViewDayOffset(d => Math.min(maxDays - 1, d + 1));
                  setActiveIndex(0);
                }}
                disabled={viewDayOffset >= maxDays - 1 || isLoading}
                className="bg-gray-800 hover:bg-gray-700 text-gray-300 px-3 py-1.5 rounded flex items-center gap-1 text-sm disabled:opacity-30 transition"
              >
                Next Day <ChevronRight size={16} />
              </button>
            </div>
          </div>

          <div className="flex-1">
            <ResponsiveContainer width="100%" height="100%">
            <ComposedChart 
              data={chartDataToRender} 
              margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
              onMouseMove={(e) => {
                if (e.activeTooltipIndex !== undefined) {
                  setActiveIndex(e.activeTooltipIndex);
                }
              }}
              onMouseLeave={() => setActiveIndex(0)}
            >
              <XAxis dataKey="time" stroke="#4b5563" tick={{fill: '#9ca3af'}} />
              <YAxis yAxisId="left" stroke="#4b5563" tick={{fill: '#9ca3af'}} />
              <YAxis 
                yAxisId="right" 
                orientation="right" 
                stroke="#60a5fa" 
                tick={{fill: '#9ca3af'}} 
                domain={metrics ? [-metrics["Total Power Capacity (MW)"] * 1.1, metrics["Total Power Capacity (MW)"] * 1.1] : [-5.5, 5.5]} 
              />
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" vertical={false} />
              <ReferenceLine yAxisId="right" y={0} stroke="#4b5563" strokeDasharray="3 3" />
              <Tooltip 
                contentStyle={{ backgroundColor: '#111827', borderColor: '#374151', color: '#fff' }}
                itemStyle={{ color: '#fff' }}
              />
              
              {selectedAssetIds.map((id, index) => (
                <Bar 
                  key={id}
                  yAxisId="right"
                  stackId="dispatch_stack"
                  dataKey={`asset_${index}`} 
                  fill={`hsl(${index * 137 % 360}, 70%, 50%)`}
                  name={`Battery ${index + 1} (MW)`}
                  isAnimationActive={false}
                />
              ))}
              
              <Line 
                yAxisId="left"
                type="monotone" 
                dataKey="price" 
                stroke="#10b981" 
                strokeWidth={2}
                dot={false}
                isAnimationActive={false} 
                name="Market Price ($)"
              />
              <Line 
                yAxisId="left"
                type="monotone" 
                dataKey="soc" 
                stroke="#fbbf24" 
                strokeWidth={3}
                dot={false}
                isAnimationActive={false} 
                name="Battery SOC (%)"
              />
            </ComposedChart>
          </ResponsiveContainer>
          </div>
        </section>

      </div>
    </main>
  );
}
