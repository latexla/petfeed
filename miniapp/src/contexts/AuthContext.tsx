import { ReactNode, createContext, useContext, useEffect, useState } from 'react';
import { authMiniapp } from '../api/auth';
import { tg } from '../telegram';

interface AuthState {
  isReady: boolean;
  error: string | null;
}

const AuthContext = createContext<AuthState>({ isReady: false, error: null });

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ isReady: false, error: null });

  useEffect(() => {
    if (!tg?.initData) {
      const diag = [
        `Telegram obj: ${window.Telegram ? 'yes' : 'NO'}`,
        `WebApp obj: ${window.Telegram?.WebApp ? 'yes' : 'NO'}`,
        `initData len: ${window.Telegram?.WebApp?.initData?.length ?? 'n/a'}`,
      ].join(' | ');
      setState({ isReady: false, error: `Открой через Telegram\n\n[debug] ${diag}` });
      return;
    }
    tg.ready();
    authMiniapp(tg.initData)
      .then(() => setState({ isReady: true, error: null }))
      .catch((err) => {
        const msg =
          err?.response?.status === 403
            ? 'Сначала запусти бота @PetFeedBot, затем открой приложение'
            : 'Закрой и открой приложение заново';
        setState({ isReady: false, error: msg });
      });
  }, []);

  return <AuthContext.Provider value={state}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);
