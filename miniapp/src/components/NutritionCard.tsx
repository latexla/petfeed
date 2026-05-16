import { Ration } from '../api/nutrition';
import { c } from '../theme';

export function NutritionCard({ ration }: { ration: Ration }) {
  return (
    <div style={{ background: c.bgSecondary, borderRadius: 16, padding: 16, marginBottom: 12 }}>
      <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 8, color: c.text }}>Рацион на сегодня</div>
      <div style={{ fontSize: 22, fontWeight: 700, color: c.text }}>
        🔥 {Math.round(ration.daily_calories)} ккал/день
      </div>
      <div style={{ display: 'flex', gap: 16, marginTop: 10, fontSize: 13, color: c.hint }}>
        <span>🥩 Белки: <b style={{ color: c.text }}>{Math.round(ration.protein_min_g)}г</b></span>
        <span>🫒 Жиры: <b style={{ color: c.text }}>{Math.round(ration.fat_min_g)}г</b></span>
        <span>🍽 {ration.meals_per_day}×/день</span>
      </div>
      {ration.hypoglycemia_warning && (
        <div style={{ marginTop: 8, color: '#ff9500', fontSize: 12 }}>
          ⚠ Риск гипогликемии — следи за приёмами пищи
        </div>
      )}
    </div>
  );
}
