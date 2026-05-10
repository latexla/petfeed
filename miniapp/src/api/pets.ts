import client from './client';

export interface Pet {
  id: number;
  name: string;
  species: string;
  breed: string | null;
  age_months: number;
  weight_kg: number;
  goal: string;
}

export async function getPets(): Promise<Pet[]> {
  const { data } = await client.get('/v1/pets');
  return data;
}
