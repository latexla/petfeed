import {
  CartesianGrid, Line, LineChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { WeightEntry } from '../api/weight';
import { c } from '../theme';

interface Props { history: WeightEntry[]; }

export function WeightChart({ history }: Props) {
  const data = [...history].reverse().map((h) => ({
    date: new Date(h.recorded_at).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' }),
    вес: Number(h.weight_kg.toFixed(2)),
  }));

  if (data.length < 2) {
    return (
      <div style={{ color: c.hint, fontSize: 13, textAlign: 'center', padding: 16 }}>
        Добавь 2+ записи для отображения графика
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={180}>
      <LineChart data={data} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={c.border} />
        <XAxis dataKey="date" tick={{ fontSize: 10, fill: c.hint }} />
        <YAxis tick={{ fontSize: 10, fill: c.hint }} domain={['auto', 'auto']} />
        <Tooltip
          contentStyle={{ background: c.bg, border: `1px solid ${c.border}`, borderRadius: 8, fontSize: 13 }}
          formatter={(v: number) => [`${v} кг`, 'Вес']}
        />
        <Line
          type="monotone" dataKey="вес" stroke={c.accent}
          strokeWidth={2} dot={{ r: 3, fill: c.accent }} activeDot={{ r: 5 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
