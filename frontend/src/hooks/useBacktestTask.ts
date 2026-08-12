import { useState, useEffect, useRef } from 'react';
import { useAuth } from '@/context/AuthContext';

export type TaskStatus = 'PENDING' | 'SUCCESS' | 'FAILURE' | 'IDLE';

interface UseBacktestTaskResult {
  status: TaskStatus;
  metrics: any | null;
  error: string | null;
  runBacktest: (startDate: string, endDate: string, assetIds?: number[]) => void;
}

export function useBacktestTask(): UseBacktestTaskResult {
  const [status, setStatus] = useState<TaskStatus>('IDLE');
  const [metrics, setMetrics] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const { token, logout } = useAuth();

  const clearPolling = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  };

  // Cleanup on unmount
  useEffect(() => {
    return clearPolling;
  }, []);

  const runBacktest = async (startDate: string, endDate: string, assetIds?: number[]) => {
    if (new Date(startDate) > new Date(endDate)) {
      setStatus('FAILURE');
      setError('Start date must be before end date.');
      return;
    }
    
    setStatus('PENDING');
    setMetrics(null);
    setError(null);
    clearPolling(); // Clear any existing

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const res = await fetch(`${API_URL}/api/v1/backtest/run`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ start_date: startDate, end_date: endDate, asset_ids: assetIds }),
      });

      if (res.status === 401) { logout(); return; }
      if (!res.ok) throw new Error('Failed to start backtest');

      const data = await res.json();
      const taskId = data.task_id;

      // Start polling every 2 seconds
      intervalRef.current = setInterval(async () => {
        try {
          const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
          const pollRes = await fetch(`${API_URL}/api/v1/backtest/tasks/${taskId}`, {
            headers: { 'Authorization': `Bearer ${token}` }
          });
          
          if (pollRes.status === 401) {
            clearPolling();
            logout();
            return;
          }

          const pollData = await pollRes.json();

          if (pollData.status === 'SUCCESS') {
            setStatus('SUCCESS');
            setMetrics(pollData.result?.metrics || pollData.result);
            clearPolling();
          } else if (pollData.status === 'FAILURE') {
            setStatus('FAILURE');
            setError(pollData.error || 'Task failed');
            clearPolling();
          }
        } catch (err: any) {
          console.error("Error polling task:", err);
          setStatus('FAILURE');
          setError(err.message || "Failed to poll task");
          clearPolling();
        }
      }, 2000);
    } catch (err: any) {
      console.error("Error starting backtest:", err);
      setStatus('FAILURE');
      setError(err.message || 'Failed to start backtest');
    }
  };

  return { status, metrics, error, runBacktest };
}
