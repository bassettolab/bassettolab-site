# BassettoLab — analytics privado

Esta aplicação FastAPI deve ser hospedada em um servidor com HTTPS (não roda no GitHub Pages).
Armazena somente URL, título e timestamp de cada visualização; não armazena IP, fingerprint ou email de visitantes.

## Configuração

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export SITE_ORIGIN=https://bassettolab.com
export PUBLIC_URL=https://analytics.bassettolab.com
export ADMIN_EMAILS=SEU_EMAIL_GOOGLE
export SESSION_SECRET="$(openssl rand -hex 32)"
export GOOGLE_CLIENT_ID=ID_DO_OAUTH
export GOOGLE_CLIENT_SECRET=SEGREDO_DO_OAUTH
export ANALYTICS_DB=/var/lib/bassettolab/analytics.sqlite3
uvicorn app:app --host 127.0.0.1 --port 8090 --proxy-headers
```

No Google Cloud Console, crie um cliente OAuth para aplicação web e cadastre
`https://analytics.bassettolab.com/auth` como URI de redirecionamento.
Configure um proxy HTTPS (Caddy) para a porta 8090, e defina o domínio DNS.
Nunca grave credenciais no repositório. Use systemd com EnvironmentFile protegido.

Em `hugo.yaml`, configure `params.analytics.endpoint` com
`https://analytics.bassettolab.com` somente após colocar a API em produção.
O painel ficará em `https://analytics.bassettolab.com/admin`.
Não disponibilize `/api/stats` sem autenticação. Os dados começam a contar após ativação.

O registro conta carregamentos de página, não usuários únicos.
