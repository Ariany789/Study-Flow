import { useEffect, useMemo, useState } from 'react';
import type { FormEvent } from 'react';
import { Bell, CalendarDays, Check, ChevronLeft, ChevronRight, Clock3, Settings, Trash2, UserRound } from 'lucide-react';
import { request } from './api';

type CalendarEvent = { id: string; title: string; event_type: string; date: string; status?: string | null };
type NotificationItem = { id: string; title: string; message: string; kind: string; read_at: string | null; created_at: string };
export type AccountUser = { id: string; name: string; email: string; theme: string; notifications_enabled: boolean; weekly_study_goal_minutes: number };

function localDateKey(value: string | Date) {
  const date = value instanceof Date ? value : new Date(value);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

function eventLabel(type: string) {
  return type === 'TASK' ? 'Tarefa' : type === 'GOAL' ? 'Meta' : 'Sessão de estudo';
}

export function CalendarPage({ token }: { token: string }) {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [month, setMonth] = useState(() => new Date(new Date().getFullYear(), new Date().getMonth(), 1));
  const [selectedDay, setSelectedDay] = useState(() => localDateKey(new Date()));
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    request('/calendar', token).then(async response => {
      if (!response.ok) throw new Error('Não foi possível carregar o calendário.');
      setEvents(await response.json());
      setError('');
    }).catch(() => setError('Não foi possível carregar o calendário. Tente atualizar a página.'))
      .finally(() => setLoading(false));
  }, [token]);

  const byDay = useMemo(() => events.reduce<Record<string, CalendarEvent[]>>((grouped, event) => {
    const key = localDateKey(event.date);
    (grouped[key] ||= []).push(event);
    return grouped;
  }, {}), [events]);
  const firstWeekday = (month.getDay() + 6) % 7;
  const days = Array.from({ length: 42 }, (_, index) => new Date(month.getFullYear(), month.getMonth(), index - firstWeekday + 1));
  const selectedEvents = byDay[selectedDay] || [];
  const monthTitle = month.toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' });
  const weekdays = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'];

  function changeMonth(offset: number) {
    const next = new Date(month.getFullYear(), month.getMonth() + offset, 1);
    setMonth(next);
    setSelectedDay(localDateKey(next));
  }

  return <section className="content calendar-page">
    <div className="tasks-heading"><div><p className="eyebrow">PRAZOS E PLANEJAMENTO</p><h2>Calendário</h2><p className="subtle">Veja os prazos das tarefas e metas e os dias em que estudou.</p></div></div>
    {error && <p className="feedback failure">{error}</p>}
    <div className="calendar-layout">
      <section className="calendar-panel" aria-label="Calendário mensal">
        <div className="calendar-toolbar"><button className="icon-action" onClick={() => changeMonth(-1)} aria-label="Mês anterior"><ChevronLeft size={19}/></button><h3>{monthTitle}</h3><button className="icon-action" onClick={() => changeMonth(1)} aria-label="Próximo mês"><ChevronRight size={19}/></button><button className="secondary calendar-today" onClick={() => { const today = new Date(); setMonth(new Date(today.getFullYear(), today.getMonth(), 1)); setSelectedDay(localDateKey(today)); }}>Hoje</button></div>
        <div className="calendar-grid weekday-row">{weekdays.map(day => <span key={day}>{day}</span>)}</div>
        <div className="calendar-grid">{days.map(day => {
          const key = localDateKey(day); const count = byDay[key]?.length || 0;
          return <button key={key} className={`calendar-day ${day.getMonth() !== month.getMonth() ? 'outside' : ''} ${key === selectedDay ? 'selected' : ''} ${key === localDateKey(new Date()) ? 'today' : ''}`} onClick={() => { setSelectedDay(key); if (day.getMonth() !== month.getMonth()) setMonth(new Date(day.getFullYear(), day.getMonth(), 1)); }} aria-label={`${day.toLocaleDateString('pt-BR')}, ${count} compromissos`}>
            <span>{day.getDate()}</span>{count > 0 && <i>{count}</i>}
          </button>;
        })}</div>
      </section>
      <section className="agenda-panel"><div className="section-heading"><div><p className="eyebrow">AGENDA DO DIA</p><h3>{new Date(`${selectedDay}T12:00:00`).toLocaleDateString('pt-BR', { day: 'numeric', month: 'long' })}</h3></div><span className="count">{selectedEvents.length} itens</span></div>
        {loading ? <div className="loading-state">Carregando compromissos...</div> : selectedEvents.length ? <div className="task-list">{selectedEvents.map(event => <article className="agenda-item" key={`${event.event_type}-${event.id}`}><span className={`agenda-type ${event.event_type.toLowerCase()}`}><CalendarDays size={16}/></span><div><strong>{event.title}</strong><small>{eventLabel(event.event_type)}{event.status ? ` · ${event.status === 'COMPLETED' ? 'Concluído' : 'Em aberto'}` : ''}</small></div></article>)}</div> : <div className="empty">Sem compromissos neste dia.<br/><span>Os prazos e sessões aparecem aqui.</span></div>}
      </section>
    </div>
  </section>;
}

export function NotificationsPage({ token }: { token: string }) {
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  async function load() {
    setLoading(true);
    try { const response = await request('/notifications', token); if (!response.ok) throw new Error(); setItems(await response.json()); setError(''); }
    catch { setError('Não foi possível carregar os avisos.'); }
    finally { setLoading(false); }
  }
  useEffect(() => { void load(); }, [token]);
  async function markRead(id: string) {
    const response = await request(`/notifications/${id}/read`, token, { method: 'PATCH' });
    if (response.ok) setItems(current => current.map(item => item.id === id ? { ...item, read_at: new Date().toISOString() } : item));
    else setError('Não foi possível marcar o aviso como lido.');
  }
  const unread = items.filter(item => !item.read_at).length;
  return <section className="content notifications-page"><div className="tasks-heading"><div><p className="eyebrow">LEMBRETES DO STUDYFLOW</p><h2>Avisos</h2><p className="subtle">Acompanhe prazos próximos e vencidos.</p></div><button className="secondary" onClick={() => void load()}>Atualizar</button></div>
    {error && <p className="feedback failure">{error}</p>}{!loading && <p className="notification-summary">{unread ? `${unread} aviso${unread === 1 ? '' : 's'} não lido${unread === 1 ? '' : 's'}` : 'Tudo em dia'}</p>}
    {loading ? <div className="loading-state">Carregando avisos...</div> : items.length ? <div className="task-list">{items.map(item => <article className={`notification-item ${item.read_at ? 'read' : 'unread'}`} key={item.id}><span className="notification-icon"><Bell size={18}/></span><div className="notification-copy"><strong>{item.title}</strong><p>{item.message}</p><small>{new Date(item.created_at).toLocaleString('pt-BR')}</small></div>{!item.read_at && <button className="secondary mark-read" onClick={() => void markRead(item.id)}><Check size={15}/> Marcar como lido</button>}</article>)}</div> : <div className="empty">Nenhum aviso por enquanto.<br/><span>Quando uma tarefa ou meta estiver perto do prazo, o lembrete aparecerá aqui.</span></div>}
  </section>;
}

export function SettingsPage({ token, user, onUserUpdate, onAccountDeleted }: { token: string; user: AccountUser; onUserUpdate: (user: AccountUser) => void; onAccountDeleted: () => void }) {
  const [name, setName] = useState(user.name);
  const [email, setEmail] = useState(user.email);
  const [theme, setTheme] = useState(user.theme || 'light');
  const [notificationsEnabled, setNotificationsEnabled] = useState(user.notifications_enabled);
  const [weeklyGoalMinutes, setWeeklyGoalMinutes] = useState(user.weekly_study_goal_minutes || 300);
  const [profileMessage, setProfileMessage] = useState('');
  const [profileError, setProfileError] = useState('');
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [securityMessage, setSecurityMessage] = useState('');
  const [securityError, setSecurityError] = useState('');
  useEffect(() => { setName(user.name); setEmail(user.email); setTheme(user.theme || 'light'); setNotificationsEnabled(user.notifications_enabled); setWeeklyGoalMinutes(user.weekly_study_goal_minutes || 300); }, [user]);

  async function saveProfile(event: FormEvent) {
    event.preventDefault(); setProfileError(''); setProfileMessage('');
    const response = await request('/users/me', token, { method: 'PATCH', body: JSON.stringify({ name, email, theme, notifications_enabled: notificationsEnabled, weekly_study_goal_minutes: weeklyGoalMinutes }) });
    if (!response.ok) { const body = await response.json().catch(() => null); setProfileError(body?.detail || 'Não foi possível salvar suas preferências.'); return; }
    const updated = await response.json(); onUserUpdate(updated); setProfileMessage('Dados e preferências salvos.');
  }

  async function changePassword(event: FormEvent) {
    event.preventDefault(); setSecurityError(''); setSecurityMessage('');
    if (newPassword !== confirmPassword) { setSecurityError('A confirmação da nova senha não confere.'); return; }
    const response = await request('/users/me/password', token, { method: 'POST', body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }) });
    if (!response.ok) { const body = await response.json().catch(() => null); setSecurityError(body?.detail || 'Não foi possível alterar a senha.'); return; }
    setCurrentPassword(''); setNewPassword(''); setConfirmPassword(''); setSecurityMessage('Senha alterada com sucesso.');
  }

  async function deleteAccount() {
    if (!window.confirm('Excluir sua conta e todos os dados do StudyFlow? Esta ação não pode ser desfeita.')) return;
    const response = await request('/users/me', token, { method: 'DELETE' });
    if (response.ok) onAccountDeleted(); else setSecurityError('Não foi possível excluir a conta.');
  }

  return <section className="content settings-page"><div className="tasks-heading"><div><p className="eyebrow">PREFERÊNCIAS E SEGURANÇA</p><h2>Conta e preferências</h2><p className="subtle">Atualize seus dados, escolha a aparência e cuide da segurança da conta.</p></div></div>
    <div className="settings-grid"><form className="settings-card" onSubmit={saveProfile}><div className="settings-title"><UserRound size={19}/><div><h3>Seus dados</h3><p>Nome, email e preferências pessoais.</p></div></div>
      <label>Nome<input value={name} onChange={event => setName(event.target.value)} required minLength={2} maxLength={120}/></label><label>Email<input type="email" value={email} onChange={event => setEmail(event.target.value)} required/></label>
      <label>Tema<select value={theme} onChange={event => setTheme(event.target.value)}><option value="light">Claro</option><option value="dark">Escuro</option><option value="system">Igual ao dispositivo</option></select></label>
      <label>Meta semanal de estudo (minutos)<input type="number" min="30" max="4200" step="15" value={weeklyGoalMinutes} onChange={event => setWeeklyGoalMinutes(Number(event.target.value))} required/><small>Tempo estudado de segunda a domingo. Padrão: 300 minutos (5 horas).</small></label>
      <label className="check-setting"><input type="checkbox" checked={notificationsEnabled} onChange={event => setNotificationsEnabled(event.target.checked)}/> Receber avisos de prazos</label>
      {profileError && <p className="feedback failure">{profileError}</p>}{profileMessage && <p className="feedback success">{profileMessage}</p>}<button className="primary">Salvar preferências</button>
    </form>
    <form className="settings-card" onSubmit={changePassword}><div className="settings-title"><Settings size={19}/><div><h3>Segurança</h3><p>Use uma senha com pelo menos 8 caracteres.</p></div></div>
      <label>Senha atual<input type="password" value={currentPassword} onChange={event => setCurrentPassword(event.target.value)} required minLength={8} autoComplete="current-password"/></label><label>Nova senha<input type="password" value={newPassword} onChange={event => setNewPassword(event.target.value)} required minLength={8} autoComplete="new-password"/></label><label>Confirme a nova senha<input type="password" value={confirmPassword} onChange={event => setConfirmPassword(event.target.value)} required minLength={8} autoComplete="new-password"/></label>
      {securityError && <p className="feedback failure">{securityError}</p>}{securityMessage && <p className="feedback success">{securityMessage}</p>}<button className="primary">Alterar senha</button><hr/><h3 className="danger-title">Excluir conta</h3><p className="subtle">A exclusão remove seus dados e não pode ser desfeita.</p><button type="button" className="danger-button" onClick={() => void deleteAccount()}>Excluir minha conta</button>
    </form></div>
  </section>;
}

export function RecentActivity({ token }: { token: string }) {
  const [items, setItems] = useState<{ id: string; title: string; event_type: string; date: string }[]>([]);
  const [error, setError] = useState('');
  const [deleting, setDeleting] = useState<string | null>(null);
  async function load() {
    const response = await request('/history', token);
    if (!response.ok) throw new Error('Não foi possível carregar a atividade recente.');
    setItems((await response.json()).slice(0, 5));
  }
  useEffect(() => { void load().catch(() => setError('Não foi possível carregar a atividade recente.')); }, [token]);
  async function remove(item: { id: string; title: string; event_type: string }) {
    if (!window.confirm('Excluir "' + item.title + '" do histórico?')) return;
    const endpoint = item.event_type === 'TASK_COMPLETED' ? '/tasks/' : item.event_type === 'GOAL_COMPLETED' ? '/goals/' : '/study-sessions/';
    setDeleting(item.id); setError('');
    try {
      const response = await request(endpoint + item.id, token, { method: 'DELETE' });
      if (!response.ok) throw new Error();
      await load();
      window.dispatchEvent(new CustomEvent('studyflow-data-changed'));
    } catch { setError('Não foi possível excluir este registro.'); }
    finally { setDeleting(null); }
  }
  return <section className="content recent-activity"><div className="section-heading"><div><p className="eyebrow">SEU PROGRESSO</p><h2>Atividade recente</h2></div><span className="count">Últimos registros</span></div>
    {error && <p className="feedback failure">{error}</p>}{items.length ? <div className="task-list">{items.map(item => <article className="agenda-item" key={`${item.event_type}-${item.id}`}><span className="agenda-type"><Clock3 size={16}/></span><div><strong>{item.title}</strong><small>{item.event_type === 'TASK_COMPLETED' ? 'Tarefa concluída' : item.event_type === 'GOAL_COMPLETED' ? 'Meta concluída' : 'Sessão de estudo'} · {new Date(item.date).toLocaleDateString('pt-BR')}</small></div><button className="icon-action delete" type="button" onClick={() => void remove(item)} disabled={deleting === item.id} aria-label="Excluir atividade" title="Excluir atividade"><Trash2 size={16}/></button></article>)}</div> : <div className="empty">Suas tarefas concluídas, metas alcançadas e sessões finalizadas aparecerão aqui.</div>}
  </section>;
}
