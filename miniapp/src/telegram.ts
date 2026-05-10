export interface TelegramWebApp {
  initData: string;
  ready: () => void;
  close: () => void;
  colorScheme: 'light' | 'dark';
}

declare global {
  interface Window {
    Telegram: { WebApp: TelegramWebApp };
  }
}

export const tg: TelegramWebApp | undefined = window.Telegram?.WebApp;
