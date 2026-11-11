# Arquitetura

O StudyFlow é separado em frontend React/Vite e backend FastAPI. O frontend acessa somente a API versionada em `/api/v1`; em desenvolvimento o Vite encaminha as chamadas para a API local e, no Docker, o Nginx encaminha as chamadas para o serviço `studyflow-api`. O backend valida entradas, autentica o usuário e aplica a autorização por proprietário antes de consultar os dados.

O modo local usa SQLite em `backend/studyflow.db`. No Docker, o SQLite fica no volume `studyflow_data`. A integração corporativa deve usar a API SQL e as procedures definidas pelo ambiente, e depende do contrato e das credenciais de acesso.

Fluxo de uma requisição protegida:

```text
Browser → API versionada → JWT → dependência de usuário → consulta com user_id → resposta
```

Calendário, avisos, metas, disciplinas e sessões seguem o mesmo fluxo, mantendo regras de negócio na API. A atividade recente é mostrada na visão geral; o calendário oferece uma navegação por mês e dia.
