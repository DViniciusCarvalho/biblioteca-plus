# Biblioteca+ — Plataforma Distribuída de Gerenciamento de Biblioteca

Projeto da disciplina de Engenharia de Software / Sistemas Distribuídos.
Sistema de biblioteca feito com **microserviços em Python (FastAPI)**, banco **PostgreSQL**,
gateway **Nginx**, testes com **Pytest**, containers com **Docker Compose** e monitoramento
com **Prometheus + Grafana**.

> Para rodar o projeto e publicar em produção, leia o **[PASSO_A_PASSO.md](PASSO_A_PASSO.md)**.
> Documentos do projeto (relatório, segurança e casos de teste) estão na pasta `docs/`. Os campos em amarelo precisam ser preenchidos pelo grupo.

## Arquitetura

```
Usuário → Gateway (Nginx :8080) → Microserviço → PostgreSQL
                                     │
   usuarios ── livros ── emprestimos ── notificacoes      (comunicação HTTP/REST)
                              │
                 Prometheus (coleta /metrics) → Grafana
```

| Serviço | Responsabilidade | Rotas principais |
|---|---|---|
| `servico_usuarios` | Cadastro, login (JWT), dados do usuário | `POST /usuarios`, `POST /login`, `GET/PUT /usuarios/{id}` |
| `servico_livros` | Cadastro, consulta, atualização, disponibilidade | `POST/GET /livros`, `GET/PUT /livros/{id}` |
| `servico_emprestimos` | Empréstimos, devoluções, histórico | `POST/GET /emprestimos`, `POST /emprestimos/{id}/devolucao` |
| `servico_notificacoes` | Simula avisos e guarda o histórico | `GET /notificacoes` |
| `gateway` | Porta única de entrada, encaminha para os serviços | — |
| `banco` | PostgreSQL | — |

Todos os serviços também têm `GET /saude` (verificação de funcionamento) e `GET /metrics` (Prometheus).

## Estrutura de pastas

```
biblioteca-plus/
├── docker-compose.yml          # sobe tudo com um comando
├── .env.example                # modelo das configurações (copiar para .env)
├── requirements-dev.txt        # pytest, ruff, black, locust...
├── PASSO_A_PASSO.md            # como executar e publicar
├── banco_de_dados/
│   ├── 01_schema.sql           # criação das tabelas
│   └── 02_dados_exemplo.sql    # livros de exemplo
├── gateway/nginx.conf
├── monitoramento/              # prometheus.yml e datasource do Grafana
├── servico_usuarios/           # cada serviço tem a mesma estrutura:
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py             #   rotas
│   │   ├── database.py         #   conexão com o banco
│   │   └── seguranca.py        #   senha e token
│   └── tests/                  #   testes unitários
├── servico_livros/
├── servico_emprestimos/        # tem também app/clientes.py (chama outros serviços)
├── servico_notificacoes/
├── testes/
│   ├── test_integracao.py      # fluxo completo pelo gateway
│   ├── test_falhas.py          # derruba serviços de propósito (precisa de Docker)
│   ├── locustfile.py           # teste de carga
│   └── coletar_metricas.py     # cobertura, Ruff, Black, complexidade
├── metricas/                   # relatorio_metricas.md (gerado pelo script)
├── docs/
│   ├── Relatorio_Final.docx
│   ├── Documentacao_de_Seguranca.docx
│   ├── Casos_de_Teste.docx
│   └── diagramas/              # arquitetura.png, modelo_dados.png (+ fontes .dot)
└── .github/workflows/ci.yml    # GitHub Actions
```

Os arquivos `database.py` e `seguranca.py` se repetem em cada serviço **de propósito**:
cada microserviço é independente e não compartilha código com os outros.

## Requisitos do documento → onde estão

| Requisito | Onde |
|---|---|
| RF01 cadastrar usuários / RF11 atualizar usuários | `POST /usuarios`, `PUT /usuarios/{id}` |
| RF02 autenticar | `POST /login` (devolve token JWT) |
| RF03 cadastrar livros / RF12 atualizar livros | `POST /livros`, `PUT /livros/{id}` |
| RF04 consultar livros / RF05 disponibilidade | `GET /livros` (campo `disponivel`) |
| RF06 empréstimo / RF08 impedir indisponível | `POST /emprestimos` (erro 409 se indisponível) |
| RF07 devolução | `POST /emprestimos/{id}/devolucao` |
| RF09 registrar operações | logs de cada serviço (`docker compose logs`) |
| RF10 consultar empréstimos / RF13 histórico | `GET /emprestimos` (filtro opcional `?status=`) |
| RF14 cancelar empréstimo | `POST /emprestimos/{id}/cancelar` (só nas primeiras 24h) |
| RF15 notificações | criadas automaticamente; consulta em `GET /notificacoes`; aviso de vencimento em `POST /emprestimos/lembretes/gerar` |
| RN01 exige login | rotas de empréstimo exigem token |
| RN02 / RN04 livro indisponível | `POST /livros/{id}/reservar` só funciona se o livro estiver livre |
| RN03 limite de empréstimos | variável `MAX_EMPRESTIMOS` (padrão 3) |

## Decisões para manter o código simples

- **SQL puro** com `psycopg2` (sem ORM).
- **Um banco PostgreSQL** com tabelas separadas por serviço; um serviço nunca lê a tabela do outro, só conversa por API.
- **Login com JWT**: o serviço de usuários cria o token; os demais só validam (mesmo `JWT_SECRET`).
- **Sem perfis de administrador**: qualquer usuário logado pode cadastrar/editar livros. A consulta de livros é pública.
- **Empréstimo de 14 dias**, limite de 3 ativos por usuário, cancelamento permitido em até 24h.
- **Tolerância a falhas**: se o serviço de livros cair, o de empréstimos responde `503`; se o de notificações cair, o empréstimo continua funcionando.
- **Sem duplicação de empréstimo**: o `UPDATE ... WHERE disponivel = TRUE` e um índice único no banco garantem que dois usuários nunca peguem o mesmo livro ao mesmo tempo.
