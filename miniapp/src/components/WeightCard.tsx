import { useNavigate } from 'react-router-dom';
import { WeightEntry } from '../api/weight';
import { c } from '../theme';

interface Props {
  history: WeightEntry[];
  loading: boolean;
}

export function WeightCard({ history, loading }: Props) {
  const navigate = useNavigate();
  const latest = history[0];
  const prev = history[1];
  const delta = latest && prev
    ? Number((latest.weight_kg - prev.weight_kg).toFixed(2))
    : null;

  return (
    <div
      onClick={() => navigate('/weight')}
      style={{ background: c.bgSecondary, borderRadius: 16, padding: 16, marginBottom: 12, cursor: 'pointer' }}
    >
      <div style={{ fontWeight: 600, fontSize: 15, color: c.text, marginBottom: 6 }}>⚖️ Вес</div>
      {loading ? (
        <div style={{ color: c.hint, fontSize: 13 }}>Загрузка...</div>
      ) : latest ? (
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
          <span style={{ fontSize: 24, fontWeight: 700, color: c.text }}>{latest.weight_kg} кг</span>
          {delta !== null && delta !== 0 && (
            <span style={{ fontSize: 13, color: delta < 0 ? '#34c759' : '#ff9500' }}>
              {delta > 0 ? `▲ +${delta}` : `▼ ${delta}`} кг
            </span>
          )}
        </div>
      ) : (
        <div style={{ color: c.hint, fontSize: 13 }}>Нет данных — добавь первый вес</div>
      )}
    </div>
  );
}
