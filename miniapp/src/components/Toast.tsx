import { useEffect, useState } from 'react';

interface Props { message: string; onDone: () => void; }

export function Toast({ message, onDone }: Props) {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const t = setTimeout(() => { setVisible(false); onDone(); }, 3000);
    return () => clearTimeout(t);
  }, [onDone]);

  if (!visible) return null;

  return (
    <div style={{
      position: 'fixed', bottom: 72, left: '50%', transform: 'translateX(-50%)',
      background: '#1c1c1e', color: '#fff', padding: '10px 20px',
      borderRadius: 20, zIndex: 200, fontSize: 14, whiteSpace: 'nowrap',
    }}>
      {message}
    </div>
  );
}
