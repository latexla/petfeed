import { Pet } from '../api/pets';

const SPECIES_EMOJI: Record<string, string> = {
  cat: '🐱', dog: '🐶', rodent: '🐹', bird: '🐦', reptile: '🦎',
};

export function PetCard({ pet }: { pet: Pet }) {
  const emoji = SPECIES_EMOJI[pet.species] ?? '🐾';
  const years = Math.floor(pet.age_months / 12);
  const months = pet.age_months % 12;
  const ageStr = years > 0 ? `${years} л. ${months} мес.` : `${months} мес.`;

  return (
    <div style={{ background: '#f5f5f7', borderRadius: 16, padding: 16, marginBottom: 12 }}>
      <div style={{ fontSize: 36 }}>{emoji}</div>
      <div style={{ fontWeight: 700, fontSize: 20, marginTop: 6 }}>{pet.name}</div>
      <div style={{ color: '#6e6e73', fontSize: 14, marginTop: 4 }}>
        {pet.breed ?? pet.species} · {pet.weight_kg} кг · {ageStr}
      </div>
    </div>
  );
}
