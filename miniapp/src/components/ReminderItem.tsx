import { Reminder } from '../api/reminders';
import { c } from '../theme';

interface Props { reminder: Reminder; onDelete: () => void; }

export function ReminderItem({ reminder, onDelete }: Props) {
  return (
    <div style={{
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      background: c.bgSecondary, borderRadius: 12, padding: '12px 16px', marginBottom: 8,
    }}>
      <span style={{ fontSize: 16, color: c.text }}>⏰ {reminder.time_of_day}</span>
      <button
        onClick={onDelete}
        style={{ background: 'none', border: 'none', color: c.destructive, cursor: 'pointer', fontSize: 20, lineHeight: 1 }}
        aria-label="Удалить"
      >
        ✕
      </button>
    </div>
  );
}
