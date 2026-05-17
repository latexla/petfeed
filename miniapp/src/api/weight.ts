import client from './client';

export interface WeightEntry {
  weight_kg: number;
  recorded_at: string;
}

export interface WeightUpdateResponse {
  pet_id: number;
  old_weight: number;
  new_weight: number;
  ration_recalculated: boolean;
}

export async function updateWeight(petId: number, weightKg: number): Promise<WeightUpdateResponse> {
  const { data } = await client.post('/v1/weight', { pet_id: petId, weight_kg: weightKg });
  return data;
}

export async function getWeightHistory(petId: number): Promise<WeightEntry[]> {
  const { data } = await client.get(`/v1/weight/history/${petId}`);
  return data;
}
