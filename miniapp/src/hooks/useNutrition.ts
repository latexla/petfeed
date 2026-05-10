import { useEffect, useState } from 'react';
import { Ration, getNutrition } from '../api/nutrition';

export function useNutrition(petId: number | null) {
  const [ration, setRation] = useState<Ration | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!petId) return;
    setLoading(true);
    setError(null);
    getNutrition(petId)
      .then(setRation)
      .catch(() => setError('Не удалось загрузить рацион'))
      .finally(() => setLoading(false));
  }, [petId]);

  return { ration, loading, error };
}
