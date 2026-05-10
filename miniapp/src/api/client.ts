import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL as string;

let accessToken: string | null = null;
let isRefreshing = false;

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

const client = axios.create({ baseURL: BASE_URL, withCredentials: true });

client.interceptors.request.use((config) => {
  if (accessToken) config.headers.Authorization = `Bearer ${accessToken}`;
  return config;
});

client.interceptors.response.use(
  (r) => r,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry && !isRefreshing) {
      original._retry = true;
      isRefreshing = true;
      try {
        const { data } = await axios.post(
          `${BASE_URL}/v1/auth/refresh`,
          {},
          { withCredentials: true },
        );
        setAccessToken(data.access_token);
        original.headers.Authorization = `Bearer ${data.access_token}`;
        return client(original);
      } catch {
        setAccessToken(null);
      } finally {
        isRefreshing = false;
      }
    }
    return Promise.reject(error);
  },
);

export default client;
