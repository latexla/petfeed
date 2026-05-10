import { useNavigate } from 'react-router-dom';
import { NutritionCard } from '../components/NutritionCard';
import { PetCard } from '../components/PetCard';
import { usePet } from '../contexts/PetContext';
import { useNutrition } from '../hooks/useNutrition';

export function Home() {
  const { activePet, loading: petLoading, error: petError } = usePet();
  const { ration, loading: rationLoading } = useNutrition(activePet?.id ?? null);
  const navigate = useNavigate();

  if (petLoading) return <div style={{ padding: 24, color: '#999' }}>Загрузка...</div>;
  if (petError) return <div style={{ padding: 24, color: '#ff3b30' }}>{petError}</div>;
  if (!activePet) {
    return (
      <div style={{ padding: 24, textAlign: 'center', marginTop: 40 }}>
        <div style={{ fontSize: 48 }}>🐾</div>
        <p style={{ marginTop: 12, color: '#666' }}>
          Питомец не найден. Создай профиль в боте @PetFeedBot
        </p>
      </div>
    );
  }

  return (
    <div style={{ padding: 16, paddingBottom: 80 }}>
      <PetCard pet={activePet} />
      {rationLoading
        ? <div style={{ color: '#999', fontSize: 14 }}>Загружаю рацион...</div>
        : ration && <NutritionCard ration={ration} />
      }
      {ration?.notes && (
        <div style={{ background: '#f5f5f7', borderRadius: 12, padding: 12, fontSize: 13, color: '#3c3c43', marginBottom: 12 }}>
          {ration.notes}
        </div>
      )}
      <button
        onClick={() => navigate('/ai')}
        style={{
          width: '100%', padding: 14, background: '#007aff', color: '#fff',
          border: 'none', borderRadius: 14, fontSize: 16, fontWeight: 600, cursor: 'pointer',
        }}
      >
        🤖 AI-ассистент
      </button>
    </div>
  );
}
