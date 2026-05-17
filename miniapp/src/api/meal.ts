import client from './client';

export interface FoodSearchResult {
  id: number;
  name: string;
  category: string;
  kcal_per_100g: number;
  protein_g: number;
  fat_g: number;
  carb_g: number;
}

export interface DailyItem {
  food_item_id: number;
  name: string;
  grams: number;
  kcal: number;
  protein_g: number;
  fat_g: number;
  carb_g: number;
}

export interface DailyTotals {
  kcal: number;
  protein_g: number;
  fat_g: number;
  carb_g: number;
  calcium_mg: number;
  phosphorus_mg: number;
  omega3_mg: number;
  taurine_mg: number;
}

export interface DailySummary {
  items: DailyItem[];
  totals: DailyTotals;
  daily_target: Record<string, number> | null;
  quality_score: number;
  quality_label: 'good' | 'ok' | 'poor';
  tips: string[];
}

export interface MealHistoryEntry {
  session_date: string;
  total_kcal: number;
  score: number;
  quality: 'good' | 'ok' | 'poor';
  kcal_pct: number | null;
  tips: string[];
}

export async function searchFood(q: string, species: string): Promise<FoodSearchResult[]> {
  const { data } = await client.get('/v1/meal/food-search', { params: { q, species } });
  return data;
}

export async function addDailyProduct(
  petId: number,
  foodItemId: number,
  grams: number,
): Promise<DailySummary> {
  const { data } = await client.post('/v1/meal/daily/add', {
    pet_id: petId,
    food_item_id: foodItemId,
    grams,
    food_type: 'natural',
  });
  return data;
}

export async function getDailySummary(petId: number): Promise<DailySummary> {
  const { data } = await client.get(`/v1/meal/daily/summary/${petId}`);
  return data;
}

export async function resetDailyMeal(petId: number): Promise<void> {
  await client.delete(`/v1/meal/daily/reset/${petId}`);
}

export async function undoDailyLast(petId: number): Promise<void> {
  await client.post(`/v1/meal/daily/undo/${petId}`);
}

export async function getMealHistory(petId: number): Promise<MealHistoryEntry[]> {
  const { data } = await client.get(`/v1/meal/history/${petId}`);
  return data;
}
