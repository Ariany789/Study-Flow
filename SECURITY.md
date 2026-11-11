# Segurança

- Senhas nunca são armazenadas em texto puro; são derivadas com PBKDF2 via Passlib.
- JWT possui expiração, algoritmo configurado e validação de assinatura.
- Toda operação de tarefa filtra também pelo `user_id`, evitando acesso entre contas.
- Schemas Pydantic rejeitam entradas inválidas e limitam tamanhos.
- CORS recebe origens explícitas por variável de ambiente.
- Endpoints protegidos filtram sempre pelo usuário autenticado, inclusive calendário, histórico e notificações.
- A API aplica headers básicos contra MIME sniffing, framing e referrer leakage.
- Segredos devem ser fornecidos por `.env` local ou secret manager; `.env` é ignorado pelo Git.
- Não registrar senhas, tokens ou segredos em logs.

Antes de produção, adicionar rate limiting nos endpoints de autenticação, HTTPS no reverse proxy, headers de segurança, migrations versionadas, rotação de segredo JWT e testes de segurança de dependências.
