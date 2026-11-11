# Executar e conferir o StudyFlow

## Primeira configuração no Windows

Na raiz do projeto, prepare o ambiente uma vez:

```powershell
python -m venv backend/.venv
backend/.venv/Scripts/python -m pip install -r backend/requirements.txt
cd frontend
corepack pnpm install --frozen-lockfile
cd ..
```

Node.js e Corepack/pnpm são necessários para a interface. Depois da configuração, o atalho **StudyFlow - Iniciar** inicia a API e o frontend e abre `http://localhost:5173`.

## Uso manual

Em um terminal, inicie a API:

```powershell
backend/.venv/Scripts/python -m uvicorn app.main:app --reload --app-dir backend
```

Em outro terminal, inicie a interface:

```powershell
cd frontend
corepack pnpm run dev
```

Abra `http://localhost:5173`. A documentação da API fica em `http://localhost:8000/api/docs`.

## Fluxo principal

1. Crie uma conta e entre.
2. Cadastre uma disciplina.
3. Crie uma tarefa com prazo e uma meta; as duas podem ser vinculadas à disciplina.
4. Abra **Calendário** para localizar os prazos e sessões por dia.
5. Abra **Avisos** para conferir lembretes próximos ou vencidos.
6. Inicie, pause e finalize uma sessão de estudo.
7. Confira estatísticas e atividade recente em **Visão geral**.
8. Abra **Conta e preferências** para atualizar perfil, tema, notificações ou senha.

## Docker

```powershell
docker compose up --build
```

Abra `http://localhost:5173`. O banco SQLite fica no volume `studyflow_data`. Para parar, use `Ctrl+C` e depois `docker compose down`; o volume permanece salvo.
