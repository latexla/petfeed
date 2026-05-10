import client from './client';

export interface StopFoodItem {
  product_name: string;
  toxic_component: string | null;
  clinical_effect: string | null;
}

export interface Ration {
  pet_id: number;
  daily_calories: number;
  meals_per_day: number;
  protein_min_g: number;
  fat_min_g: number;
  stop_foods_level1: StopFoodItem[];
  stop_foods_level2: StopFoodItem[];
  stop_foods_level3: StopFoodItem[];
  recommendations: string[];
  hypoglycemia_warning: boolean;
  notes: string;
}

export async function getNutrition(petId: number): Promise<Ration> {
  const { data } = await client.get(`/v1/nutrition/${petId}`);
  return data;
}
