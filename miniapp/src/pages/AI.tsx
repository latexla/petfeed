import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AIResponse, askAI } from '../api/ai';
import { usePet } from '../contexts/PetContext';

interface Message { id: number; role: 'user' | 'assistant'; text: string; }

const DAILY_LIMIT = 10;

export function AI() {
  const { activePet } = usePet();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [requestsLeft, setRequestsLeft] = useState(DAILY_LIMIT);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const bottomRef = useRef<HTMLDivElement>(null);
  const msgId = useRef(0);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const send = async () => {
    const question = input.trim();
    if (!question || !activePet || loading) return;

    setInput('');
    setMessages((prev) => [...prev, { id: msgId.current++, role: 'user', text: question }]);
    setLoading(true);

    try {
      const res: AIResponse = await askAI(activePet.id, question);
      setMessages((prev) => [...prev, { id: msgId.current++, role: 'assistant', text: res.answer }]);
      setRequestsLeft(res.requests_left);
    } catch (err: unknown) {
      const isAxiosError = err !== null && typeof err === 'object' && 'response' in err;
      const status = isAxiosError ? (err as { response?: { status?: number } }).response?.status : undefined;
      const reply =
        status === 429
          ? `Лимит ${DAILY_LIMIT} запросов/день исчерпан. Возвращайся завтра!`
          : 'Что-то пошло не так, попробуй ещё раз.';
      setMessages((prev) => [...prev, { id: msgId.current++, role: 'assistant', text: reply }]);
      if (status === 429) setRequestsLeft(0);
    } finally {
      setLoading(false);
    }
  };

  const atLimit = requestsLeft === 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100dvh' }}>
      <div style={{
        display: 'flex', alignItems: 'center', padding: '12px 16px',
        borderBottom: '1px solid #e5e5e5', background: '#fff',
      }}>
        <button
          onClick={() => navigate(-1)}
          style={{ background: 'none', border: 'none', fontSize: 22, cursor: 'pointer', padding: '0 8px 0 0' }}
        >
          ‹
        </button>
        <span style={{ fontWeight: 600, fontSize: 17, flex: 1 }}>AI-ассистент</span>
        <span style={{ fontSize: 12, color: requestsLeft > 3 ? '#34c759' : '#ff9500' }}>
          {requestsLeft}/{DAILY_LIMIT}
        </span>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '16px', background: '#f5f5f7' }}>
        {messages.length === 0 && (
          <div style={{ textAlign: 'center', color: '#8e8e93', marginTop: 40 }}>
            <div style={{ fontSize: 48, marginBottom: 12 }}>🤖</div>
            <p>Задай вопрос о питании {activePet?.name ?? 'питомца'}</p>
            <p style={{ fontSize: 12, marginTop: 8 }}>Например: «Можно ли давать курицу каждый день?»</p>
          </div>
        )}
        {messages.map((m) => (
          <div
            key={m.id}
            style={{
              display: 'flex',
              justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start',
              marginBottom: 10,
            }}
          >
            <div style={{
              maxWidth: '80%', padding: '10px 14px', borderRadius: 16,
              background: m.role === 'user' ? '#007aff' : '#fff',
              color: m.role === 'user' ? '#fff' : '#000',
              fontSize: 15, lineHeight: 1.5,
              boxShadow: '0 1px 2px rgba(0,0,0,.08)',
            }}>
              {m.text}
            </div>
          </div>
        ))}
        {loading && (
          <div style={{ color: '#8e8e93', fontSize: 14 }}>Думаю...</div>
        )}
        <div ref={bottomRef} />
      </div>

      <div style={{
        padding: '10px 16px', background: '#fff', borderTop: '1px solid #e5e5e5',
        display: 'flex', gap: 10, alignItems: 'center',
      }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && send()}
          placeholder={atLimit ? 'Лимит исчерпан' : 'Спроси про питание...'}
          disabled={atLimit || loading}
          style={{
            flex: 1, padding: '10px 14px', borderRadius: 20,
            border: '1px solid #ddd', fontSize: 15, outline: 'none',
            background: atLimit ? '#f5f5f7' : '#fff',
          }}
        />
        <button
          onClick={send}
          disabled={atLimit || loading || !input.trim()}
          style={{
            width: 44, height: 44, borderRadius: 22, background: '#007aff',
            color: '#fff', border: 'none', cursor: 'pointer', fontSize: 20,
            opacity: atLimit || loading || !input.trim() ? 0.4 : 1,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}
        >
          ↑
        </button>
      </div>
    </div>
  );
}
