import { useEffect, useState } from 'react';
import { games as gamesApi } from '../utils/api';

interface BoxScore {
  batters: Record<string, {
    name: string;
    at_bats: number;
    hits: number;
    doubles: number;
    triples: number;
    home_runs: number;
    rbi: number;
    runs: number;
    strikeouts: number;
    walks: number;
  }>;
  pitchers: Record<string, {
    name: string;
    strikeouts: number;
    walks: number;
    hits_allowed: number;
    home_runs_allowed: number;
    runs_allowed: number;
  }>;
}

interface UseGameStatsReturn {
  boxScore: BoxScore | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export const useGameStats = (gameId: string): UseGameStatsReturn => {
  const [boxScore, setBoxScore] = useState<BoxScore | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Intentar obtener box score desde la API
      const response = await gamesApi.getBoxScore?.(gameId);
      if (response?.box_score) {
        setBoxScore(response.box_score);
      }
    } catch (err) {
      // Si no existe la API aún, inicializar con estructura vacía
      setError(null);
      setBoxScore({ batters: {}, pitchers: {} });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (gameId) {
      fetchStats();
    }
  }, [gameId]);

  return {
    boxScore,
    loading,
    error,
    refetch: fetchStats,
  };
};
