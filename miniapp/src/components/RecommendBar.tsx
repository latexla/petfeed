import { useState } from 'react';
import { FoodSearchResult } from '../api/meal';
import { RecommendResult } from '../api/recommend';
import { c } from '../theme';

interface Props {
  mode: 'natural' | 'commercial';
  setMode: (m: 'natural' | 'commercial') => void;
  selected: string[];
  toggleIngredient: (name: string) => void;
  recentIngredients: string[];
  productName: string;
  setProductName: (v: string) => void;
  result: RecommendResult | null;
  loading: boolean;
  applying: boolean;
  error: string | null;
  recommend: () => void;
  apply: () => void;
  onCancel: () => void;
  onSearchIngredient: (q: string) => void;
  searchResults: FoodSearchResult[];
}

export function RecommendBar({
  mode, setMode, selected, toggleIngredient,
  recentIngredients, productName, setProductName,
  result, loading, applying, error,
  recommend, apply, onCancel,
  onSearchIngredient, searchResults,
}: Props) {
  const [showSearch, setShowSearch] = useState(false);
  const [ingredientQuery, setIngredientQuery] = useState('');

  const modeChip = (active: boolean): React.CSSProperties => ({
    padding: '8px 16px',
    borderRadius: 20,
    border: `1px solid ${active ? c.accent : c.border}`,
    background: active ? c.accent : c.bg,
    color: active ? c.accentText : c.text,
    fontSize: 14,
    fontWeight: active ? 600 : 400,
    cursor: 'pointer',
  });

  const ingredientChipStyle = (name: string): React.CSSProperties => ({
    padding: '6px 12px',
    borderRadius: 16,
    border: `1px solid ${selected.includes(name) ? c.accent : c.border}`,
    background: selected.includes(name) ? `${c.accent}22` : c.bgSecondary,
    color: c.text,
    fontSize: 13,
    cursor: 'pointer',
    flexShrink: 0,
  });

  const inputStyle: React.CSSProperties = {
    width: '100%',
    padding: '10px 12px',
    borderRadius: 10,
    border: `1px solid ${c.border}`,
    fontSize: 14,
    background: c.bg,
    color: c.text,
    outline: 'none',
    boxSizing: 'border-box',
  };

  const primaryBtn = (disabled: boolean): React.CSSProperties => ({
    width: '100%',
    padding: '11px 0',
    background: c.accent,
    color: c.accentText,
    border: 'none',
    borderRadius: 12,
    fontSize: 15,
    fontWeight: 600,
    cursor: disabled ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.5 : 1,
  });

  return (
    <div style={{ marginBottom: 16 }}>
      {/* Mode toggle */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <button style={modeChip(mode === 'natural')} onClick={() => setMode('natural')}>
          🥩 Натуральный
        </button>
        <button style={modeChip(mode === 'commercial')} onClick={() => setMode('commercial')}>
          🛒 Готовый корм
        </button>
      </div>

      {/* Natural mode */}
      {mode === 'natural' && (
        <div>
          {(recentIngredients.length > 0 || !showSearch) && (
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 10 }}>
              {recentIngredients.map((name) => (
                <button key={name} style={ingredientChipStyle(name)} onClick={() => toggleIngredient(name)}>
                  {selected.includes(name) ? '✓ ' : ''}{name}
                </button>
              ))}
              <button
                style={{ ...ingredientChipStyle('__add__'), border: `1px dashed ${c.border}` }}
                onClick={() => setShowSearch(!showSearch)}
              >
                + Найти
              </button>
            </div>
          )}

          {(showSearch || recentIngredients.length === 0) && (
            <div style={{ marginBottom: 10 }}>
              <input
                value={ingredientQuery}
                onChange={(e) => {
                  setIngredientQuery(e.target.value);
                  if (e.target.value.length >= 2) onSearchIngredient(e.target.value);
                }}
                placeholder="🔍 Добавить ингредиент..."
                style={{ ...inputStyle, marginBottom: 4 }}
              />
              {searchResults.length > 0 && (
                <div style={{ background: c.bg, border: `1px solid ${c.border}`, borderRadius: 10, overflow: 'hidden' }}>
                  {searchResults.slice(0, 5).map((r) => (
                    <div
                      key={r.id}
                      onClick={() => {
                        toggleIngredient(r.name);
                        setIngredientQuery('');
                        setShowSearch(false);
                      }}
                      style={{ padding: '8px 12px', borderBottom: `1px solid ${c.border}`, cursor: 'pointer', fontSize: 13, color: c.text }}
                    >
                      {r.name}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {selected.length > 0 && (
            <div style={{ fontSize: 13, color: c.hint, marginBottom: 8 }}>
              Выбрано: {selected.join(', ')}
            </div>
          )}

          <button
            onClick={recommend}
            disabled={selected.length === 0 || loading}
            style={primaryBtn(selected.length === 0 || loading)}
          >
            {loading ? 'Подбираем...' : '✨ Подобрать граммовку'}
          </button>
        </div>
      )}

      {/* Commercial mode */}
      {mode === 'commercial' && (
        <div>
          <input
            value={productName}
            onChange={(e) => {
              setProductName(e.target.value);
              if (e.target.value.length >= 2) onSearchIngredient(e.target.value);
            }}
            placeholder="🔍 Найди корм (Royal Canin, Purina...)"
            style={{ ...inputStyle, marginBottom: 8 }}
          />
          {searchResults.length > 0 && !result && (
            <div style={{ background: c.bg, border: `1px solid ${c.border}`, borderRadius: 10, marginBottom: 8, overflow: 'hidden' }}>
              {searchResults.slice(0, 5).map((r) => (
                <div
                  key={r.id}
                  onClick={() => setProductName(r.name)}
                  style={{ padding: '8px 12px', borderBottom: `1px solid ${c.border}`, cursor: 'pointer', fontSize: 13, color: c.text }}
                >
                  {r.name}
                </div>
              ))}
            </div>
          )}
          <button
            onClick={recommend}
            disabled={!productName.trim() || loading}
            style={primaryBtn(!productName.trim() || loading)}
          >
            {loading ? 'Ищем...' : '✨ Рассчитать граммовку'}
          </button>
        </div>
      )}

      {/* Error */}
      {error && (
        <div style={{ marginTop: 8, color: c.destructive, fontSize: 13 }}>{error}</div>
      )}

      {/* Result */}
      {result && (
        <div style={{ marginTop: 12, background: c.bgSecondary, borderRadius: 14, padding: 14 }}>
          <div style={{ fontWeight: 600, fontSize: 15, color: c.text, marginBottom: 8 }}>
            Рекомендация · покрытие {result.covers_pct}%
          </div>

          {result.items.map((item, i) => (
            <div
              key={i}
              style={{ paddingBottom: 6, marginBottom: 6, borderBottom: `1px solid ${c.border}` }}
            >
              <div style={{ fontSize: 14, color: c.text, fontWeight: 500 }}>{item.name}</div>
              <div style={{ fontSize: 12, color: c.hint, marginTop: 2 }}>
                {item.grams}г · {Math.round(item.kcal)} ккал · Б:{Math.round(item.protein_g)}г Ж:{Math.round(item.fat_g)}г
              </div>
            </div>
          ))}

          {result.deficiencies.map((d, i) => (
            <div key={i} style={{ fontSize: 12, color: '#ff9500', marginTop: 4 }}>💊 {d}</div>
          ))}

          {result.warnings.map((w, i) => (
            <div key={i} style={{ fontSize: 12, color: c.destructive, marginTop: 4 }}>{w}</div>
          ))}

          <button
            onClick={apply}
            disabled={applying}
            style={{ width: '100%', marginTop: 12, padding: '11px 0', background: '#34c759', color: '#fff', border: 'none', borderRadius: 12, fontSize: 15, fontWeight: 600, cursor: applying ? 'not-allowed' : 'pointer', opacity: applying ? 0.6 : 1 }}
          >
            {applying ? 'Добавляем...' : '✅ Применить к дню'}
          </button>

          <button
            onClick={onCancel}
            style={{ width: '100%', marginTop: 6, padding: '8px 0', background: 'none', border: 'none', color: c.hint, fontSize: 13, cursor: 'pointer' }}
          >
            Отмена
          </button>
        </div>
      )}
    </div>
  );
}
