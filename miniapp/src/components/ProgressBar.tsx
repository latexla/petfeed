import { c } from '../theme';

interface Props {
  value: number;
  target: number;
  color?: string;
  height?: number;
}

export function ProgressBar({ value, target, color, height = 8 }: Props) {
  const pct = target > 0 ? Math.min(130, (value / target) * 100) : 0;
  const barColor = color ?? (
    pct >= 90 && pct <= 110 ? '#34c759' :
    pct < 70 || pct > 130 ? '#ff3b30' : '#ff9500'
  );
  const displayPct = Math.min(100, pct);

  return (
    <div style={{ background: c.bgSecondary, borderRadius: height, height, overflow: 'hidden', width: '100%' }}>
      <div style={{
        width: `${displayPct}%`, height: '100%',
        background: barColor, borderRadius: height,
        transition: 'width 0.3s ease',
      }} />
    </div>
  );
}
