import { useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FoodSearchResult } from '../api/meal';
import { QualityBadge } from '../components/QualityBadge';
import { ProgressBar } from '../components/ProgressBar';
import { usePet } from '../contexts/PetContext';
import { useMealSession } from '../hooks/useMealSession';
import { c } from '../theme';

export function Meal() {
  const { activePet } = usePet();
  const { summary, history, searchResults, loading, searching, adding, search, add, undo, reset } =
    useMealSession(activePet?.id ?? null, activePet?.species ?? null);

  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState<FoodSearchResult | null>(null);
  const [grams, setGrams] = useState('');
  const [confirmReset, setConfirmReset] = useState(false);
  const navigate = useNavigate();

  const handleSearch = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const v = e.target.value;
      setQuery(v);
      if (v.length >= 2) search(v);
    },
    [search],
  );

  const handleSelect = (r: FoodSearchResult) => {
    setSelected(r);
    setQuery(r.name);
  };

  const handleAdd = async () => {
    if (!selected || !grams || adding) return;
    const g = parseFloat(grams);
    if (!g || g <= 0) return;
    await add(selected.id, g);
    setSelected(null);
    setQuery('');
    setGrams('');
  };

  const handleReset = async () => {
    if (!confirmReset) { setConfirmReset(true); return; }
    await reset();
    setConfirmReset(false);
  };

  const kcalTarget = summary?.daily_target?.kcal ?? 0;
  const kcalActual = summary?.totals?.kcal ?? 0;

  if (loading) return <div style={{ padding: 24, color: c.hint }}>Загрузка...</div>;
  if (!activePet) return <div style={{ padding: 24, color: c.hint }}>Сначала создай питомца в боте</div>;

  return (
    <div style={{ paddingBottom: 80 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', padding: '12px 16px', borderBottom: `1px solid ${c.border}`, background: c.bg }}>
        <button onClick={() => navigate(-1)} style={{ background: 'none', border: 'none', fontSize: 22, cursor: 'pointer', color: c.accent, paddingRight: 8 }}>‹</button>
        <span style={{ fontWeight: 600, fontSize: 17, color: c.text }}>Питание · {activePet.name}</span>
      </div>

      <div style={{ padding: 16 }}>
        {/* Daily summary block */}
        <div style={{ background: c.bgSecondary, borderRadius: 16, padding: 16, marginBottom: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <span style={{ fontSize: 14, color: c.hint }}>
              {Math.round(kcalActual)} / {Math.round(kcalTarget)} ккал
            </span>
            {summary && summary.items.length > 0 && (
              <QualityBadge score={summary.quality_score} quality={summary.quality_label} />
            )}
          </div>

          <ProgressBar value={kcalActual} target={kcalTarget} height={10} />

          {summary?.totals && kcalActual > 0 && (
            <div style={{ display: 'flex', gap: 16, marginTop: 10, fontSize: 12, color: c.hint }}>
              <span>Б: {Math.round(summary.totals.protein_g)}г</span>
              <span>Ж: {Math.round(summary.totals.fat_g)}г</span>
              <span>У: {Math.round(summary.totals.carb_g)}г</span>
            </div>
          )}

          {summary?.tips && summary.tips.length > 0 && kcalActual > 0 && (
            <div style={{ marginTop: 10 }}>
              {summary.tips.slice(0, 3).map((tip, i) => (
                <div key={i} style={{ fontSize: 12, color: c.hint, marginTop: 4 }}>💡 {tip}</div>
              ))}
            </div>
          )}
        </div>

        {/* Search */}
        <div style={{ marginBottom: 16 }}>
          <input
            value={query}
            onChange={handleSearch}
            placeholder="🔍 Найди продукт (мин. 2 символа)..."
            style={{ width: '100%', padding: '12px 14px', borderRadius: 12, border: `1px solid ${c.border}`, fontSize: 15, outline: 'none', background: c.bg, color: c.text, boxSizing: 'border-box' }}
          />

          {searching && (
            <div style={{ color: c.hint, fontSize: 13, marginTop: 6 }}>Поиск...</div>
          )}

          {!selected && searchResults.length > 0 && (
            <div style={{ background: c.bg, borderRadius: 12, border: `1px solid ${c.border}`, marginTop: 8, overflow: 'hidden' }}>
              {searchResults.map((r) => (
                <div
                  key={r.id}
                  onClick={() => handleSelect(r)}
                  style={{ padding: '10px 14px', borderBottom: `1px solid ${c.border}`, cursor: 'pointer' }}
                >
                  <div style={{ fontSize: 14, color: c.text, fontWeight: 500 }}>{r.name}</div>
                  <div style={{ fontSize: 12, color: c.hint, marginTop: 2 }}>
                    {Math.round(r.kcal_per_100g)} ккал/100г · Б:{Math.round(r.protein_g)}г Ж:{Math.round(r.fat_g)}г
                  </div>
                </div>
              ))}
            </div>
          )}

          {selected && (
            <div style={{ marginTop: 10, background: c.bgSecondary, borderRadius: 12, padding: 14 }}>
              <div style={{ fontSize: 14, color: c.text, fontWeight: 600, marginBottom: 8 }}>
                {selected.name} · {Math.round(selected.kcal_per_100g)} ккал/100г
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <input
                  type="number" min="1" max="2000"
                  value={grams}
                  onChange={(e) => setGrams(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
                  placeholder="граммов"
                  autoFocus
                  style={{ flex: 1, padding: '10px 12px', borderRadius: 10, border: `1px solid ${c.border}`, fontSize: 15, background: c.bg, color: c.text, outline: 'none' }}
                />
                <button
                  onClick={handleAdd}
                  disabled={!grams || adding}
                  style={{ padding: '10px 18px', background: c.accent, color: c.accentText, border: 'none', borderRadius: 10, fontSize: 15, fontWeight: 600, cursor: 'pointer', opacity: !grams || adding ? 0.5 : 1 }}
                >
                  {adding ? '...' : '+ Добавить'}
                </button>
              </div>
              <button
                onClick={() => { setSelected(null); setQuery(''); setGrams(''); }}
                style={{ marginTop: 8, background: 'none', border: 'none', color: c.hint, fontSize: 13, cursor: 'pointer' }}
              >
                ✕ Отменить выбор
              </button>
            </div>
          )}
        </div>

        {/* Items list */}
        {summary?.items && summary.items.length > 0 && (
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontWeight: 600, fontSize: 15, color: c.text, marginBottom: 8 }}>Добавлено сегодня</div>
            {summary.items.map((item, i) => (
              <div
                key={i}
                style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: c.bgSecondary, borderRadius: 12, padding: '10px 14px', marginBottom: 8 }}
              >
                <div>
                  <div style={{ fontSize: 14, color: c.text, fontWeight: 500 }}>{item.name}</div>
                  <div style={{ fontSize: 12, color: c.hint, marginTop: 2 }}>{item.grams}г · {Math.round(item.kcal)} ккал</div>
                </div>
                {i === summary.items.length - 1 && (
                  <button onClick={undo} style={{ background: 'none', border: 'none', color: c.destructive, fontSize: 20, cursor: 'pointer', lineHeight: 1 }}>✕</button>
                )}
              </div>
            ))}
          </div>
        )}

        {/* History */}
        {history.length > 0 && (
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontWeight: 600, fontSize: 15, color: c.text, marginBottom: 8 }}>Последние дни</div>
            {history.slice(0, 7).map((h) => (
              <div
                key={h.session_date}
                style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: `1px solid ${c.border}` }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div style={{ width: 10, height: 10, borderRadius: '50%', flexShrink: 0, background: h.quality === 'good' ? '#34c759' : h.quality === 'ok' ? '#ff9500' : '#ff3b30' }} />
                  <span style={{ fontSize: 14, color: c.text }}>
                    {new Date(h.session_date).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' })}
                  </span>
                </div>
                <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                  <span style={{ fontSize: 13, color: c.hint }}>{Math.round(h.total_kcal)} ккал</span>
                  <span style={{ fontSize: 13, fontWeight: 600, color: h.quality === 'good' ? '#34c759' : h.quality === 'ok' ? '#ff9500' : '#ff3b30' }}>
                    {h.score}/100
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Reset button */}
        {summary?.items && summary.items.length > 0 && (
          <button
            onClick={handleReset}
            style={{ width: '100%', padding: 12, background: 'none', border: `1px solid ${c.destructive}`, color: c.destructive, borderRadius: 12, fontSize: 14, cursor: 'pointer' }}
          >
            {confirmReset ? '⚠️ Подтвердить сброс дня' : '🗑 Сбросить день'}
          </button>
        )}
      </div>
    </div>
  );
}
