import axios from 'axios';
import { setAccessToken } from './client';

const BASE_URL: string = import.meta.env.VITE_API_URL ?? '';

export async function authMiniapp(initData: string): Promise<void> {
  const { data } = await axios.post(
    `${BASE_URL}/v1/auth/miniapp`,
    { init_data: initData },
    { withCredentials: true },
  );
  if (!data.access_token) throw new Error('Invalid auth response: missing access_token');
  setAccessToken(data.access_token);
}

export async function logoutApi(): Promise<void> {
  await axios.post(`${BASE_URL}/v1/auth/logout`, {}, { withCredentials: true });
  setAccessToken(null);
}
