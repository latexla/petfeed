import { useCallback, useEffect, useState } from 'react';
import {
  DailySummary, FoodSearchResult, MealHistoryEntry,
  addDailyProduct, getDailySummary, getMealHistory,
  resetDailyMeal, searchFood, undoDailyLast,
} from '../api/meal';

export function useMealSession(petId: number | null, species: string | null) {
  const [summary, setSummary] = useState<DailySummary | null>(null);
  const [history, setHistory] = useState<MealHistoryEntry[]>([]);
  const [searchResults, setSearchResults] = useState<FoodSearchResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [searching, setSearching] = useState(false);
  const [adding, setAdding] = useState(false);

  const loadSummary = useCallback(async () => {
    if (!petId) return;
    try {
      const data = await getDailySummary(petId);
      setSummary(data);
    } catch {
      setSummary({ items: [], totals: {} as DailySummary['totals'], daily_target: null, quality_score: 0, quality_label: 'poor', tips: [] });
    }
  }, [petId]);

  const loadHistory = useCallback(async () => {
    if (!petId) return;
    try {
      const data = await getMealHistory(petId);
      setHistory(data);
    } catch {
      // silent — history not critical
    }
  }, [petId]);

  useEffect(() => {
    if (!petId) return;
    setLoading(true);
    Promise.all([loadSummary(), loadHistory()]).finally(() => setLoading(false));
  }, [petId, loadSummary, loadHistory]);

  const search = useCallback(async (q: string) => {
    if (!q.trim() || !species) { setSearchResults([]); return; }
    setSearching(true);
    try {
      const results = await searchFood(q, species);
      setSearchResults(results);
    } finally {
      setSearching(false);
    }
  }, [species]);

  const add = async (foodItemId: number, grams: number): Promise<void> => {
    if (!petId || adding) return;
    setAdding(true);
    try {
      const newSummary = await addDailyProduct(petId, foodItemId, grams);
      setSummary(newSummary);
      setSearchResults([]);
    } finally {
      setAdding(false);
    }
  };

  const undo = async (): Promise<void> => {
    if (!petId) return;
    await undoDailyLast(petId);
    await loadSummary();
  };

  const reset = async (): Promise<void> => {
    if (!petId) return;
    await resetDailyMeal(petId);
    await Promise.all([loadSummary(), loadHistory()]);
  };

  return { summary, history, searchResults, loading, searching, adding, search, add, undo, reset };
}
