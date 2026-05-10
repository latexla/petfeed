import { useCallback, useEffect, useState } from 'react';
import { Reminder, getReminders, setReminders } from '../api/reminders';

export function useReminders(petId: number | null) {
  const [reminders, setLocal] = useState<Reminder[]>([]);
  const [loading, setLoading] = useState(false);

  const load = useCallback(() => {
    if (!petId) return;
    setLoading(true);
    getReminders(petId).then(setLocal).finally(() => setLoading(false));
  }, [petId]);

  useEffect(() => { load(); }, [load]);

  const add = async (time: string) => {
    if (!petId) return;
    const times = [...reminders.map((r) => r.time_of_day), time];
    const updated = await setReminders(petId, times);
    setLocal(updated);
  };

  const remove = async (id: number) => {
    if (!petId) return;
    const times = reminders.filter((r) => r.id !== id).map((r) => r.time_of_day);
    const updated = await setReminders(petId, times);
    setLocal(updated);
  };

  return { reminders, loading, add, remove };
}
