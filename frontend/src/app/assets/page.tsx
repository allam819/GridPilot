'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import { Activity, Plus, Trash2, Battery } from 'lucide-react';

interface Asset {
  id: number;
  name: string;
  power_capacity_mw: number;
  energy_capacity_mwh: number;
}

export default function AssetsPage() {
  const { token, logout } = useAuth();
  const [assets, setAssets] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  // Form State
  const [name, setName] = useState('');
  const [power, setPower] = useState('');
  const [energy, setEnergy] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchAssets = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/v1/assets', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.status === 401) { logout(); return; }
      if (!res.ok) throw new Error('Failed to fetch assets');
      const data = await res.json();
      setAssets(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) fetchAssets();
  }, [token]);

  const handleCreateAsset = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      const res = await fetch('http://localhost:8000/api/v1/assets', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}` 
        },
        body: JSON.stringify({
          name,
          power_capacity_mw: parseFloat(power),
          energy_capacity_mwh: parseFloat(energy)
        })
      });
      if (res.status === 401) { logout(); return; }
      if (!res.ok) throw new Error('Failed to create asset');
      
      setName('');
      setPower('');
      setEnergy('');
      await fetchAssets();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      const res = await fetch(`http://localhost:8000/api/v1/assets/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.status === 401) { logout(); return; }
      if (!res.ok) throw new Error('Failed to delete asset');
      await fetchAssets();
    } catch (err: any) {
      setError(err.message);
    }
  };

  if (loading) {
    return <div className="min-h-screen bg-gray-950 flex items-center justify-center text-emerald-400"><Activity className="animate-spin" /></div>;
  }

  return (
    <main className="min-h-screen bg-gray-950 text-white p-8 font-sans">
      <div className="max-w-6xl mx-auto space-y-8">
        <header className="border-b border-gray-800 pb-4">
          <h1 className="text-4xl font-light text-emerald-400">Asset <span className="font-bold">Portfolio</span></h1>
          <p className="text-gray-400 mt-2">Manage your organization's battery energy storage systems (BESS).</p>
        </header>

        {error && (
          <div className="bg-red-500/10 border border-red-500/50 text-red-400 p-4 rounded-lg text-sm">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Create Asset Form */}
          <div className="lg:col-span-1">
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
              <h2 className="text-xl font-bold flex items-center gap-2 text-gray-200 mb-6">
                <Plus size={20} /> Add New Asset
              </h2>
              <form onSubmit={handleCreateAsset} className="space-y-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Asset Name</label>
                  <input 
                    type="text" required value={name} onChange={e => setName(e.target.value)}
                    placeholder="e.g., Texas Node Alpha"
                    className="w-full bg-gray-950 border border-gray-800 rounded-lg p-2.5 text-white focus:outline-none focus:border-emerald-500 transition"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Power Capacity (MW)</label>
                  <input 
                    type="number" required step="0.1" min="0.1" value={power} onChange={e => setPower(e.target.value)}
                    placeholder="e.g., 5.0"
                    className="w-full bg-gray-950 border border-gray-800 rounded-lg p-2.5 text-white focus:outline-none focus:border-emerald-500 transition"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Energy Capacity (MWh)</label>
                  <input 
                    type="number" required step="0.1" min="0.1" value={energy} onChange={e => setEnergy(e.target.value)}
                    placeholder="e.g., 10.0"
                    className="w-full bg-gray-950 border border-gray-800 rounded-lg p-2.5 text-white focus:outline-none focus:border-emerald-500 transition"
                  />
                </div>
                <button 
                  type="submit" disabled={isSubmitting}
                  className="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-3 rounded-lg mt-4 transition disabled:opacity-50"
                >
                  {isSubmitting ? 'Provisioning...' : 'Provision Asset'}
                </button>
              </form>
            </div>
          </div>

          {/* Asset Grid */}
          <div className="lg:col-span-2">
            <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
              {assets.length === 0 ? (
                <div className="p-12 text-center text-gray-500">
                  <Battery className="mx-auto h-12 w-12 text-gray-700 mb-4" />
                  <h3 className="text-lg font-medium text-gray-300">No assets found</h3>
                  <p className="mt-1">Provision a new battery asset to begin VPP optimization.</p>
                </div>
              ) : (
                <table className="w-full text-left text-sm text-gray-300">
                  <thead className="bg-gray-950 text-gray-400 uppercase border-b border-gray-800">
                    <tr>
                      <th className="px-6 py-4 font-medium">Asset Name</th>
                      <th className="px-6 py-4 font-medium">Power (MW)</th>
                      <th className="px-6 py-4 font-medium">Energy (MWh)</th>
                      <th className="px-6 py-4 font-medium text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {assets.map((asset) => (
                      <tr key={asset.id} className="border-b border-gray-800/50 hover:bg-gray-800/20 transition">
                        <td className="px-6 py-4 font-medium text-emerald-400 flex items-center gap-3">
                          <Battery size={16} /> {asset.name}
                        </td>
                        <td className="px-6 py-4 font-mono">{asset.power_capacity_mw.toFixed(1)}</td>
                        <td className="px-6 py-4 font-mono">{asset.energy_capacity_mwh.toFixed(1)}</td>
                        <td className="px-6 py-4 text-right">
                          <button 
                            onClick={() => handleDelete(asset.id)}
                            className="text-gray-500 hover:text-red-400 transition"
                            title="Delete Asset"
                          >
                            <Trash2 size={18} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>

        </div>
      </div>
    </main>
  );
}
