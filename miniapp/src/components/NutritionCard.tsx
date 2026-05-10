import { Ration } from '../api/nutrition';

export function NutritionCard({ ration }: { ration: Ration }) {
  return (
    <div style={{ background: '#e8f4fd', borderRadius: 16, padding: 16, marginBottom: 12 }}>
      <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 8 }}>Рацион на сегодня</div>
      <div style={{ fontSize: 22, fontWeight: 700 }}>
        🔥 {Math.round(ration.daily_calories)} ккал/день
      </div>
      <div style={{ display: 'flex', gap: 16, marginTop: 10, fontSize: 13, color: '#3c3c43' }}>
        <span>🥩 Белки: <b>{Math.round(ration.protein_min_g)}г</b></span>
        <span>🫒 Жиры: <b>{Math.round(ration.fat_min_g)}г</b></span>
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
