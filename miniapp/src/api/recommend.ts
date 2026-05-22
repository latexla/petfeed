import client from './client';
import { DailySummary } from './meal';

export interface RecommendItem {
  name: string;
  grams: number;
  kcal: number;
  protein_g: number;
  fat_g: number;
  carb_g: number;
  calcium_mg: number;
  phosphorus_mg: number;
  omega3_mg: number;
  taurine_mg: number;
  food_item_id: number | null;
}

export interface NutrientMap {
  kcal: number;
  protein_g: number;
  fat_g: number;
  carb_g: number;
  calcium_mg: number;
  phosphorus_mg: number;
  omega3_mg: number;
  taurine_mg: number;
}

export interface RecommendResult {
  items: RecommendItem[];
  totals: NutrientMap;
  targets: NutrientMap;
  micro_coverage: Record<string, number>;
  covers_pct: number;
  deficiencies: string[];
  warnings: string[];
}

export async function fetchRecommendation(
  petId: number,
  mode: 'natural' | 'commercial',
  ingredients: string[],
  productName: string,
): Promise<RecommendResult> {
  const { data } = await client.post('/v1/meal/recommend', {
    pet_id: petId,
    mode,
    ingredients,
    product_name: productName,
  });
  return data;
}

export async function addNamedProduct(
  petId: number,
  item: RecommendItem,
): Promise<DailySummary> {
  const { data } = await client.post('/v1/meal/daily/add-named', {
    pet_id: petId,
    name: item.name,
    grams: item.grams,
    kcal_per_100g: item.grams > 0 ? (item.kcal / item.grams) * 100 : 0,
    protein_g: item.grams > 0 ? (item.protein_g / item.grams) * 100 : 0,
    fat_g: item.grams > 0 ? (item.fat_g / item.grams) * 100 : 0,
    carb_g: item.grams > 0 ? (item.carb_g / item.grams) * 100 : 0,
    calcium_mg: item.grams > 0 ? (item.calcium_mg / item.grams) * 100 : 0,
    phosphorus_mg: item.grams > 0 ? (item.phosphorus_mg / item.grams) * 100 : 0,
    omega3_mg: item.grams > 0 ? (item.omega3_mg / item.grams) * 100 : 0,
    taurine_mg: item.grams > 0 ? (item.taurine_mg / item.grams) * 100 : 0,
  });
  return data;
}
