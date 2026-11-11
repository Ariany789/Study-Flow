# API

Base local: `http://localhost:8000/api/v1`.

No modo local, a API persiste usuários, hashes de senha e dados da aplicação no SQLite configurado em `DATABASE_URL`. Não há integração com Supabase nem com a API corporativa de SQL nesta versão.

## Autenticação

`POST /auth/register` recebe `name`, `email` e `password`; `POST /auth/login` recebe `email` e `password`. Ambos retornam `access_token`, `token_type` e `user`. Envie o token protegido como `Authorization: Bearer <token>`.

`GET /auth/me` retorna a conta autenticada.

## Tarefas

- `POST /tasks`: cria tarefa com `title`, `description`, `status`, `priority` e `due_date`.
- `GET /tasks`: lista tarefas próprias; aceita `status`, `priority` e `search`.
- `GET /tasks/{id}`: consulta tarefa própria.
- `PATCH /tasks/{id}`: atualiza campos permitidos.
- `DELETE /tasks/{id}`: remove tarefa própria.

Status: `PENDING`, `IN_PROGRESS`, `COMPLETED`. Prioridade: `LOW`, `MEDIUM`, `HIGH`.

## Disciplinas

- `POST /subjects`: cria uma disciplina com nome, descrição, cor, código, período, status e datas opcionais.
- `GET /subjects`: lista somente as disciplinas do usuário autenticado.
- `GET /subjects/stats`: retorna totais, disciplinas ativas, em andamento, concluídas e atrasadas.
- `GET /subjects/{id}`: retorna o detalhe da disciplina, progresso calculado pelas tarefas concluídas, minutos estudados, tarefas relacionadas e metas relacionadas.
- `PATCH /subjects/{id}`: atualiza a disciplina própria.
- `DELETE /subjects/{id}`: remove a disciplina própria, as tarefas e as metas vinculadas. Sessões ficam no histórico, sem vínculo com a disciplina.

Os vínculos de tarefas, metas e sessões validam a propriedade do usuário. O progresso da disciplina é calculado localmente a partir das tarefas associadas; os dados continuam no SQLite até a integração futura com Supabase.

Ao excluir uma disciplina, tarefas e metas vinculadas são excluídas em conjunto. Sessões de estudo são preservadas no histórico.

`DELETE /study-sessions/{id}` remove sessões concluídas ou canceladas. Sessões em andamento ou pausadas precisam ser finalizadas ou canceladas antes da exclusão. A exclusão recalcula metas de tempo vinculadas à disciplina.

## Metas de estudo

- `POST /goals`: cria uma meta de tarefas ou de tempo estudado.
- `GET /goals`: lista as metas da conta autenticada.
- `PATCH /goals/{id}`: atualiza uma meta própria.
- `DELETE /goals/{id}`: remove a meta da conta e também as tarefas vinculadas.

Documentação OpenAPI está disponível em `/api/docs` e `/api/redoc`.

## Produtividade e conta

`GET /dashboard`, `/calendar` e `/history` agregam indicadores, prazos e atividades do usuário autenticado. O dashboard retorna o tempo estudado na semana atual e a meta semanal em minutos. `PATCH /users/me` também aceita `weekly_study_goal_minutes` entre 30 e 4200. `GET /notifications` lista notificações próprias e cria lembretes para tarefas e metas com prazo vencido ou nos próximos três dias, se a pessoa tiver ativado os avisos. `PATCH /notifications/{id}/read` marca um aviso como lido. `PATCH /users/me` atualiza nome, email, tema (`light`, `dark` ou `system`) e preferência de notificações.

`POST /users/me/password` altera a senha mediante senha atual. `DELETE /users/me` exclui a conta, os dados acadêmicos e os registros de auditoria associados.
