# StudyFlow

Plataforma de organização de estudos e produtividade acadêmica.

## Stack

- Frontend: React, TypeScript, Vite e CSS com tokens de design.
- Backend: Python, FastAPI, SQLAlchemy e JWT.
- Banco: SQLite local por padrão. A configuração Docker guarda os dados no volume `studyflow_data`.
- Autenticação: JWT com hash de senha PBKDF2 (sem senha em texto puro).

## Executar localmente

No Windows, prepare o ambiente uma vez e depois clique duas vezes em [StudyFlow - Iniciar.lnk](StudyFlow%20-%20Iniciar.lnk). O atalho inicia a API e a interface e abre `http://localhost:5173`. O roteiro está em [TESTAR_STUDYFLOW.md](TESTAR_STUDYFLOW.md).

```powershell
python -m venv backend/.venv
backend/.venv/Scripts/python -m pip install -r backend/requirements.txt
cd frontend
corepack pnpm install --frozen-lockfile
```

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

No Windows, ative o ambiente com `.venv\Scripts\activate`.

### Instalador Windows

O arquivo para compartilhar é `dist-installer/StudyFlow-Setup.exe`. Ele instala o executável do StudyFlow e cria um atalho no menu Iniciar; a interface abre em uma janela própria do StudyFlow, sem deixar uma aba do navegador aberta. Python, Node.js e o código da interface já vão dentro do app. O instalador verifica se o Microsoft Edge WebView2 Runtime está presente e, se faltar, o instala durante a configuração. O construtor do instalador requer Python do projeto, Node.js/Corepack, Inno Setup 6 e acesso à internet para baixar o pequeno instalador oficial do WebView2. Essas ferramentas são necessárias apenas para gerar o instalador, não para quem o instala.

O programa fica em `%LOCALAPPDATA%\Programs\StudyFlow`. As contas, os dados e a sessão ficam em `%LOCALAPPDATA%\StudyFlow`; o banco local SQLite é salvo em `studyflow.db`. Fechar ou reabrir o app não apaga esses dados, e desinstalar o programa preserva essa pasta para uma instalação posterior. Essa pasta de dados fica no local padrão do Windows para dados de aplicativos, sem espalhar arquivos do projeto em Documentos ou na área de trabalho.

Para gerar o instalador em Windows após preparar o ambiente do projeto, execute no PowerShell: `& .\backend\.venv\Scripts\python.exe tools\build_windows_installer.py`.

Para publicar uma versão baixável no GitHub, envie as alterações para `main` e crie uma tag de versão, por exemplo `git tag v1.0.0` seguida de `git push origin v1.0.0`. O GitHub Actions gera o instalador Windows e o anexa a uma nova versão em Releases.

### Frontend

```bash
cd frontend
corepack pnpm install --frozen-lockfile
corepack pnpm run dev
```

Em desenvolvimento, o Vite encaminha `/api` para `http://localhost:8000`. No Docker, o Nginx encaminha as chamadas para o serviço `studyflow-api`, então a interface não depende do endereço local do navegador.

### Docker

```bash
docker compose up --build
```

O Compose grava o SQLite em `/data/studyflow.db`, persistido no volume `studyflow_data`. O banco corporativo não deve ser acessado diretamente: a integração pela API de procedures ainda depende dos endpoints, nomes de procedures e credenciais fornecidos pelo ambiente de destino.

## Configuração

Copie `.env.example` para `.env` e ajuste os valores. Para execução local, `DATABASE_URL` aponta para `backend/studyflow.db`; no Compose, o SQLite fica no volume Docker. Nunca versione `.env` ou segredos reais. Troque `JWT_SECRET` por um valor forte fora do ambiente local.

## API

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `GET|POST /api/v1/tasks`
- `GET|PATCH|DELETE /api/v1/tasks/{id}`
- `GET|POST /api/v1/subjects`, `GET /api/v1/subjects/stats` e `GET|PATCH|DELETE /api/v1/subjects/{id}`
- `GET|POST /api/v1/goals`, `PATCH /api/v1/goals/{id}` e `DELETE /api/v1/goals/{id}`
- `GET|POST /api/v1/study-sessions` e `DELETE /api/v1/study-sessions/{id}`
- `GET /api/v1/dashboard`
- `GET /api/v1/calendar`
- `GET /api/v1/history`
- `GET /api/v1/notifications`
- `PATCH /api/v1/notifications/{id}/read`
- `PATCH /api/v1/users/me`
- `POST /api/v1/users/me/password`
- `DELETE /api/v1/users/me`
- `GET /health`

Documentação interativa: `http://localhost:8000/api/docs`.

Ao excluir uma meta ou disciplina, as tarefas vinculadas também são excluídas e deixam de aparecer na visão geral. A atividade recente e o histórico de sessões permitem excluir seus registros; sessões em andamento ou pausadas precisam ser finalizadas ou canceladas antes. O card Pendentes conta somente tarefas com status `PENDING`, e o card de próximos passos permite apagar pendências antigas que ficaram sem vínculo.

### Fluxo de atualização e sessão

As telas autenticadas mantêm o JWT em `localStorage` e validam a sessão em `/auth/me` antes de renderizar o conteúdo. Assim, F5 e Ctrl+R não encerram uma sessão válida; tokens inválidos ou expirados continuam levando o usuário ao login. O backend normaliza URLs SQLite relativas para um caminho consistente.

A tela de Disciplinas usa `POST /api/v1/subjects` seguido de reconciliação com `GET /api/v1/subjects` e `GET /api/v1/subjects/stats`. A lista mostra estado de carregamento antes de exibir a mensagem vazia, preserva os dados anteriores em caso de erro e protege as respostas contra condições de corrida. O botão compacto “Atualizar dados” faz uma nova busca apenas da tela atual.

Tarefas, metas e sessões podem ser vinculadas a uma disciplina pelo campo “Disciplina (opcional)” no cadastro. O frontend envia `subject_id`, e o backend valida a propriedade do registro antes de salvar. Ao abrir uma disciplina, seus dados relacionados são carregados novamente do backend.

Na inicialização, o backend também normaliza prioridades gravadas por versões antigas (`LOW`, `MEDIUM`, `HIGH`) para o formato interno do ORM. O calendário organiza prazos e sessões por dia; a atividade recente aparece na Visão geral, evitando uma aba de histórico que repetia parte da lista de sessões. Avisos são gerados para tarefas e metas que vencem nos próximos três dias ou já venceram, quando a preferência de notificações está ativa.

Sessões de estudo usam o fluxo persistente de iniciar, pausar, retomar, finalizar ou cancelar. O estado fica no backend, uma única sessão ativa é permitida por usuário e a duração é calculada por timestamps, sem depender da frequência do `setInterval` do navegador. As sessões concluídas alimentam a disciplina, o dashboard, o histórico, o calendário e as metas configuradas para tempo de estudo.

A Visão geral acompanha uma meta semanal de estudo, contabilizada automaticamente pelas sessões concluídas desde segunda-feira. O padrão é 300 minutos (5 horas), ajustável entre 30 e 4200 minutos nas preferências da conta. Ao finalizar uma sessão, a pessoa também pode selecionar uma tarefa pendente ou em andamento para marcá-la como concluída.

## Testes

```bash
cd backend
pytest
```

O pipeline de CI executa validação Python, testes backend e build TypeScript do frontend em cada push ou pull request.

## Escopo e próximos passos

O MVP local inclui autenticação, tarefas com prazo, disciplinas, metas, sessões cronometradas, calendário mensal, avisos, preferências de conta e visão geral com atividade recente. Para uma publicação corporativa ainda precisam ser definidos o serviço de banco de dados, o contrato da API SQL por procedures, as credenciais e o ambiente de implantação. Refresh tokens, rate limiting distribuído e auditoria operacional também ficam para essa etapa.
