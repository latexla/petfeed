import { useState } from 'react';
import { ReminderItem } from '../components/ReminderItem';
import { usePet } from '../contexts/PetContext';
import { useReminders } from '../hooks/useReminders';

export function Reminders() {
  const { activePet } = usePet();
  const { reminders, loading, add, remove } = useReminders(activePet?.id ?? null);
  const [newTime, setNewTime] = useState('');
  const [saving, setSaving] = useState(false);

  const handleAdd = async () => {
    if (!newTime || saving) return;
    setSaving(true);
    try {
      await add(newTime);
      setNewTime('');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div style={{ padding: 24, color: '#999' }}>Загрузка...</div>;

  return (
    <div style={{ padding: 16, paddingBottom: 80 }}>
      <h2 style={{ marginBottom: 16 }}>Напоминания</h2>

      {reminders.length === 0 && (
        <div style={{ color: '#8e8e93', fontSize: 14, marginBottom: 16 }}>
          Нет напоминаний — добавь первое 👇
        </div>
      )}

      {reminders.map((r) => (
        <ReminderItem key={r.id} reminder={r} onDelete={() => remove(r.id)} />
      ))}

      <div style={{ display: 'flex', gap: 10, marginTop: 16 }}>
        <input
          type="time"
          value={newTime}
          onChange={(e) => setNewTime(e.target.value)}
          style={{
            flex: 1, padding: '12px 14px', borderRadius: 12,
            border: '1px solid #ddd', fontSize: 16, outline: 'none',
          }}
        />
        <button
          onClick={handleAdd}
          disabled={!newTime || saving}
          style={{
            padding: '12px 22px', background: '#007aff', color: '#fff',
            border: 'none', borderRadius: 12, fontSize: 20, cursor: 'pointer',
            opacity: !newTime || saving ? 0.5 : 1,
          }}
        >
          +
        </button>
      </div>
    </div>
  );
}
