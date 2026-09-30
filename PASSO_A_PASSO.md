# Passo a passo — Biblioteca+

Este guia tem duas partes: **rodar no seu computador** (partes 1 a 6) e **publicar em produção** (parte 7).

---

## 1. O que instalar antes

| Programa | Para quê | Onde baixar |
|---|---|---|
| **Docker Desktop** (Windows/Mac) ou Docker Engine (Linux) | Roda o projeto inteiro | https://www.docker.com/products/docker-desktop |
| **Git** | Versionamento e envio para o GitHub | https://git-scm.com |
| **Python 3.12** (opcional) | Só se quiser rodar os testes fora do Docker | https://www.python.org |

Depois de instalar o Docker Desktop, abra-o e espere ele ficar "running" (baleia verde/parada de piscar).

---

## 2. Rodar o projeto no seu computador

Abra o terminal (PowerShell no Windows) **dentro da pasta `biblioteca-plus`** e execute:

```bash
# 1) Criar o arquivo de configuração
cp .env.example .env

# 2) (Opcional) abra o .env e troque as senhas

# 3) Construir e subir tudo
docker compose up -d --build

# 4) Ver se está tudo rodando (todos devem aparecer como "running" / "healthy")
docker compose ps
```

A primeira vez demora alguns minutos (baixa as imagens). O banco de dados é criado sozinho:
os arquivos `banco_de_dados/01_schema.sql` e `02_dados_exemplo.sql` rodam automaticamente na primeira vez.

**Testar se funcionou:** abra no navegador `http://localhost:8080/saude` e `http://localhost:8080/livros`.
Você deve ver o status "ok" e a lista de 6 livros de exemplo.

### Endereços

| O quê | Endereço |
|---|---|
| API (gateway) | http://localhost:8080 |
| Documentação Swagger — Usuários | http://localhost:8001/docs |
| Documentação Swagger — Livros | http://localhost:8002/docs |
| Documentação Swagger — Empréstimos | http://localhost:8003/docs |
| Documentação Swagger — Notificações | http://localhost:8004/docs |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 (usuário `admin`, senha = `GRAFANA_PASSWORD` do `.env`) |

---

## 3. Usar o sistema (Roteiro de Teste RT01 e fluxo de empréstimo)

O jeito mais fácil é pelo **Swagger** (página `/docs`), sem precisar de programa nenhum:

1. Abra http://localhost:8001/docs → `POST /usuarios` → **Try it out** e envie:
   ```json
   { "nome": "João da Silva", "email": "joao@example.com", "senha": "Senha123" }
   ```
   Resultado esperado: **201** com "Cadastro realizado com sucesso" (é o **RT01** do documento).
   Enviar de novo o mesmo e-mail deve dar **409**.
2. Ainda no Swagger de usuários, `POST /login` com e-mail e senha. Copie o `access_token` da resposta.
3. Clique no botão **Authorize** (cadeado, no topo), cole o token e confirme.
4. Vá em http://localhost:8003/docs (empréstimos), clique em **Authorize** e cole o mesmo token
   (cada serviço tem seu Swagger, então o token precisa ser colado em cada um).
5. `POST /emprestimos` com `{ "livro_id": 1 }` → **201**. O livro passa a ficar indisponível.
6. Tente emprestar o mesmo livro de novo → **409 Livro indisponível**.
7. `POST /emprestimos/{id}/devolucao` → o livro volta a ficar disponível.
8. Em http://localhost:8004/docs (com o token) → `GET /notificacoes` mostra os avisos gerados.

**Pelo terminal (alternativa):** no Windows use `curl.exe` (sem o `.exe` o PowerShell usa outro comando):

```bash
curl.exe -X POST http://localhost:8080/usuarios -H "Content-Type: application/json" -d "{\"nome\":\"João da Silva\",\"email\":\"joao@example.com\",\"senha\":\"Senha123\"}"
curl.exe -X POST http://localhost:8080/login -H "Content-Type: application/json" -d "{\"email\":\"joao@example.com\",\"senha\":\"Senha123\"}"
curl.exe http://localhost:8080/livros
```

**Ver os logs (RF09):**
```bash
docker compose logs -f emprestimos      # logs de um serviço
docker compose logs -f                  # logs de todos
```

**Conferir os dados direto no banco:**
```bash
docker compose exec banco psql -U biblioteca_user -d biblioteca -c "SELECT * FROM usuarios;"
```
(use o usuário e o banco que estão no seu `.env`)

---

## 4. Testes e qualidade de código

Crie um ambiente virtual e instale as dependências (uma vez só):

```bash
python -m venv venv
venv\Scripts\activate            # Windows
# source venv/bin/activate       # Linux/Mac

pip install -r requirements-dev.txt
pip install -r servico_usuarios/requirements.txt -r servico_emprestimos/requirements.txt
```

**Testes unitários** (não precisam do Docker nem do banco) — rode um serviço por vez:

```bash
cd servico_usuarios      && python -m pytest -v && cd ..
cd servico_livros        && python -m pytest -v && cd ..
cd servico_emprestimos   && python -m pytest -v && cd ..
cd servico_notificacoes  && python -m pytest -v && cd ..
```

**Teste de integração** (precisa do sistema rodando com `docker compose up -d`):

```bash
python -m pytest testes/test_integracao.py -v
```

**Teste de carga** (sistema rodando):

```bash
locust -f testes/locustfile.py --host http://localhost:8080
```
Abra http://localhost:8089, coloque por exemplo 50 usuários e clique em Start. Tire prints dos gráficos para o relatório.

**Teste de falhas** (tolerância a falhas do documento) — derruba um serviço de propósito e confere a reação:
```bash
python -m pytest testes/test_falhas.py -v -s
```
Ou manualmente:
```bash
docker compose stop livros
# tente criar um empréstimo: deve responder 503 "Serviço de livros indisponível"
docker compose start livros
docker compose restart gateway
```

**Métricas de qualidade** (cobertura de testes, Ruff, Black e complexidade; não precisa de Docker):
```bash
python testes/coletar_metricas.py
```
O resultado aparece no terminal e é gravado em `metricas/relatorio_metricas.md`. Copie os números para a seção 8 do `docs/Relatorio_Final.docx`.

**Análise estática e formatação:**
```bash
ruff check .        # aponta erros e código sem uso
black .             # formata o código automaticamente
```
Rode o `black .` uma vez antes do primeiro commit para o passo de formatação do GitHub Actions ficar verde.

---

## 5. Monitoramento (Prometheus + Grafana)

1. Abra http://localhost:9090/targets — os 4 serviços devem estar **UP**.
2. Abra http://localhost:3000, entre com `admin` e a senha do `.env`.
3. Menu **Explore** (ou **Dashboards → New**) → fonte **Prometheus** já vem configurada.
4. Consultas úteis:
   - `http_requests_total` — total de requisições por serviço e rota
   - `rate(http_requests_total[1m])` — requisições por segundo
   - `http_request_duration_seconds_sum / http_request_duration_seconds_count` — tempo médio de resposta
   - `up` — 1 se o serviço está no ar, 0 se caiu (disponibilidade)

---

## 6. Enviar para o GitHub

```bash
git init
git add .
git commit -m "Projeto Biblioteca+"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/biblioteca-plus.git
git push -u origin main
```
Crie o repositório vazio no GitHub antes. O arquivo `.env` **não** vai junto (está no `.gitignore`) — ótimo, ele tem senhas.
Ao dar o push, a aba **Actions** do GitHub roda o pipeline (`.github/workflows/ci.yml`): análise, testes unitários e teste de integração.

---

## 7. Publicar em produção (servidor na nuvem)

A forma mais simples: alugar um **servidor Linux (VPS)**, instalar o Docker e rodar o mesmo `docker compose`.

### 7.1 Criar o servidor

Crie uma máquina virtual com **Ubuntu 24.04** e pelo menos **2 GB de RAM** em algum provedor
(por exemplo Oracle Cloud "Always Free", DigitalOcean, Hetzner, AWS Lightsail/EC2, Azure — alguns
têm créditos gratuitos para estudantes, como o GitHub Student Developer Pack).

No painel do provedor, libere no firewall as portas **22** (SSH), **80** (HTTP) e **443** (HTTPS, se for usar).
Anote o **IP público** do servidor.

### 7.2 Entrar no servidor e instalar o Docker

```bash
ssh usuario@IP_DO_SERVIDOR        # o usuário depende do provedor (ubuntu, root, opc...)

curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
exit                              # saia e entre de novo para valer o grupo
```

Firewall do próprio Ubuntu (opcional, mas recomendado):
```bash
sudo ufw allow OpenSSH
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

### 7.3 Baixar o projeto e configurar

```bash
git clone https://github.com/SEU_USUARIO/biblioteca-plus.git
cd biblioteca-plus
cp .env.example .env
nano .env
```

No `.env` de **produção**, troque:

| Variável | Valor |
|---|---|
| `POSTGRES_PASSWORD` | uma senha forte |
| `JWT_SECRET` | texto aleatório longo — gere com `openssl rand -hex 32` |
| `GRAFANA_PASSWORD` | uma senha forte |
| `GATEWAY_PORT` | `80` |

Salve no nano com `Ctrl+O`, `Enter`, `Ctrl+X`.

### 7.4 Subir

```bash
docker compose up -d --build
docker compose ps
```

Teste no seu navegador: `http://IP_DO_SERVIDOR/saude` e `http://IP_DO_SERVIDOR/livros`.

**Segurança já configurada:** só o gateway (porta 80) fica aberto para a internet.
Swagger (`/docs`), Prometheus e Grafana ficam presos ao `127.0.0.1` do servidor. Para vê-los do seu computador, use um túnel SSH:

```bash
ssh -L 3000:localhost:3000 -L 8001:localhost:8001 usuario@IP_DO_SERVIDOR
# enquanto o terminal estiver aberto, acesse http://localhost:3000 e http://localhost:8001/docs
```

### 7.5 Domínio e HTTPS (opcional)

1. No provedor de domínio, crie um registro **A** apontando `seudominio.com` para o IP do servidor.
2. No `docker-compose.yml`, troque a porta do gateway para `"127.0.0.1:8080:80"` e coloque `GATEWAY_PORT=8080` no `.env`.
3. Instale o Caddy, que cuida do certificado HTTPS sozinho:
   ```bash
   sudo apt install -y caddy
   echo "seudominio.com { reverse_proxy localhost:8080 }" | sudo tee /etc/caddy/Caddyfile
   sudo systemctl restart caddy
   docker compose up -d
   ```
4. Acesse `https://seudominio.com/livros`.

### 7.6 Atualizar a versão em produção

Depois de fazer `git push` no seu computador:
```bash
ssh usuario@IP_DO_SERVIDOR
cd biblioteca-plus
git pull
docker compose up -d --build
```

### 7.7 Comandos do dia a dia

```bash
docker compose ps                    # estado dos serviços
docker compose logs -f emprestimos   # logs
docker compose restart livros        # reiniciar um serviço
docker compose down                  # desligar (os dados do banco ficam guardados)

# Backup do banco
docker compose exec -T banco pg_dump -U biblioteca_user biblioteca > backup.sql
# Restaurar backup
docker compose exec -T banco psql -U biblioteca_user -d biblioteca < backup.sql
```

---

## 8. Problemas comuns

| Problema | Solução |
|---|---|
| `port is already allocated` | Outra coisa usa a porta. Mude `GATEWAY_PORT` no `.env` (ex.: 8081) ou feche o outro programa. |
| Serviço reinicia sem parar | `docker compose logs nome_do_servico` mostra o erro. |
| Mudei a senha do banco no `.env` e deu erro de senha | O banco só lê a senha na 1ª criação. Apague os dados e recrie: `docker compose down -v` e `docker compose up -d --build` (**apaga todos os dados**). |
| Alterei o `01_schema.sql` e nada mudou | Os `.sql` só rodam na 1ª criação. Use `docker compose down -v` (apaga dados) ou rode manualmente: `docker compose exec -T banco psql -U biblioteca_user -d biblioteca < banco_de_dados/01_schema.sql` |
| Erro `401 Token inválido` | O token expira em 60 minutos: faça `POST /login` de novo. |
| Erro `503` | O banco ou outro serviço está fora do ar. Veja `docker compose ps`. |
| Docker não abre no Windows | Ative a virtualização (WSL 2) — o instalador do Docker Desktop orienta. |

**Antes de entregar:** confira que o `.env` não foi para o GitHub, que o `docker compose up -d --build` funciona do zero
(`docker compose down -v` antes, para simular uma máquina nova) e guarde prints dos testes, do Grafana e do GitHub Actions para o relatório final.
