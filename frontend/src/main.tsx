import { StrictMode, useEffect, useState } from 'react';
import type { FormEvent, ReactNode } from 'react';
import { createRoot } from 'react-dom/client';
import { Bell, BookOpen, CalendarDays, CheckCircle2, Circle, Clock3, History, LayoutDashboard, LoaderCircle, LogOut, Moon, Pencil, Plus, RefreshCw, Settings, Sparkles, Sun, Target, Timer, Trash2 } from 'lucide-react';
import './styles.css';
import './theme.css';
import { request, publicRequest } from './api';
import { CalendarPage, NotificationsPage, RecentActivity, SettingsPage, type AccountUser } from './WorkspaceViews';

type Task = { id: string; title: string; description?: string; status: string; priority: string; due_date?: string };
type TaskPage = { items: Task[]; page: number; page_size: number; total: number; pages: number };
type Goal = { id: string; title: string; progress: number; target: number; status: string };
type Subject = { id: string; name: string; color: string };
type Dashboard = { pending_tasks: number; completed_tasks: number; overdue_tasks: number; active_goals: number; studied_minutes: number; week_study_seconds: number; weekly_study_goal_minutes: number };
type User = AccountUser;
function normalizeTaskPage(value: any): TaskPage { return Array.isArray(value) ? { items: value, page: 1, page_size: value.length || 8, total: value.length, pages: 1 } : { items: value?.items || [], page: value?.page || 1, page_size: value?.page_size || 8, total: value?.total || 0, pages: value?.pages || 1 }; }
function RefreshButton({ onRefresh, loading }: { onRefresh: () => void | Promise<void>; loading: boolean }) { return <button className={`refresh-button ${loading ? 'is-loading' : ''}`} onClick={onRefresh} disabled={loading} aria-label="Atualizar dados" title="Atualizar dados"><RefreshCw size={17}/><span className="sr-only">{loading ? 'Atualizando dados' : 'Atualizar dados'}</span></button>; }
function Loading({ text }: { text: string }) { return <div className="loading-state"><LoaderCircle className="spin" size={20}/>{text}</div>; }
function SubjectSelect({ token, value, onChange }: { token: string; value: string; onChange: (value: string) => void }) { const [subjects, setSubjects] = useState<Subject[]>([]); useEffect(() => { request('/subjects', token).then(async response => { if (response.ok) setSubjects(await response.json()); }); }, [token]); return <label className="subject-field">Disciplina (opcional)<select value={value} onChange={e => onChange(e.target.value)}><option value="">Sem disciplina</option>{subjects.map(subject => <option key={subject.id} value={subject.id}>{subject.name}</option>)}</select></label>; }

function App() {
  const [token, setToken] = useState(() => localStorage.getItem('studyflow_token'));
  const [authChecking, setAuthChecking] = useState(() => Boolean(localStorage.getItem('studyflow_token')));
  const [view, setView] = useState('dashboard');
  const [user, setUser] = useState<User | null>(null);
  const [theme, setTheme] = useState(localStorage.getItem('studyflow_theme') || 'light');
  const [profileOpen, setProfileOpen] = useState(false);
  const effectiveTheme = theme === 'system' ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light') : theme;
  useEffect(() => { document.documentElement.dataset.theme = effectiveTheme; localStorage.setItem('studyflow_theme', theme); }, [effectiveTheme, theme]);
  useEffect(() => {
    let active = true;
    if (!token) { setAuthChecking(false); setUser(null); return; }
    setAuthChecking(true);
    request('/auth/me', token).then(async response => {
      if (!active) return;
      if (response.ok) { const account = await response.json(); setUser(account); setTheme(account.theme || 'light'); }
      else { localStorage.removeItem('studyflow_token'); setToken(null); }
    }).catch(() => { if (active) { localStorage.removeItem('studyflow_token'); setToken(null); } })
      .finally(() => { if (active) setAuthChecking(false); });
    return () => { active = false; };
  }, [token]);
  function logout() { localStorage.removeItem('studyflow_token'); setToken(null); setUser(null); }
  async function chooseTheme(nextTheme: string) {
    setTheme(nextTheme);
    if (token) { const response = await request('/users/me', token, { method: 'PATCH', body: JSON.stringify({ theme: nextTheme }) }); if (response.ok) setUser(await response.json()); }
  }
  if (authChecking) return <div className="auth-loading"><LoaderCircle className="spin" size={24}/> Verificando sua sessão...</div>;
  if (!token) return <Login onLogin={value => { localStorage.setItem('studyflow_token', value); setToken(value); }} />;
  return <div className="app-shell">
    <aside className="app-sidebar"><div className="brand"><div className="brand-mark"><Sparkles size={18}/></div><span>Study<span>Flow</span></span></div>
      <nav className="side-nav" aria-label="Navegação principal">
        <div className="nav-group" role="group" aria-label="Início">
          <span className="nav-group-label">Início</span>
          <Nav active={view === 'dashboard'} onClick={() => setView('dashboard')} icon={<LayoutDashboard size={18}/>} text="Visão geral"/>
        </div>
        <div className="nav-group" role="group" aria-label="Planejar">
          <span className="nav-group-label">Planejar</span>
          <Nav active={view === 'tasks'} onClick={() => setView('tasks')} icon={<CheckCircle2 size={18}/>} text="Tarefas"/>
          <Nav active={view === 'goals'} onClick={() => setView('goals')} icon={<Target size={18}/>} text="Metas de estudo"/>
          <Nav active={view === 'subjects'} onClick={() => setView('subjects')} icon={<BookOpen size={18}/>} text="Disciplinas"/>
        </div>
        <div className="nav-group" role="group" aria-label="Acompanhar">
          <span className="nav-group-label">Acompanhar</span>
          <Nav active={view === 'sessions'} onClick={() => setView('sessions')} icon={<Timer size={18}/>} text="Sessões de estudo"/>
          <Nav active={view === 'calendar'} onClick={() => setView('calendar')} icon={<CalendarDays size={18}/>} text="Calendário"/>
          <Nav active={view === 'history'} onClick={() => setView('history')} icon={<History size={18}/>} text="Atividade recente"/>
          <Nav active={view === 'notifications'} onClick={() => setView('notifications')} icon={<Bell size={18}/>} text="Avisos de prazos"/>
        </div>
      </nav>
      <div className="sidebar-actions">
        <span className="nav-group-label">Conta</span>
        <Nav active={view === 'settings'} onClick={() => setView('settings')} icon={<Settings size={18}/>} text="Conta e preferências"/>
        <button className="theme-toggle" onClick={() => void chooseTheme(effectiveTheme === 'dark' ? 'light' : 'dark')} aria-label={effectiveTheme === 'dark' ? 'Ativar tema claro' : 'Ativar tema escuro'} title={effectiveTheme === 'dark' ? 'Tema claro' : 'Tema escuro'}>{effectiveTheme === 'dark' ? <Sun size={17}/> : <Moon size={17}/>}<span>{effectiveTheme === 'dark' ? 'Tema claro' : 'Tema escuro'}</span></button>
        <button className="logout" onClick={logout}><LogOut size={17}/> Sair</button>
      </div>
    </aside>
    <GlobalSessionIndicator token={token} onOpen={() => setView('sessions')}/>
    <main><header><div><p className="eyebrow">STUDYFLOW · SEU ESPAÇO DE FOCO</p><h1>Olá, {user?.name || 'estudante'}.</h1><p className="subtle">Pequenas sessões consistentes constroem grandes resultados.</p></div>
      <div className="header-actions"><button className="theme-icon" onClick={() => void chooseTheme(effectiveTheme === 'dark' ? 'light' : 'dark')} aria-label="Alternar tema" title="Alternar tema">{effectiveTheme === 'dark' ? <Sun size={18}/> : <Moon size={18}/>}</button><button className="avatar" onClick={() => setProfileOpen(!profileOpen)} aria-expanded={profileOpen} aria-label="Abrir conta">{user?.name?.charAt(0).toUpperCase() || 'S'}</button>{profileOpen && <div className="profile-menu"><strong>{user?.name || 'Estudante'}</strong><span>{user?.email || 'Sem email'}</span><hr/><button onClick={() => { setProfileOpen(false); setView('settings'); }}>Conta e preferências</button><button className="profile-logout" onClick={logout}>Sair da conta</button></div>}</div>
    </header>
    {view === 'dashboard' ? <Dashboard token={token} onOpenSettings={() => setView('settings')}/> : view === 'tasks' ? <LinkedTasksModule token={token}/> : view === 'goals' ? <StudyGoalsModule token={token}/> : view === 'subjects' ? <SubjectStudyModule token={token}/> : view === 'sessions' ? <StudySessionsModule token={token}/> : view === 'calendar' ? <CalendarPage token={token}/> : view === 'history' ? <RecentActivity token={token}/> : view === 'notifications' ? <NotificationsPage token={token}/> : view === 'settings' && user ? <SettingsPage token={token} user={user} onUserUpdate={updated => { setUser(updated); setTheme(updated.theme || 'light'); }} onAccountDeleted={logout}/> : <Dashboard token={token} onOpenSettings={() => setView('settings')}/>}
    </main>
  </div>;
}
function Nav({ active, onClick, icon, text }: { active: boolean; onClick: () => void; icon: ReactNode; text: string }) { return <button type="button" className={`nav-button ${active ? 'active' : ''}`} onClick={onClick} aria-label={text} aria-current={active ? 'page' : undefined} title={text}>{icon}<span>{text}</span></button>; }
function Login({ onLogin }: { onLogin: (token: string) => void }) {
  const [register, setRegister] = useState(false);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError('');
    try {
      const response = await publicRequest(register ? '/auth/register' : '/auth/login', {
        method: 'POST',
        body: JSON.stringify(register ? { name, email, password } : { email, password }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        setError(body?.detail || 'Não foi possível entrar. Confira seus dados e tente novamente.');
        return;
      }
      const data = await response.json();
      onLogin(data.access_token);
    } catch {
      setError('Não foi possível conectar ao StudyFlow. Tente novamente.');
    } finally {
      setLoading(false);
    }
  }

  return <div className="login"><section className="login-card">
    <div className="brand"><div className="brand-mark"><Sparkles size={18}/></div><span>Study<span>Flow</span></span></div>
    <p className="eyebrow">SEU ESPAÇO DE FOCO</p>
    <h1>{register ? 'Criar conta' : 'Bem-vindo de volta'}</h1>
    <p className="subtle">{register ? 'Organize seu próximo ciclo de estudos.' : 'Entre para continuar seus estudos.'}</p>
    <form onSubmit={submit}>
      {register && <label>Nome<input value={name} onChange={event => setName(event.target.value)} required minLength={2} maxLength={120} autoComplete="name"/></label>}
      <label>Email<input type="email" value={email} onChange={event => setEmail(event.target.value)} required autoComplete="email"/></label>
      <label>Senha<input type="password" value={password} onChange={event => setPassword(event.target.value)} required minLength={8} autoComplete={register ? 'new-password' : 'current-password'}/></label>
      {error && <p className="feedback failure" role="alert">{error}</p>}
      <button className="primary" type="submit" disabled={loading}>{loading ? 'Aguarde...' : register ? 'Criar conta' : 'Entrar'}</button>
    </form>
    <small>{register ? 'Já tem uma conta?' : 'Ainda não tem uma conta?'}{' '}
      <button className="link-button" type="button" onClick={() => { setRegister(!register); setError(''); }}>{register ? 'Entrar' : 'Criar conta'}</button>
    </small>
  </section></div>;
}

function Stat({ label, value, green = false }: { label: string; value: ReactNode; green?: boolean }) {
  return <div className="stat">
    <div className={'stat-icon' + (green ? ' green' : '')} aria-hidden="true">{green ? <CheckCircle2 size={18}/> : <Circle size={18}/>}</div>
    <div><small>{label}</small><strong>{value}</strong></div>
  </div>;
}

function TaskRow({ task, token, allowDelete = false, onChanged }: { task: Task; token: string; allowDelete?: boolean; onChanged?: () => void | Promise<void> }) {
  const [completed, setCompleted] = useState(task.status === 'COMPLETED');
  const [updating, setUpdating] = useState(false);
  async function toggle() {
    if (updating) return;
    setUpdating(true);
    try {
      const response = await request('/tasks/' + task.id, token, {
        method: 'PATCH',
        body: JSON.stringify({ status: completed ? 'PENDING' : 'COMPLETED' }),
      });
      if (response.ok) { setCompleted(!completed); await onChanged?.(); }
    } finally {
      setUpdating(false);
    }
  }
  async function remove() {
    if (updating || !window.confirm('Excluir a tarefa "' + task.title + '"?')) return;
    setUpdating(true);
    try {
      const response = await request('/tasks/' + task.id, token, { method: 'DELETE' });
      if (response.ok) await onChanged?.();
    } finally {
      setUpdating(false);
    }
  }
  const taskStatus = task.status === 'COMPLETED' ? 'Tarefa concluída' : task.status === 'IN_PROGRESS' ? 'Em andamento' : 'Tarefa pendente';
  return <div className={'task' + (completed ? ' done' : '')}>
    <button className="check" type="button" onClick={() => void toggle()} disabled={updating} aria-label={completed ? 'Marcar tarefa como pendente' : 'Concluir tarefa'}>
      {completed ? <CheckCircle2/> : <Circle/>}
    </button>
    <div><strong>{task.title}</strong><small>{task.description || taskStatus}</small></div>
    {task.due_date && <span className="tag">Prazo {new Date(task.due_date).toLocaleDateString('pt-BR')}</span>}
    {allowDelete && <button className="icon-action delete" type="button" onClick={() => void remove()} disabled={updating} aria-label={'Excluir tarefa ' + task.title} title="Excluir tarefa"><Trash2 size={16}/></button>}
  </div>;
}

function Empty({ text }: { text: string }) { return <div className="empty">{text}</div>; }

function sessionChanged() { window.dispatchEvent(new CustomEvent('studyflow-session-changed')); }

function formatStudySeconds(value: number) {
  const total = Math.max(0, Math.floor(value || 0));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const seconds = total % 60;
  return [hours, minutes, seconds].map(part => String(part).padStart(2, '0')).join(':');
}

function formatStudyCompact(value: number) {
  const totalMinutes = Math.floor(Math.max(0, value || 0) / 60);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  return hours ? hours + 'h ' + minutes + 'min' : minutes + 'min';
}

function Dashboard({ token, onOpenSettings }: { token: string; onOpenSettings: () => void }) {
  const [data, setData] = useState<Dashboard | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  async function load(manual = false) {
    if (manual) setRefreshing(true);
    try {
    const [summary, taskResponse] = await Promise.all([request('/dashboard', token), request('/tasks', token)]);
      if (summary.ok) setData(await summary.json());
      if (taskResponse.ok) setTasks(normalizeTaskPage(await taskResponse.json()).items.slice(0, 5));
    } catch { /* Mantém os dados já carregados quando a API falha. */
    } finally { setRefreshing(false); }
  }
  useEffect(() => {
    const refresh = () => { void load(true); };
    void load();
    window.addEventListener('studyflow-data-changed', refresh);
    return () => window.removeEventListener('studyflow-data-changed', refresh);
  }, [token]);
  const weeklyGoalMinutes = data?.weekly_study_goal_minutes || 300;
  const weeklySeconds = data?.week_study_seconds || 0;
  const weeklyMinutes = Math.floor(weeklySeconds / 60);
  const weeklyProgress = Math.min(100, Math.round((weeklyMinutes / weeklyGoalMinutes) * 100));
  return <><section className="hero"><div><p className="eyebrow light">SEU FLUXO DE HOJE</p><h2>Clareza para fazer<br/><em>o que importa.</em></h2></div><div className="hero-number">{data?.studied_minutes || 0}<small>min estudados</small></div></section>
    <div className="stats"><Stat label="Pendentes" value={data?.pending_tasks ?? 0}/><Stat label="Concluídas" value={data?.completed_tasks ?? 0} green/><Stat label="Metas ativas" value={data?.active_goals ?? 0}/><Stat label="Em atraso" value={data?.overdue_tasks ?? 0}/></div>
    <section className={`content weekly-study-goal ${weeklyProgress >= 100 ? 'reached' : ''}`}><div className="weekly-goal-heading"><div><p className="eyebrow">ACOMPANHAMENTO SEMANAL</p><h2>Meta de estudo</h2></div><button type="button" className="secondary" onClick={onOpenSettings}>Ajustar meta</button></div><div className="weekly-goal-summary"><strong>{formatStudyCompact(weeklySeconds)}</strong><span>de {formatStudyCompact(weeklyGoalMinutes * 60)} nesta semana</span><b>{weeklyProgress}%</b></div><div className="progress-track" role="progressbar" aria-label="Progresso da meta semanal" aria-valuemin={0} aria-valuemax={100} aria-valuenow={weeklyProgress}><div style={{ width: `${weeklyProgress}%` }}/></div><small>{weeklyProgress >= 100 ? 'Meta semanal atingida. Bom trabalho!' : `Faltam ${formatStudyCompact(Math.max(0, weeklyGoalMinutes - weeklyMinutes) * 60)} para alcançar sua meta.`}</small></section>
    <section className="content"><div className="section-heading"><div><p className="eyebrow">PRÓXIMOS PASSOS</p><h2>Tarefas para fazer</h2></div><RefreshButton onRefresh={() => load(true)} loading={refreshing}/></div><div className="task-list">{tasks.length ? tasks.map(task => <TaskRow key={task.id} task={task} token={token} allowDelete onChanged={() => load(true)}/>) : <Empty text="Você ainda não possui tarefas pendentes."/>}</div></section>
    <RecentActivity token={token}/></>;
}
function SubjectStudyModule({ token }: { token: string }) {
  const [subjects, setSubjects] = useState<any[]>([]); const [stats, setStats] = useState<any>({}); const [selected, setSelected] = useState<any>(null); const [loading, setLoading] = useState(true); const [refreshing, setRefreshing] = useState(false); const [error, setError] = useState(''); const [message, setMessage] = useState(''); const [open, setOpen] = useState(false); const [name, setName] = useState(''); const [description, setDescription] = useState(''); const [starting, setStarting] = useState(''); const [deletingSubject, setDeletingSubject] = useState(false);
  async function load(manual = false) { if (manual) setRefreshing(true); else setLoading(true); try { const [list, summary] = await Promise.all([request('/subjects', token), request('/subjects/stats', token)]); if (!list.ok) throw new Error('Não foi possível carregar as disciplinas.'); setSubjects(await list.json()); if (summary.ok) setStats(await summary.json()); setError(''); } catch { setError('Não foi possível carregar suas disciplinas.'); } finally { setLoading(false); setRefreshing(false); } }
  useEffect(() => { load(); }, [token]);
  async function start(subjectId: string) { setStarting(subjectId); setError(''); const response = await request('/study-sessions/start', token, { method: 'POST', body: JSON.stringify({ subject_id: subjectId }) }); if (response.ok) { setMessage('Estudo iniciado. O cronômetro está em andamento.'); sessionChanged(); } else { const body = await response.json().catch(() => null); setError(body?.detail || 'Não foi possível iniciar o estudo.'); } setStarting(''); }
  async function show(id: string) { setError(''); const response = await request('/subjects/' + id, token); if (response.ok) setSelected(await response.json()); else setError('Não foi possível carregar os detalhes da disciplina.'); }
  async function removeSubject(subject: any) {
    if (!window.confirm('Excluir a disciplina "' + subject.name + '"? As tarefas e metas vinculadas também serão excluídas. Sessões registradas serão mantidas no histórico.')) return;
    setDeletingSubject(true);
    setError('');
    setMessage('');
    try {
      const response = await request('/subjects/' + subject.id, token, { method: 'DELETE' });
      if (!response.ok) throw new Error('Não foi possível excluir a disciplina.');
      setSelected(null);
      setMessage('Disciplina, tarefas e metas vinculadas excluídas. Sessões permanecem no histórico.');
      await load(true);
    } catch {
      setError('Não foi possível excluir a disciplina. Tente novamente.');
    } finally {
      setDeletingSubject(false);
    }
  }
  async function create(e: FormEvent) { e.preventDefault(); const response = await request('/subjects', token, { method: 'POST', body: JSON.stringify({ name, description: description || null, color: '#5267df', status: 'PLANNED' }) }); if (response.ok) { setName(''); setDescription(''); setOpen(false); setMessage('Disciplina criada com sucesso.'); await load(true); } else setError('Não foi possível criar a disciplina.'); }
  if (selected) return <section className="content subject-detail"><button className="back-button" onClick={() => setSelected(null)}>← Minhas disciplinas</button><div className="detail-heading"><div className="subject-avatar"><BookOpen size={28}/></div><div><p className="eyebrow">CENTRO ACADÊMICO</p><h2>{selected.name}</h2><p className="subtle">{selected.description || 'Organize tudo o que você está estudando nesta disciplina.'}</p></div><button className="primary" onClick={() => start(selected.id)} disabled={starting === selected.id}>{starting === selected.id ? 'Iniciando...' : '▶ Iniciar estudo'}</button></div>{error && <p className="feedback failure">{error}</p>}<div className="subject-progress"><strong>{selected.stats.progress}%</strong><span>progresso por tarefas</span><div className="progress-track"><div style={{width: selected.stats.progress + '%'}}/></div></div><div className="detail-metrics"><Stat label="Tarefas" value={selected.stats.total_tasks}/><Stat label="Concluídas" value={selected.stats.completed_tasks} green/><Stat label="Sessões" value={selected.stats.total_sessions}/><Stat label="Minutos estudados" value={selected.stats.studied_minutes}/></div><div className="related-section"><div className="section-heading"><div><p className="eyebrow">PLANEJAMENTO</p><h3>Metas relacionadas</h3></div><span className="count">{selected.related_goals?.length || 0} metas</span></div>{selected.related_goals?.length ? selected.related_goals.map((goal: any) => <div className="task related-item" key={goal.id}><div className="stat-icon"><Target size={18}/></div><div><strong>{goal.title}</strong><small>{goal.metric === 'TIME' ? `${goal.progress || 0} de ${goal.target || 0} minutos` : `${goal.progress || 0} de ${goal.target || 0} tarefas concluídas`}</small></div></div>) : <Empty text="Nenhuma meta relacionada a esta disciplina."/>}</div><div className="related-section"><div className="section-heading"><div><p className="eyebrow">EXECUÇÃO</p><h3>Tarefas relacionadas</h3></div><span className="count">{selected.related_tasks?.length || 0} tarefas</span></div>{selected.related_tasks?.length ? selected.related_tasks.map((task: any) => <div className="task related-item" key={task.id}><div className="stat-icon"><CheckCircle2 size={18}/></div><div><strong>{task.title}</strong><small>{task.status === 'COMPLETED' ? 'Concluída' : 'Pendente'}</small></div></div>) : <Empty text="Nenhuma tarefa relacionada a esta disciplina."/>}</div></section>;
  return <section className="content subjects-page"><div className="tasks-heading"><div><p className="eyebrow">CENTRO ACADÊMICO</p><h2>Minhas disciplinas</h2><p className="subtle">Escolha uma disciplina e comece a estudar com o cronômetro.</p></div><div className="page-actions"><RefreshButton onRefresh={() => load(true)} loading={refreshing}/><button className="primary" onClick={() => setOpen(true)}><Plus size={17}/> Nova disciplina</button></div></div><div className="task-stats"><Stat label="Ativas" value={stats.active || 0}/><Stat label="Em andamento" value={stats.in_progress || 0}/><Stat label="Concluídas" value={stats.completed || 0} green/><Stat label="Atrasadas" value={stats.overdue || 0}/></div>{message && <p className="feedback success">{message}</p>}{error && <p className="feedback failure">{error}</p>}{loading ? <Loading text="Carregando disciplinas..."/> : <div className="subject-grid">{subjects.length ? subjects.map(subject => <article className="subject-card" key={subject.id}><div className="subject-card-top"><div className="subject-avatar"><BookOpen size={20}/></div><button className="icon-action delete" type="button" onClick={() => void removeSubject(subject)} disabled={deletingSubject} aria-label={'Excluir disciplina ' + subject.name} title={'Excluir disciplina ' + subject.name}><Trash2 size={16}/></button></div><h3><button className="subject-title-link" type="button" onClick={() => void show(subject.id)}>{subject.name}</button></h3><p>{subject.description || 'Área de estudo sem descrição.'}</p><span className="badge">{subject.status === 'IN_PROGRESS' ? 'Em andamento' : subject.status === 'COMPLETED' ? 'Concluída' : 'Planejada'}</span><button className="primary study-start-button" onClick={() => start(subject.id)} disabled={starting === subject.id}>{starting === subject.id ? 'Iniciando...' : '▶ Iniciar estudo'}</button></article>) : <Empty text="Você ainda não possui disciplinas."/>}</div>}{open && <div className="modal-backdrop" onClick={() => setOpen(false)}><form className="task-modal" onClick={e => e.stopPropagation()} onSubmit={create}><div className="section-heading"><h2>Nova disciplina</h2><button type="button" className="modal-close" onClick={() => setOpen(false)}>×</button></div><label>Nome<input autoFocus value={name} onChange={e => setName(e.target.value)} required maxLength={120}/></label><label>Descrição<textarea value={description} onChange={e => setDescription(e.target.value)} maxLength={2000}/></label><div className="modal-actions"><button type="button" className="secondary" onClick={() => setOpen(false)}>Cancelar</button><button className="primary">Criar disciplina</button></div></form></div>}</section>;
}

function StudySessionsModule({ token }: { token: string }) {
  const [sessions, setSessions] = useState<any[]>([]); const [subjects, setSubjects] = useState<any[]>([]); const [tasks, setTasks] = useState<Task[]>([]); const [stats, setStats] = useState<any>({}); const [active, setActive] = useState<any>(null); const [selectedSubject, setSelectedSubject] = useState(''); const [selectedTaskId, setSelectedTaskId] = useState(''); const [showStart, setShowStart] = useState(false); const [confirmFinish, setConfirmFinish] = useState(false); const [completing, setCompleting] = useState(false); const [loading, setLoading] = useState(true); const [refreshing, setRefreshing] = useState(false); const [error, setError] = useState(''); const [message, setMessage] = useState(''); const [tick, setTick] = useState(0); const [deletingSession, setDeletingSession] = useState<string | null>(null);
  async function load(manual = false) { if (manual) setRefreshing(true); else setLoading(true); try { const [sessionResponse, subjectResponse, statsResponse, activeResponse, pendingResponse, inProgressResponse] = await Promise.all([request('/study-sessions', token), request('/subjects', token), request('/study-sessions/stats', token), request('/study-sessions/active', token), request('/tasks?status=PENDING&page_size=50', token), request('/tasks?status=IN_PROGRESS&page_size=50', token)]); if (!sessionResponse.ok || !subjectResponse.ok || !statsResponse.ok || !activeResponse.ok) throw new Error(); setSessions(await sessionResponse.json()); setSubjects(await subjectResponse.json()); setStats(await statsResponse.json()); setActive(await activeResponse.json()); const availableTasks = [...(pendingResponse.ok ? normalizeTaskPage(await pendingResponse.json()).items : []), ...(inProgressResponse.ok ? normalizeTaskPage(await inProgressResponse.json()).items : [])]; setTasks(availableTasks); setError(''); } catch { setError('Não foi possível carregar suas sessões.'); } finally { setLoading(false); setRefreshing(false); } }
  useEffect(() => { load(); }, [token]);
  useEffect(() => { if (!active || active.status !== 'RUNNING') return; const timer = window.setInterval(() => setTick(value => value + 1), 1000); return () => window.clearInterval(timer); }, [active]);
  function displayedSeconds() { if (!active) return 0; const extra = active.status === 'RUNNING' && active.active_started_at ? Math.max(0, Math.floor((Date.now() - new Date(active.active_started_at).getTime()) / 1000)) : 0; return (active.duration_seconds || 0) + extra + tick * 0; }
  async function start() { if (!selectedSubject) return; const response = await request('/study-sessions/start', token, { method: 'POST', body: JSON.stringify({ subject_id: selectedSubject }) }); if (response.ok) { setShowStart(false); setSelectedSubject(''); setMessage('Estudo iniciado.'); sessionChanged(); await load(true); } else { const body = await response.json().catch(() => null); setError(body?.detail || 'Não foi possível iniciar o estudo.'); } }
  async function action(name: 'pause' | 'resume' | 'finish' | 'cancel') {
    if (!active) return;
    if (name === 'finish') setCompleting(true);
    try {
      const response = await request(`/study-sessions/${active.id}/${name}`, token, { method: 'POST' });
      if (response.ok) {
        setActive(name === 'finish' || name === 'cancel' ? null : await response.json());
        let taskUpdateFailed = false;
        if (name === 'finish' && selectedTaskId) {
          try {
            const taskResponse = await request(`/tasks/${selectedTaskId}`, token, { method: 'PATCH', body: JSON.stringify({ status: 'COMPLETED' }) });
            taskUpdateFailed = !taskResponse.ok;
          } catch { taskUpdateFailed = true; }
        }
        if (name === 'finish') setMessage(taskUpdateFailed ? 'Sessão registrada; não foi possível concluir a tarefa selecionada.' : selectedTaskId ? 'Sessão concluída e tarefa marcada como concluída.' : 'Sessão concluída com sucesso.');
        if (name === 'cancel') setMessage('Sessão cancelada.');
        setConfirmFinish(false); setSelectedTaskId(''); sessionChanged(); window.dispatchEvent(new CustomEvent('studyflow-data-changed')); await load(true);
        if (taskUpdateFailed) setError('Tente concluir a tarefa pela aba Tarefas.');
      } else { const body = await response.json().catch(() => null); setError(body?.detail || 'Não foi possível atualizar a sessão.'); }
    } catch {
      setError('Não foi possível atualizar a sessão. Verifique sua conexão e tente novamente.');
    } finally {
      if (name === 'finish') setCompleting(false);
    }
  }
  async function removeSession(session: any) {
    if (!window.confirm('Excluir esta sessão de estudo do histórico?')) return;
    setDeletingSession(session.id); setError('');
    try {
      const response = await request(`/study-sessions/${session.id}`, token, { method: 'DELETE' });
      if (!response.ok) throw new Error();
      setMessage('Sessão removida do histórico.');
      sessionChanged();
      await load(true);
    } catch { setError('Não foi possível excluir esta sessão.'); }
    finally { setDeletingSession(null); }
  }
  const subjectName = active ? subjects.find(subject => subject.id === active.subject_id)?.name || 'Disciplina' : '';
  return <section className="content sessions-page"><div className="tasks-heading"><div><p className="eyebrow">FOCO E EVOLUÇÃO</p><h2>Minhas sessões de estudo</h2><p className="subtle">Comece uma sessão e deixe o StudyFlow acompanhar seu tempo.</p></div><div className="page-actions"><RefreshButton onRefresh={() => load(true)} loading={refreshing}/><button className="primary" onClick={() => setShowStart(true)} disabled={Boolean(active)}>▶ Iniciar estudo</button></div></div>{error && <p className="feedback failure">{error}</p>}{message && <p className="feedback success">{message}</p>}{active && <div className={`active-session-card ${active.status === 'PAUSED' ? 'paused' : ''}`}><div><span className="session-status"><i/> {active.status === 'PAUSED' ? 'ESTUDO PAUSADO' : 'ESTUDO EM ANDAMENTO'}</span><h3>{subjectName}</h3><p>Sessão atual</p></div><strong className="session-timer">{formatStudySeconds(displayedSeconds())}</strong><div className="session-actions">{active.status === 'RUNNING' ? <button className="secondary" onClick={() => action('pause')}>⏸ Pausar</button> : <button className="primary" onClick={() => action('resume')}>▶ Retomar</button>}<button className="danger-button" onClick={() => setConfirmFinish(true)}>■ Finalizar</button></div></div>}<div className="session-stats"><Stat label="Hoje" value={formatStudyCompact(stats.today_seconds || 0) as any}/><Stat label="Esta semana" value={formatStudyCompact(stats.week_seconds || 0) as any}/><Stat label="Este mês" value={formatStudyCompact(stats.month_seconds || 0) as any}/><Stat label="Total" value={formatStudyCompact(stats.total_seconds || 0) as any}/></div><div className="section-heading"><div><p className="eyebrow">HISTÓRICO</p><h3>Sessões concluídas</h3></div><span className="count">{stats.total_sessions || 0} sessões</span></div>{loading ? <Loading text="Carregando sessões..."/> : <div className="task-list">{sessions.filter(session => session.status === 'COMPLETED').length ? sessions.filter(session => session.status === 'COMPLETED').map(session => <div className="task session-history-item" key={session.id}><div className="stat-icon"><Clock3 size={18}/></div><div><strong>{subjects.find(subject => subject.id === session.subject_id)?.name || 'Disciplina'}</strong><small>{formatStudySeconds(session.duration_seconds)} · {new Date(session.started_at).toLocaleString('pt-BR')}</small></div><button className="icon-action delete" type="button" onClick={() => void removeSession(session)} disabled={deletingSession === session.id} aria-label="Excluir sessão de estudo" title="Excluir sessão"><Trash2 size={16}/></button></div>) : <Empty text="Você ainda não possui sessões de estudo."/>}</div>}{showStart && <div className="modal-backdrop" onClick={() => setShowStart(false)}><form className="task-modal" onClick={event => event.stopPropagation()} onSubmit={event => { event.preventDefault(); start(); }}><div className="section-heading"><h2>Novo estudo</h2><button type="button" className="modal-close" onClick={() => setShowStart(false)}>×</button></div>{subjects.length ? <label>Escolha uma disciplina<select autoFocus value={selectedSubject} onChange={event => setSelectedSubject(event.target.value)} required><option value="">Selecione...</option>{subjects.map(subject => <option key={subject.id} value={subject.id}>{subject.name}</option>)}</select></label> : <Empty text="Você ainda não possui disciplinas."/>}<div className="modal-actions"><button type="button" className="secondary" onClick={() => setShowStart(false)}>Cancelar</button><button className="primary" disabled={!subjects.length || !selectedSubject}>▶ Iniciar estudo</button></div></form></div>}{confirmFinish && active && <div className="modal-backdrop" onClick={() => { if (!completing) { setConfirmFinish(false); setSelectedTaskId(''); } }}><div className="task-modal" onClick={event => event.stopPropagation()}><h2>Finalizar sessão</h2><p>Você estudou <strong>{formatStudySeconds(displayedSeconds())}</strong> em {subjectName}.</p><p>Se terminou uma tarefa durante este estudo, você pode marcá-la como concluída:</p>{tasks.length ? <label>Tarefa<select value={selectedTaskId} onChange={event => setSelectedTaskId(event.target.value)}><option value="">Não marcar tarefa</option>{tasks.map(task => <option key={task.id} value={task.id}>{task.title}{task.status === 'IN_PROGRESS' ? ' · Em andamento' : ' · Pendente'}</option>)}</select></label> : <p className="subtle">Você não tem tarefas pendentes ou em andamento.</p>}<div className="modal-actions"><button className="secondary" onClick={() => { setConfirmFinish(false); setSelectedTaskId(''); }}>Continuar estudando</button><button className="primary" onClick={() => void action('finish')} disabled={completing}>{completing ? 'Salvando...' : 'Finalizar sessão'}</button></div></div></div>}</section>;
}

function GlobalSessionIndicator({ token, onOpen }: { token: string; onOpen: () => void }) { const [active, setActive] = useState<any>(null); const [subjects, setSubjects] = useState<any[]>([]); const [tick, setTick] = useState(0); async function load() { const [activeResponse, subjectResponse] = await Promise.all([request('/study-sessions/active', token), request('/subjects', token)]); if (activeResponse.ok) setActive(await activeResponse.json()); if (subjectResponse.ok) setSubjects(await subjectResponse.json()); } useEffect(() => { load(); const refresh = () => load(); window.addEventListener('studyflow-session-changed', refresh); const timer = window.setInterval(load, 5000); return () => { window.removeEventListener('studyflow-session-changed', refresh); window.clearInterval(timer); }; }, [token]); useEffect(() => { if (!active || active.status !== 'RUNNING') return; const timer = window.setInterval(() => setTick(value => value + 1), 1000); return () => window.clearInterval(timer); }, [active]); if (!active) return null; const extra = active.status === 'RUNNING' && active.active_started_at ? Math.max(0, Math.floor((Date.now() - new Date(active.active_started_at).getTime()) / 1000)) : 0; const subject = subjects.find(item => item.id === active.subject_id); return <button className={`global-session-indicator ${active.status === 'PAUSED' ? 'paused' : ''}`} onClick={onOpen}><span className="session-status"><i/> {active.status === 'PAUSED' ? 'Estudo pausado' : 'Estudando'}</span><strong>{subject?.name || 'Disciplina'} · {formatStudySeconds((active.duration_seconds || 0) + extra + tick * 0)}</strong><small>Ver sessão</small></button>; }

function StudyGoalsModule({ token }: { token: string }) {
  const [goals, setGoals] = useState<any[]>([]);
  const [subjects, setSubjects] = useState<any[]>([]);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [target, setTarget] = useState('10');
  const [subjectId, setSubjectId] = useState('');
  const [dueDate, setDueDate] = useState('');
  const [metric, setMetric] = useState('TASKS');
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [deletingGoal, setDeletingGoal] = useState<string | null>(null);
  async function load() {
    const [goalsResponse, subjectsResponse] = await Promise.all([request('/goals', token), request('/subjects', token)]);
    if (goalsResponse.ok) setGoals(await goalsResponse.json());
    if (subjectsResponse.ok) setSubjects(await subjectsResponse.json());
    else setError('Não foi possível carregar as disciplinas.');
  }
  useEffect(() => { void load(); }, [token]);
  async function removeGoal(goal: any) {
    if (!window.confirm('Excluir a meta "' + goal.title + '"? As tarefas vinculadas a ela também serão excluídas.')) return;
    setDeletingGoal(goal.id);
    setError('');
    setMessage('');
    try {
      const response = await request('/goals/' + goal.id, token, { method: 'DELETE' });
      if (!response.ok) throw new Error('Não foi possível excluir a meta.');
      setGoals(current => current.filter(item => item.id !== goal.id));
      setMessage('Meta e tarefas vinculadas excluídas das outras áreas.');
    } catch {
      setError('Não foi possível excluir a meta. Tente novamente.');
    } finally {
      setDeletingGoal(null);
    }
  }
  async function create(event: FormEvent) {
    event.preventDefault();
    const dueAt = dueDate ? new Date(dueDate + 'T12:00:00').toISOString() : null;
    const response = await request('/goals', token, { method: 'POST', body: JSON.stringify({ title, description: description || null, target: Number(target) || 10, priority: 'MEDIUM', metric, subject_id: subjectId || null, due_date: dueAt }) });
    if (response.ok) {
      setTitle(''); setDescription(''); setTarget(metric === 'TIME' ? '60' : '10'); setSubjectId(''); setDueDate(''); setMetric('TASKS'); setOpen(false); setMessage('Meta criada com sucesso.'); setError(''); await load();
    } else { const body = await response.json().catch(() => null); setError(body?.detail || 'Não foi possível criar a meta.'); }
  }
  return <section className="content goals-page">
    <div className="tasks-heading"><div><p className="eyebrow">OBJETIVOS E EVOLUÇÃO</p><h2>Metas de estudo</h2><p className="subtle">Acompanhe tarefas concluídas ou minutos estudados por disciplina.</p></div><button className="primary" onClick={() => setOpen(true)}><Plus size={17}/> Nova meta</button></div>
    {message && <p className="feedback success">{message}</p>}{error && <p className="feedback failure">{error}</p>}
    <div className="goal-grid">{goals.length ? goals.map(goal => { const subject = subjects.find(item => item.id === goal.subject_id); return <article className="goal-card" key={goal.id}><div className="goal-card-top"><div className="goal-icon"><Target size={21}/></div><button className="icon-action delete" type="button" onClick={() => void removeGoal(goal)} disabled={Boolean(deletingGoal)} aria-label={'Excluir meta ' + goal.title} title={'Excluir meta ' + goal.title}><Trash2 size={16}/></button></div><h3>{goal.title}</h3><p>{goal.description || 'Sem descrição'}</p><div className="progress-label"><span>{goal.metric === 'TIME' ? 'Tempo de estudo' : 'Tarefas concluídas'}</span><strong>{goal.progress || 0}/{goal.target || 0}</strong></div><div className="progress-track"><div style={{width: (goal.target ? Math.min(100, Math.round((goal.progress / goal.target) * 100)) : 0) + '%'}}/></div><small>{subject?.name || 'Sem disciplina'}{goal.due_date ? ' · Prazo ' + new Date(goal.due_date).toLocaleDateString('pt-BR') : ''}</small></article>; }) : <Empty text="Você ainda não possui metas."/>}</div>
    {open && <div className="modal-backdrop" onClick={() => setOpen(false)}><form className="task-modal goal-modal" onClick={event => event.stopPropagation()} onSubmit={create}><div className="section-heading"><h2>Nova meta</h2><button type="button" className="modal-close" onClick={() => setOpen(false)}>×</button></div><label>Nome da meta<input autoFocus value={title} onChange={event => setTitle(event.target.value)} required maxLength={180}/></label><label>Descrição<textarea value={description} onChange={event => setDescription(event.target.value)} maxLength={3000}/></label><label>Tipo de acompanhamento<select value={metric} onChange={event => { setMetric(event.target.value); setTarget(event.target.value === 'TIME' ? '60' : '10'); }}><option value="TASKS">Tarefas concluídas</option><option value="TIME">Tempo de estudo em minutos</option></select></label><label>{metric === 'TIME' ? 'Minutos desejados' : 'Quantidade de tarefas'}<input type="number" min="1" value={target} onChange={event => setTarget(event.target.value)} required/></label><SubjectSelect token={token} value={subjectId} onChange={setSubjectId}/><label>Prazo (opcional)<input type="date" value={dueDate} onChange={event => setDueDate(event.target.value)}/></label><div className="modal-actions"><button type="button" className="secondary" onClick={() => setOpen(false)}>Cancelar</button><button className="primary" type="submit">Criar meta</button></div></form></div>}
  </section>;
}
function LinkedTasksModule({ token }: { token: string }) {
  const [tasks, setTasks] = useState<any[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [subjectId, setSubjectId] = useState('');
  const [dueDate, setDueDate] = useState('');
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState('');
  async function load() {
    const [taskResponse, subjectResponse] = await Promise.all([request('/tasks?page=1&page_size=100', token), request('/subjects', token)]);
    if (taskResponse.ok) { const data = await taskResponse.json(); setTasks(Array.isArray(data) ? data : data.items || []); }
    if (subjectResponse.ok) setSubjects(await subjectResponse.json());
  }
  useEffect(() => { void load(); }, [token]);
  async function create(event: FormEvent) {
    event.preventDefault();
    const dueAt = dueDate ? new Date(dueDate + 'T12:00:00').toISOString() : null;
    const response = await request('/tasks', token, { method: 'POST', body: JSON.stringify({ title, description: description || null, status: 'PENDING', priority: 'MEDIUM', subject_id: subjectId || null, due_date: dueAt }) });
    if (response.ok) { setTitle(''); setDescription(''); setSubjectId(''); setDueDate(''); setOpen(false); setMessage('Tarefa criada.'); await load(); }
    else { const body = await response.json().catch(() => null); setMessage(body?.detail || 'Não foi possível criar a tarefa.'); }
  }
  async function toggle(task: any) { await request('/tasks/' + task.id, token, { method: 'PATCH', body: JSON.stringify({ status: task.status === 'COMPLETED' ? 'PENDING' : 'COMPLETED', subject_id: task.subject_id || null }) }); await load(); }
  async function remove(id: string) { if (!confirm('Excluir tarefa? Esta ação não poderá ser desfeita.')) return; const response = await request('/tasks/' + id, token, { method: 'DELETE' }); if (response.ok) await load(); }
  return <section className="content tasks-page">
    <div className="tasks-heading"><div><p className="eyebrow">LISTA DE EXECUÇÃO</p><h2>Tarefas</h2><p className="subtle">Cada tarefa é uma ação concreta. Organize, defina prazo e marque ao concluir.</p></div><button className="primary" onClick={() => setOpen(true)}><Plus size={17}/> Nova tarefa</button></div>
    {message && <p className="feedback success">{message}</p>}
    <div className="task-list">{tasks.length ? tasks.map(task => <div className="task task-card" key={task.id}><button className="check" onClick={() => toggle(task)} aria-label="Alternar conclusão">{task.status === 'COMPLETED' ? <CheckCircle2/> : <Circle/>}</button><div className="task-card-main"><strong>{task.title}</strong><small>{task.description || 'Sem descrição'}</small><div className="task-meta"><span>{task.status === 'COMPLETED' ? 'Concluída' : task.status === 'IN_PROGRESS' ? 'Em andamento' : 'Pendente'}</span><span>{subjects.find(subject => subject.id === task.subject_id)?.name || 'Sem disciplina'}</span>{task.due_date && <span>Prazo: {new Date(task.due_date).toLocaleDateString('pt-BR')}</span>}</div></div><div className="item-actions"><button className="icon-action delete" onClick={() => remove(task.id)} aria-label="Excluir tarefa"><Trash2 size={16}/></button></div></div>) : <Empty text="Você ainda não possui tarefas."/>}</div>
    {open && <div className="modal-backdrop" onClick={() => setOpen(false)}><form className="task-modal" onClick={event => event.stopPropagation()} onSubmit={create}><div className="section-heading"><h2>Nova tarefa</h2><button type="button" className="modal-close" onClick={() => setOpen(false)}>×</button></div><label>Título<input autoFocus value={title} onChange={event => setTitle(event.target.value)} required maxLength={180}/></label><label>Descrição<textarea value={description} onChange={event => setDescription(event.target.value)} maxLength={5000}/></label><SubjectSelect token={token} value={subjectId} onChange={setSubjectId}/><label>Prazo (opcional)<input type="date" value={dueDate} onChange={event => setDueDate(event.target.value)}/></label><div className="modal-actions"><button type="button" className="secondary" onClick={() => setOpen(false)}>Cancelar</button><button className="primary" type="submit">Criar tarefa</button></div></form></div>}
  </section>;
}
createRoot(document.getElementById('root')!).render(<StrictMode><App/></StrictMode>);

