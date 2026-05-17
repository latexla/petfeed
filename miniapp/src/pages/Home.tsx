import { useNavigate } from 'react-router-dom';
import { NutritionCard } from '../components/NutritionCard';
import { PetCard } from '../components/PetCard';
import { MealSummaryCard } from '../components/MealSummaryCard';
import { WeightCard } from '../components/WeightCard';
import { usePet } from '../contexts/PetContext';
import { useNutrition } from '../hooks/useNutrition';
import { useMealSession } from '../hooks/useMealSession';
import { useWeightHistory } from '../hooks/useWeightHistory';
import { c } from '../theme';

export function Home() {
  const { activePet, loading: petLoading, error: petError } = usePet();
  const { ration, loading: rationLoading } = useNutrition(activePet?.id ?? null);
  const { summary: mealSummary, loading: mealLoading } = useMealSession(
    activePet?.id ?? null,
    activePet?.species ?? null,
  );
  const { history: weightHistory, loading: weightLoading } = useWeightHistory(activePet?.id ?? null);
  const navigate = useNavigate();

  if (petLoading) return <div style={{ padding: 24, color: c.hint }}>Загрузка...</div>;
  if (petError) return <div style={{ padding: 24, color: c.destructive }}>{petError}</div>;
  if (!activePet) {
    return (
      <div style={{ padding: 24, textAlign: 'center', marginTop: 40 }}>
        <div style={{ fontSize: 48 }}>🐾</div>
        <p style={{ marginTop: 12, color: c.hint }}>
          Питомец не найден. Создай профиль в боте @PetFeedBot
        </p>
      </div>
    );
  }

  return (
    <div style={{ padding: 16, paddingBottom: 80 }}>
      <PetCard pet={activePet} />
      {rationLoading
        ? <div style={{ color: c.hint, fontSize: 14 }}>Загружаю рацион...</div>
        : ration && <NutritionCard ration={ration} />
      }
      {ration?.notes && (
        <div style={{ background: c.bgSecondary, borderRadius: 12, padding: 12, fontSize: 13, color: c.hint, marginBottom: 12 }}>
          {ration.notes}
        </div>
      )}

      <MealSummaryCard summary={mealSummary} loading={mealLoading} />
      <WeightCard history={weightHistory} loading={weightLoading} />

      <button
        onClick={() => navigate('/ai')}
        style={{
          width: '100%', padding: 14, background: c.accent, color: c.accentText,
          border: 'none', borderRadius: 14, fontSize: 16, fontWeight: 600, cursor: 'pointer',
        }}
      >
        🤖 AI-ассистент
      </button>
    </div>
  );
}
