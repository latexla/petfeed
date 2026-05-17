const COLORS = { good: '#34c759', ok: '#ff9500', poor: '#ff3b30' } as const;
const LABELS = { good: 'Отлично', ok: 'Нормально', poor: 'Плохо' } as const;

interface Props {
  score: number;
  quality: 'good' | 'ok' | 'poor';
  size?: 'sm' | 'md';
}

export function QualityBadge({ score, quality, size = 'md' }: Props) {
  const color = COLORS[quality];
  const dotSize = size === 'sm' ? 10 : 12;
  const fontSize = size === 'sm' ? 11 : 13;

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
      <div style={{ width: dotSize, height: dotSize, borderRadius: '50%', background: color, flexShrink: 0 }} />
      <span style={{ fontSize, color, fontWeight: 600 }}>{LABELS[quality]}</span>
      <span style={{ fontSize: fontSize - 1, color: '#8e8e93' }}>{score}/100</span>
    </div>
  );
}
