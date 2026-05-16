import { usePet } from '../contexts/PetContext';
import { c } from '../theme';

const SPECIES_EMOJI: Record<string, string> = {
  cat: '🐱', dog: '🐶', rodent: '🐹', bird: '🐦', reptile: '🦎',
};
const GOAL_LABELS: Record<string, string> = {
  maintain: 'Поддержание веса', lose: 'Похудение', gain: 'Набор веса', growth: 'Рост',
};

const BOT_USERNAME = (import.meta.env.VITE_BOT_USERNAME as string | undefined) ?? 'PetFeedBot';

export function Profile() {
  const { pets, activePet, setActivePet, loading } = usePet();

  if (loading) return <div style={{ padding: 24, color: c.hint }}>Загрузка...</div>;
  if (!activePet) return <div style={{ padding: 24, color: c.hint }}>Питомец не найден</div>;

  const emoji = SPECIES_EMOJI[activePet.species] ?? '🐾';
  const years = Math.floor(activePet.age_months / 12);
  const months = activePet.age_months % 12;
  const ageStr = years > 0 ? `${years} л. ${months} мес.` : `${months} мес.`;

  return (
    <div style={{ padding: 16, paddingBottom: 80 }}>
      <h2 style={{ marginBottom: 16, color: c.text }}>Профиль</h2>

      <div style={{ background: c.bgSecondary, borderRadius: 16, padding: 16, marginBottom: 16 }}>
        <div style={{ fontSize: 40 }}>{emoji}</div>
        <div style={{ fontWeight: 700, fontSize: 20, marginTop: 8, color: c.text }}>{activePet.name}</div>
        <div style={{ color: c.hint, fontSize: 14, marginTop: 4, lineHeight: 1.6 }}>
          <div>Порода: {activePet.breed ?? 'Метис'}</div>
          <div>Вес: {activePet.weight_kg} кг</div>
          <div>Возраст: {ageStr}</div>
          <div>Цель: {GOAL_LABELS[activePet.goal] ?? activePet.goal}</div>
        </div>
        <a
          href={`https://t.me/${BOT_USERNAME}`}
          target="_blank"
          rel="noreferrer"
          style={{ display: 'inline-block', marginTop: 10, color: c.link, fontSize: 14 }}
        >
          Изменить в боте →
        </a>
      </div>

      {pets.length > 1 && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontWeight: 600, marginBottom: 8, fontSize: 15, color: c.text }}>Мои питомцы</div>
          {pets.map((p) => (
            <button
              key={p.id}
              onClick={() => setActivePet(p)}
              style={{
                display: 'block', width: '100%', textAlign: 'left',
                padding: '12px 16px', marginBottom: 6,
                background: c.bgSecondary,
                border: p.id === activePet.id ? `1.5px solid ${c.accent}` : '1.5px solid transparent',
                borderRadius: 12, cursor: 'pointer', fontSize: 15, color: c.text,
              }}
            >
              {SPECIES_EMOJI[p.species] ?? '🐾'} {p.name}
            </button>
          ))}
        </div>
      )}

      <a
        href={`https://t.me/${BOT_USERNAME}?start=feedback`}
        target="_blank"
        rel="noreferrer"
        style={{
          display: 'block', width: '100%', padding: 14, textAlign: 'center',
          background: c.bg, border: `1.5px solid ${c.accent}`, color: c.accent,
          borderRadius: 14, fontSize: 15, fontWeight: 600, textDecoration: 'none',
        }}
      >
        💬 Оставить отзыв
      </a>
    </div>
  );
}
