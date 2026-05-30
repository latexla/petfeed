import type { ReactNode } from 'react';
import { c } from '../theme';

export function Privacy() {
  return (
    <div style={{ padding: 24, paddingBottom: 40, maxWidth: 600, margin: '0 auto' }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 8, color: c.text }}>
        Политика конфиденциальности
      </h1>
      <p style={{ fontSize: 12, color: c.hint, marginBottom: 24 }}>
        Последнее обновление: 30 мая 2026 г.
      </p>

      <Section title="Какие данные мы собираем">
        <p>При использовании PetFeed мы собираем:</p>
        <ul>
          <li>Telegram ID пользователя (для идентификации аккаунта)</li>
          <li>Данные о питомце, которые вы вводите сами: вид, порода, возраст, вес, цель питания, имя</li>
          <li>Записи о кормлениях и изменениях веса, которые вы добавляете</li>
          <li>Вопросы к AI-ассистенту</li>
        </ul>
      </Section>

      <Section title="Зачем мы это собираем">
        <p>
          Данные используются исключительно для работы сервиса: расчёта рациона,
          отправки напоминаний о кормлении и персонализации рекомендаций.
        </p>
      </Section>

      <Section title="Как хранятся данные">
        <p>
          Данные хранятся в защищённой базе данных на серверах Railway (ЕС/США).
          Передача данных на сервер осуществляется по зашифрованному каналу (HTTPS).
        </p>
      </Section>

      <Section title="Передача третьим лицам">
        <p>
          Мы не продаём и не передаём ваши данные третьим лицам.
          Вопросы к AI-ассистенту обрабатываются сервисом DeepSeek API согласно их
          политике конфиденциальности.
        </p>
      </Section>

      <Section title="Удаление данных">
        <p>
          Чтобы удалить все свои данные, напишите нам:{' '}
          <a href="mailto:latyshevalex361@gmail.com" style={{ color: c.accent }}>
            latyshevalex361@gmail.com
          </a>
        </p>
      </Section>

      <Section title="Контакт">
        <p>
          По вопросам конфиденциальности:{' '}
          <a href="mailto:latyshevalex361@gmail.com" style={{ color: c.accent }}>
            latyshevalex361@gmail.com
          </a>
        </p>
      </Section>
    </div>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div style={{ marginBottom: 24 }}>
      <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 8, color: '#333' }}>
        {title}
      </h2>
      <div style={{ fontSize: 14, lineHeight: 1.7, color: '#555' }}>
        {children}
      </div>
    </div>
  );
}
