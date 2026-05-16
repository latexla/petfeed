import { useState } from 'react';
import { usePet } from '../contexts/PetContext';
import { useNutrition } from '../hooks/useNutrition';
import { c } from '../theme';

export function Nutrition() {
  const { activePet, loading: petLoading } = usePet();
  const { ration, loading: rationLoading, error } = useNutrition(activePet?.id ?? null);
  const [showStopList, setShowStopList] = useState(false);

  if (petLoading || rationLoading) return <div style={{ padding: 24, color: c.hint }}>Загрузка...</div>;
  if (error) return <div style={{ padding: 24, color: c.destructive }}>{error}</div>;
  if (!ration) return <div style={{ padding: 24, color: c.hint }}>Рацион не найден</div>;

  const allStopFoods = [
    ...ration.stop_foods_level1,
    ...ration.stop_foods_level2,
    ...ration.stop_foods_level3,
  ];

  return (
    <div style={{ padding: 16, paddingBottom: 80 }}>
      <h2 style={{ marginBottom: 16, color: c.text }}>Рацион питания</h2>

      <div style={{ background: c.bgSecondary, borderRadius: 16, padding: 16, marginBottom: 12 }}>
        <div style={{ fontSize: 24, fontWeight: 700, color: c.text }}>🔥 {Math.round(ration.daily_calories)} ккал/день</div>
        <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 6, fontSize: 15, color: c.text }}>
          <div>🥩 Белки (мин.): <b>{Math.round(ration.protein_min_g)} г</b></div>
          <div>🫒 Жиры (мин.): <b>{Math.round(ration.fat_min_g)} г</b></div>
          <div>🍽 Приёмов в день: <b>{ration.meals_per_day}</b></div>
        </div>
      </div>

      {ration.recommendations.length > 0 && (
        <div style={{ background: c.bgSecondary, borderRadius: 12, padding: 14, marginBottom: 12 }}>
          <div style={{ fontWeight: 600, marginBottom: 6, color: c.text }}>Рекомендации</div>
          {ration.recommendations.map((r, i) => (
            <div key={i} style={{ fontSize: 13, color: c.hint, marginBottom: 4 }}>• {r}</div>
          ))}
        </div>
      )}

      <button
        onClick={() => setShowStopList(!showStopList)}
        style={{
          width: '100%', padding: 12, background: c.bg,
          border: `1px solid ${c.border}`, borderRadius: 12, cursor: 'pointer',
          display: 'flex', justifyContent: 'space-between', fontSize: 15, color: c.text,
        }}
      >
        <span>🚫 Стоп-лист ({allStopFoods.length} продуктов)</span>
        <span>{showStopList ? '▲' : '▼'}</span>
      </button>

      {showStopList && (
        <div style={{ marginTop: 8 }}>
          {allStopFoods.map((item, i) => (
            <div key={i} style={{ padding: '8px 14px', borderBottom: `1px solid ${c.border}`, fontSize: 14 }}>
              <b style={{ color: c.text }}>{item.product_name}</b>
              {item.clinical_effect && <div style={{ color: c.hint, fontSize: 12 }}>{item.clinical_effect}</div>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
