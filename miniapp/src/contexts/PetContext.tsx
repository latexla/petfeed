import { ReactNode, createContext, useCallback, useContext, useEffect, useState } from 'react';
import { Pet, getPets } from '../api/pets';

interface PetState {
  pets: Pet[];
  activePet: Pet | null;
  setActivePet: (pet: Pet) => void;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

const PetContext = createContext<PetState>({
  pets: [], activePet: null, setActivePet: () => {}, loading: true, error: null, reload: () => {},
});

export function PetProvider({ children }: { children: ReactNode }) {
  const [pets, setPets] = useState<Pet[]>([]);
  const [activePet, setActivePet] = useState<Pet | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    getPets()
      .then((data) => { setPets(data); setActivePet(data[0] ?? null); })
      .catch(() => setError('Не удалось загрузить питомца'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  return (
    <PetContext.Provider value={{ pets, activePet, setActivePet, loading, error, reload: load }}>
      {children}
    </PetContext.Provider>
  );
}

export const usePet = () => useContext(PetContext);
