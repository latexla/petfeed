import { useState, useCallback } from 'react';
import { addDailyProduct } from '../api/meal';
import { fetchRecommendation, addNamedProduct, RecommendResult } from '../api/recommend';

const MODE_KEY = 'petfeed_feed_mode';
const RECENT_KEY = 'petfeed_recent_ingredients';
const MAX_RECENT = 7;

function loadMode(): 'natural' | 'commercial' {
  return (localStorage.getItem(MODE_KEY) as 'natural' | 'commercial') ?? 'natural';
}

function saveMode(mode: 'natural' | 'commercial'): void {
  localStorage.setItem(MODE_KEY, mode);
}

function loadRecentIngredients(): string[] {
  try {
    return JSON.parse(localStorage.getItem(RECENT_KEY) ?? '[]');
  } catch {
    return [];
  }
}

function saveRecentIngredients(names: string[]): void {
  localStorage.setItem(RECENT_KEY, JSON.stringify(names.slice(0, MAX_RECENT)));
}

export function useRecommend(petId: number | null, onApplied: () => void) {
  const [mode, setModeState] = useState<'natural' | 'commercial'>(loadMode);
  const [selected, setSelected] = useState<string[]>([]);
  const [productName, setProductName] = useState('');
  const [result, setResult] = useState<RecommendResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [applying, setApplying] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const setMode = useCallback((m: 'natural' | 'commercial') => {
    setModeState(m);
    saveMode(m);
    setResult(null);
    setSelected([]);
    setProductName('');
    setError(null);
  }, []);

  const toggleIngredient = useCallback((name: string) => {
    setSelected((prev) =>
      prev.includes(name) ? prev.filter((n) => n !== name) : [...prev, name],
    );
    setResult(null);
  }, []);

  const recommend = useCallback(async () => {
    if (!petId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchRecommendation(
        petId,
        mode,
        mode === 'natural' ? selected : [],
        mode === 'commercial' ? productName : '',
      );
      setResult(data);
    } catch {
      setError('Не удалось получить рекомендацию. Попробуй ещё раз.');
    } finally {
      setLoading(false);
    }
  }, [petId, mode, selected, productName]);

  const apply = useCallback(async () => {
    if (!petId || !result || applying) return;
    setApplying(true);
    try {
      for (const item of result.items) {
        if (item.food_item_id != null) {
          await addDailyProduct(petId, item.food_item_id, item.grams);
        } else {
          await addNamedProduct(petId, item);
        }
      }
      if (mode === 'natural' && selected.length > 0) {
        const current = loadRecentIngredients();
        const updated = Array.from(new Set([...selected, ...current]));
        saveRecentIngredients(updated);
      }
      setResult(null);
      setSelected([]);
      setProductName('');
      onApplied();
    } catch {
      setError('Ошибка при добавлении продуктов.');
    } finally {
      setApplying(false);
    }
  }, [petId, result, applying, mode, selected, onApplied]);

  const cancel = useCallback(() => setResult(null), []);

  const recentIngredients = loadRecentIngredients();

  return {
    mode, setMode,
    selected, toggleIngredient,
    productName, setProductName,
    recentIngredients,
    result, loading, applying, error,
    recommend, apply, cancel,
  };
}
