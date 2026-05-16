import { useLocation, useNavigate } from 'react-router-dom';
import { c } from '../theme';

const TABS = [
  { path: '/', label: 'Главная', icon: '🏠' },
  { path: '/nutrition', label: 'Рацион', icon: '🍽' },
  { path: '/reminders', label: 'Напоминания', icon: '⏰' },
  { path: '/profile', label: 'Профиль', icon: '👤' },
];

export function TabBar() {
  const location = useLocation();
  const navigate = useNavigate();

  if (location.pathname === '/ai') return null;

  return (
    <nav style={{
      position: 'fixed', bottom: 0, left: 0, right: 0,
      display: 'flex', background: c.bg,
      borderTop: `1px solid ${c.border}`, zIndex: 100,
    }}>
      {TABS.map((tab) => {
        const active = location.pathname === tab.path;
        return (
          <button
            key={tab.path}
            onClick={() => navigate(tab.path)}
            style={{
              flex: 1, padding: '8px 0', border: 'none', background: 'none',
              color: active ? c.accent : c.hint,
              display: 'flex', flexDirection: 'column', alignItems: 'center',
              gap: 2, fontSize: 10, cursor: 'pointer',
            }}
          >
            <span style={{ fontSize: 22 }}>{tab.icon}</span>
            {tab.label}
          </button>
        );
      })}
    </nav>
  );
}
