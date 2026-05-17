import { useCallback, useEffect, useState } from 'react';
import {
  WeightEntry, WeightUpdateResponse,
  getWeightHistory, updateWeight,
} from '../api/weight';

export function useWeightHistory(petId: number | null) {
  const [history, setHistory] = useState<WeightEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [updating, setUpdating] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<WeightUpdateResponse | null>(null);

  const load = useCallback(() => {
    if (!petId) return;
    setLoading(true);
    getWeightHistory(petId).then(setHistory).finally(() => setLoading(false));
  }, [petId]);

  useEffect(() => { load(); }, [load]);

  const update = async (weightKg: number): Promise<WeightUpdateResponse | null> => {
    if (!petId) return null;
    setUpdating(true);
    try {
      const result = await updateWeight(petId, weightKg);
      setLastUpdate(result);
      load();
      return result;
    } finally {
      setUpdating(false);
    }
  };

  return { history, loading, updating, lastUpdate, update, reload: load };
}
