import client from './client';

export interface AIResponse {
  answer: string;
  cache_hit: boolean;
  requests_left: number;
}

export async function askAI(petId: number, question: string): Promise<AIResponse> {
  const { data } = await client.post('/v1/ai/ask', { pet_id: petId, question });
  return data;
}
