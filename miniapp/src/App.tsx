import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { c } from './theme';
import { PetProvider } from './contexts/PetContext';
import { TabBar } from './components/TabBar';
import { AI } from './pages/AI';
import { Home } from './pages/Home';
import { Nutrition } from './pages/Nutrition';
import { Profile } from './pages/Profile';
import { Reminders } from './pages/Reminders';

function AppRoutes() {
  const { isReady, error } = useAuth();

  if (error) {
    return (
      <div style={{ padding: 24, textAlign: 'center', marginTop: 60 }}>
        <div style={{ fontSize: 40, marginBottom: 12 }}>🐾</div>
        <p style={{ color: c.hint }}>{error}</p>
      </div>
    );
  }

  if (!isReady) {
    return (
      <div style={{ padding: 24, textAlign: 'center', marginTop: 60, color: c.hint }}>
        Загрузка...
      </div>
    );
  }

  return (
    <PetProvider>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/nutrition" element={<Nutrition />} />
        <Route path="/reminders" element={<Reminders />} />
        <Route path="/profile" element={<Profile />} />
        <Route path="/ai" element={<AI />} />
      </Routes>
      <TabBar />
    </PetProvider>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}
