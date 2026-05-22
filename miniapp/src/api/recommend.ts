// src/api/recommend.ts stub
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
  _petId: number,
  _mode: 'natural' | 'commercial',
  _ingredients: string[],
  _productName: string
): Promise<RecommendResult> {
  throw new Error('stub');
}

export async function addNamedProduct(
  _petId: number,
  _item: RecommendItem
): Promise<any> {
  throw new Error('stub');
}
