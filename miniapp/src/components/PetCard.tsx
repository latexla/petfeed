import { Pet } from '../api/pets';
import { c } from '../theme';

const SPECIES_EMOJI: Record<string, string> = {
  cat: '🐱', dog: '🐶', rodent: '🐹', bird: '🐦', reptile: '🦎',
};

export function PetCard({ pet }: { pet: Pet }) {
  const emoji = SPECIES_EMOJI[pet.species] ?? '🐾';
  const years = Math.floor(pet.age_months / 12);
  const months = pet.age_months % 12;
  const ageStr = years > 0 ? `${years} л. ${months} мес.` : `${months} мес.`;

  return (
    <div style={{ background: c.bgSecondary, borderRadius: 16, padding: 16, marginBottom: 12 }}>
      <div style={{ fontSize: 36 }}>{emoji}</div>
      <div style={{ fontWeight: 700, fontSize: 20, marginTop: 6, color: c.text }}>{pet.name}</div>
      <div style={{ color: c.hint, fontSize: 14, marginTop: 4 }}>
        {pet.breed ?? pet.species} · {pet.weight_kg} кг · {ageStr}
      </div>
    </div>
  );
}
