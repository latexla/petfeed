import { useNavigate } from 'react-router-dom';
import { DailySummary } from '../api/meal';
import { c } from '../theme';
import { ProgressBar } from './ProgressBar';
import { QualityBadge } from './QualityBadge';

interface Props {
  summary: DailySummary | null;
  loading: boolean;
}

export function MealSummaryCard({ summary, loading }: Props) {
  const navigate = useNavigate();
  const kcalTarget = summary?.daily_target?.kcal ?? 0;
  const kcalActual = summary?.totals?.kcal ?? 0;

  return (
    <div
      onClick={() => navigate('/meal')}
      style={{ background: c.bgSecondary, borderRadius: 16, padding: 16, marginBottom: 12, cursor: 'pointer' }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
        <span style={{ fontWeight: 600, fontSize: 15, color: c.text }}>🍖 Питание сегодня</span>
        {summary && summary.items.length > 0 && (
          <QualityBadge score={summary.quality_score} quality={summary.quality_label} size="sm" />
        )}
      </div>
      {loading ? (
        <div style={{ color: c.hint, fontSize: 13 }}>Загрузка...</div>
      ) : (
        <>
          <div style={{ fontSize: 13, color: c.hint, marginBottom: 6 }}>
            {Math.round(kcalActual)} / {Math.round(kcalTarget)} ккал
          </div>
          <ProgressBar value={kcalActual} target={kcalTarget} />
          {summary?.tips && summary.tips.length > 0 && kcalActual > 0 && (
            <div style={{ fontSize: 11, color: c.hint, marginTop: 6 }}>
              💡 {summary.tips[0]}
            </div>
          )}
        </>
      )}
    </div>
  );
}
