import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { WeightChart } from '../components/WeightChart';
import { usePet } from '../contexts/PetContext';
import { useWeightHistory } from '../hooks/useWeightHistory';
import { c } from '../theme';

export function Weight() {
  const { activePet } = usePet();
  const { history, loading, updating, lastUpdate, update } = useWeightHistory(activePet?.id ?? null);
  const [input, setInput] = useState('');
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const handleUpdate = async () => {
    const kg = parseFloat(input);
    if (!kg || kg <= 0 || kg > 200) { setError('Введи корректный вес (0.1–200 кг)'); return; }
    setError(null);
    try {
      await update(kg);
      setInput('');
    } catch {
      setError('Ошибка при обновлении веса');
    }
  };

  if (loading) return <div style={{ padding: 24, color: c.hint }}>Загрузка...</div>;

  const latest = history[0];

  return (
    <div style={{ paddingBottom: 80 }}>
      <div style={{ display: 'flex', alignItems: 'center', padding: '12px 16px', borderBottom: `1px solid ${c.border}`, background: c.bg }}>
        <button onClick={() => navigate(-1)} style={{ background: 'none', border: 'none', fontSize: 22, cursor: 'pointer', color: c.accent, paddingRight: 8 }}>‹</button>
        <span style={{ fontWeight: 600, fontSize: 17, color: c.text }}>Трекер веса · {activePet?.name}</span>
      </div>

      <div style={{ padding: 16 }}>
        <div style={{ background: c.bgSecondary, borderRadius: 16, padding: 16, marginBottom: 16 }}>
          <div style={{ fontSize: 13, color: c.hint, marginBottom: 4 }}>Текущий вес</div>
          <div style={{ fontSize: 32, fontWeight: 700, color: c.text }}>
            {latest ? `${latest.weight_kg} кг` : '—'}
          </div>
          {lastUpdate?.ration_recalculated && (
            <div style={{ fontSize: 12, color: '#34c759', marginTop: 4 }}>✓ Рацион пересчитан</div>
          )}
        </div>

        <div style={{ display: 'flex', gap: 10, marginBottom: 4 }}>
          <input
            type="number" step="0.1" min="0.1" max="200"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleUpdate()}
            placeholder="Новый вес, кг"
            style={{ flex: 1, padding: '12px 14px', borderRadius: 12, border: `1px solid ${error ? c.destructive : c.border}`, fontSize: 16, outline: 'none', background: c.bg, color: c.text }}
          />
          <button
            onClick={handleUpdate}
            disabled={updating || !input}
            style={{ padding: '12px 20px', background: c.accent, color: c.accentText, border: 'none', borderRadius: 12, fontSize: 15, fontWeight: 600, cursor: 'pointer', opacity: updating || !input ? 0.5 : 1 }}
          >
            {updating ? '...' : 'Обновить'}
          </button>
        </div>
        {error && <div style={{ color: c.destructive, fontSize: 12, marginBottom: 12 }}>{error}</div>}

        {history.length >= 2 && (
          <div style={{ background: c.bgSecondary, borderRadius: 16, padding: 16, marginTop: 16, marginBottom: 16 }}>
            <div style={{ fontWeight: 600, fontSize: 15, color: c.text, marginBottom: 12 }}>📈 Динамика веса</div>
            <WeightChart history={history} />
          </div>
        )}

        {history.length > 0 && (
          <div style={{ background: c.bgSecondary, borderRadius: 16, overflow: 'hidden' }}>
            <div style={{ fontWeight: 600, fontSize: 15, color: c.text, padding: '12px 16px', borderBottom: `1px solid ${c.border}` }}>История</div>
            {history.map((h, i) => {
              const prev = history[i + 1];
              const delta = prev ? Number((h.weight_kg - prev.weight_kg).toFixed(2)) : null;
              return (
                <div key={h.recorded_at} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 16px', borderBottom: i < history.length - 1 ? `1px solid ${c.border}` : 'none' }}>
                  <span style={{ fontSize: 14, color: c.hint }}>
                    {new Date(h.recorded_at).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short', year: '2-digit' })}
                  </span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span style={{ fontWeight: 600, color: c.text, fontSize: 15 }}>{h.weight_kg} кг</span>
                    {delta !== null && delta !== 0 && (
                      <span style={{ fontSize: 12, color: delta < 0 ? '#34c759' : '#ff9500' }}>
                        {delta > 0 ? `▲ +${delta}` : `▼ ${delta}`}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
