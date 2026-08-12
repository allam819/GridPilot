'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { Activity, LogOut, LayoutDashboard, Cpu, Database } from 'lucide-react';

export default function Navbar() {
  const { token, logout } = useAuth();
  const pathname = usePathname();

  if (!token) return null;

  return (
    <nav className="bg-gray-900 border-b border-gray-800 text-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center gap-8">
            <Link href="/" className="flex items-center gap-2 text-emerald-400">
              <Activity size={24} />
              <span className="font-light text-xl text-white">Grid<span className="font-bold text-emerald-400">Pilot</span></span>
            </Link>
            
            <div className="flex space-x-4">
              <Link 
                href="/" 
                className={`flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition ${
                  pathname === '/' ? 'bg-gray-800 text-white' : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                }`}
              >
                <LayoutDashboard size={18} />
                VPP Dashboard
              </Link>
              <Link 
                href="/digital-twin" 
                className={`flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition ${
                  pathname === '/digital-twin' ? 'bg-gray-800 text-emerald-400' : 'text-gray-300 hover:bg-gray-800 hover:text-emerald-400'
                }`}
              >
                <Cpu size={18} />
                Digital Twin
              </Link>
              <Link 
                href="/assets" 
                className={`flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition ${
                  pathname === '/assets' ? 'bg-gray-800 text-emerald-400' : 'text-gray-300 hover:bg-gray-800 hover:text-emerald-400'
                }`}
              >
                <Database size={18} />
                Assets
              </Link>
            </div>
          </div>
          
          <div>
            <button 
              onClick={logout}
              className="flex items-center gap-2 text-gray-400 hover:text-red-400 transition text-sm font-medium px-3 py-2"
            >
              <LogOut size={18} />
              Sign Out
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
}
