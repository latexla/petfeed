import client from './client';

export interface Reminder {
  id: number;
  pet_id: number;
  time_of_day: string;
}

export async function getReminders(petId: number): Promise<Reminder[]> {
  const { data } = await client.get(`/v1/reminders/${petId}`);
  return data;
}

export async function setReminders(petId: number, times: string[]): Promise<Reminder[]> {
  const { data } = await client.post('/v1/reminders', { pet_id: petId, times });
  return data;
}
