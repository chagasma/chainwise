# Chainwise — Planejamento Inicial

> Assistente de IA configurável para explicar e diagnosticar transações EVM e contratos Solidity.
> Desafio: AnyChain Transaction Assistant (CloudWalk Nimbus 1.4)

---

## 0. Status Atual (checkpoint — última atualização: 2026-08-20)

**Backend é o foco atual; frontend fica pra depois.** Tudo abaixo já está implementado,
testado (unitário + validado ao vivo contra APIs reais) e commitado em `main`.

### O que já funciona

- **Pipeline completo `GET /tx/{hash}/explain`**: Blockscout → enrichment de tokens via RPC →
  repo grounding (fallback de ABI) → LangGraph → OpenRouter → explicação em linguagem natural
  com citação de fontes. Validado ponta a ponta com transações reais no Ethereum mainnet e na
  Polygon PoS.
- **Config-driven portability comprovada**: troquei `CHAINWISE_NETWORK` entre `ethereum-mainnet`
  e `polygon-pos` sem tocar em código e o pipeline inteiro funcionou (explorer, RPC, LLM).
  `gnosis-chain` tem RPC funcionando, mas o explorer oficial (`gnosis.blockscout.com`) está
  fora do ar agora (redirecionando pra `gnosisscan.io`, que não é Blockscout-compatible) — ver
  "Problemas conhecidos" abaixo. Isso não é bug nosso: validamos que o `BlockscoutClient`
  degrada graciosamente (502 com mensagem clara) exatamente como devia.
- **Adapters** (`adapters/`): `BlockscoutClient` (tx/receipt/logs), `RPCClient` (`eth_call` via
  JSON-RPC puro, sem `web3.py`), `GitHubClient` (code search + file contents). Todos herdam
  `adapters/base.py::HttpAdapter` (lifecycle do `httpx.Client` + context manager) e seguem o
  mesmo padrão: client HTTP burro, erros tipados (`AdapterError`/`AdapterNotFoundError` e
  subclasses por adapter), tratados uniformemente em `api/routes.py::_translate_adapter_error`.
  Retries automáticos em falha de conexão via `httpx.HTTPTransport(retries=2)` (nativo do httpx,
  não custom) em produção; testes sempre injetam `httpx.MockTransport`, então nunca retryam de
  verdade.
- **Enrichment de tokens** (`services/enricher.py`): resolve `symbol`/`decimals` ERC-20 via
  `eth_call`, decodificação ABI feita na mão (sem `eth_abi` — só 2 tipos primitivos), com
  bounds-check contra resposta vazia (`"0x"`) mascarando falha como sucesso.
- **Repo grounding / fallback de ABI** (`services/decoder.py` + `services/repo_grounding.py`):
  quando a Blockscout não decodifica (`decoded_input is null`), busca artefatos ABI nos repos
  configurados por rede (aceita ABI array puro, artifact Truffle/Hardhat, e `solc
  --combined-json abi` com múltiplos contratos por arquivo), calcula selectors via `keccak256`
  de verdade (`eth-utils`/`eth-abi`, com fallback de assinatura canônica recursivo pra structs/
  tuples), decodifica o calldata e cita o arquivo exato no GitHub. Precisa de `GITHUB_TOKEN`
  pra funcionar de verdade (a API de code search do GitHub exige auth) — sem token, degrada
  graciosamente pra "sem grounding" (log em `info`, não crasha nada).
- **Agent** (`agent/`): grafo LangGraph com 2 nós (`explain`/`diagnose`, ramificados por
  `reverted`), checkpointer Postgres, LLM via OpenRouter (`langchain_openai.ChatOpenAI`). Ver
  ADR 0002 pra justificativa completa.
- **Config de rede**: `ethereum-mainnet`, `gnosis-chain`, `polygon-pos` (YAML por rede, ver
  ADR 0001). `NetworkConfig` é `frozen` com campos `tuple` (não `list`) — precisa ser hashável
  pro cache abaixo poder usar `network` como parte da chave.
- **Cache local** (`chainwise/cache.py::ttl_cache`): TTL cache simples (dict + lock, sem
  dependência nova) aplicado em `_get_transaction_summary` (30s) — evita bater na Blockscout de
  novo pra `/tx/{hash}` e `/tx/{hash}/explain` na mesma janela curta. Erros nunca são cacheados
  (só sucesso). Isolamento de teste garantido por um `autouse fixture` em `tests/conftest.py` que
  limpa o cache antes de cada teste.
- **Docker Compose cobrindo o backend**: `docker-compose.yml` agora sobe `postgres` + `backend`
  juntos (`make up` / `make down`), com `backend` lendo `src/backend/.env` (opcional) e a URL do
  Postgres sobrescrita pro nome do serviço (`postgres:5432`) dentro da rede do compose. Porta do
  Postgres no host é configurável via `CHAINWISE_PG_PORT` (default `5432`) pra não colidir com
  outro Postgres local — validei ao vivo com `CHAINWISE_PG_PORT=5433 docker compose up`
  (`/` e `/network` respondendo, checkpointer conectando via nome de serviço).
- **Modos developer/support/auditor** (`?mode=` em `/tx/{hash}/explain`, default `developer`):
  não é um branch novo no grafo — `MODE_ADDENDA` em `agent/prompts.py` é só texto extra
  concatenado ao prompt (`explain`/`diagnose`) já escolhido por `reverted`, injetado em
  `_run_llm_node` a partir de `state["mode"]`. `support` tira jargão técnico; `auditor` pede pra
  sinalizar explicitamente padrões sensíveis (approvals, ownership/admin, delegatecall/proxy) e
  dizer quando nenhum foi encontrado, em vez de simplesmente omitir a seção. Cada modo não-padrão
  isola sua própria conversa no checkpointer (`thread_id = f"{tx_hash}:{mode}"`) pra não misturar
  histórico com o modo `developer` (que mantém `thread_id == tx_hash` pra não quebrar checkpoints
  existentes). Validado ao vivo nos 3 modos contra a mesma tx real — `auditor` de fato sinalizou o
  padrão `execute(bytes)` como sensível e disse explicitamente que não achou troca de ownership.
- **Bug real achado testando manualmente** (não pelos testes automatizados): a Blockscout às
  vezes manda `revert_reason` como objeto decodificado (erro customizado do Solidity, mesmo shape
  do `decoded_input`), não como string — `TransactionSummary` só aceitava string e 502ava.
  Corrigido em `api/schemas.py::_revert_reason`. Reforça que testes mockados não substituem bater
  numa API real de vez em quando.
- **76 testes** (unitários, tudo mockado via `httpx.MockTransport`/fakes — nenhum teste bate em
  rede real), lint (`ruff`) e typecheck (`pyright`) limpos. Rodar com `make check`.
- **4 revisões de qualidade de código** já passaram por essa base (via skill `code-quality`) —
  achados corrigidos: deduplicação de erro/network lookup nas rotas, bug real de decode ABI
  vazio, layering de `TokenMetadata`, `GitHubRateLimitedError` sem uso real, e (4ª rodada,
  focada no nó `diagnose` recém-adicionado): `_explain`/`_diagnose` duplicados viraram um
  `_run_llm_node` único com `functools.partial`; `close`/`__enter__`/`__exit__` idênticos nos 3
  adapters viraram `adapters/base.py::HttpAdapter`; o contrato do payload JSON duplicado nos dois
  system prompts virou `_PAYLOAD_CONTRACT` compartilhado em `agent/prompts.py`;
  `explain_transaction` em `api/routes.py` foi quebrado em `_build_prompt_payload`/`_run_agent`;
  `NetworkConfig.abi_strategy` (que existia mas nunca era lido) agora é checado de fato antes de
  chamar `ground_transaction`; `RPCClient.get_code` (código morto, sem chamador) foi removido.

### O que falta (nessa ordem sugerida)

1. ~~**Failure diagnostics estruturado**~~ — feito: `agent/graph.py` agora tem 2 nós
   (`explain`/`diagnose`) com edge condicional a partir de `START`, ramificando em
   `state["reverted"]` (setado em `routes.py` a partir de `summary.status == "reverted"`).
   `agent/prompts.py::DIAGNOSE_SYSTEM_PROMPT` estrutura a resposta em o que foi tentado / causa
   provável / próximos passos, deixando claro quando a causa é inferência (sem `revert_reason`
   do explorer) em vez de fato. Testado em `tests/test_agent.py`.
2. ~~**Cache local + retries nos adapters**~~ — feito: `chainwise/cache.py::ttl_cache` (30s) em
   `_get_transaction_summary`; `httpx.HTTPTransport(retries=2)` como transport padrão em todos os
   adapters. Ver seção "O que já funciona".
3. ~~**Docker Compose cobrindo o backend**~~ — feito: `make up`/`make down`. Ver seção "O que já
   funciona".
4. **Gnosis Chain** — reconferido em 2026-08-20: RPC ok, explorer (`gnosis.blockscout.com`)
   continua redirecionando (301) pra `gnosisscan.io`, não Blockscout-compatible. Segue bloqueado
   por serviço externo, não por código nosso.
5. **Bônus** (em andamento, um de cada vez):
   - [x] Modos developer/support/auditor — feito (`?mode=` em `/tx/{hash}/explain`). Ver seção
     "O que já funciona".
   - [ ] Structured triage flow (perguntas esclarecedoras antes de concluir).
   - [ ] Multi-transaction analysis.
   - [ ] Gas optimization suggestions.
   - [ ] Security vulnerability detection baseada em padrões conhecidos — parcialmente coberto
     pelo modo `auditor` acima (sinaliza approvals/ownership/delegatecall inline na explicação),
     mas ainda não é uma feature dedicada com sua própria detecção estruturada.
6. **Frontend mínimo** — só existe um `.gitkeep` em `src/frontend/`. Deixado por último, depois
   do backend (core + bônus que entrarem) estar fechado.
7. **README + `docs/examples.md`** — setup, config, pelo menos 3 exemplos reais de
   query/output (já temos vários rodados ao longo do desenvolvimento pra reaproveitar, incluindo
   um caso de repo grounding real com `go-ethereum`).

### Problemas conhecidos

- `gnosis-chain.yaml` aponta pra `https://gnosis.blockscout.com`, que é a URL oficial
  documentada (confirmada via Chainlist e docs.gnosischain.com), mas está redirecionando (301)
  pra `gnosisscan.io` no momento — pode ser uma instabilidade temporária. Não mexi na config
  porque não é uma URL errada, é um serviço externo fora do ar agora. Vale reconferir antes de
  fechar o teste de portabilidade dessa rede.
- Repo grounding só encontra algo de verdade com `GITHUB_TOKEN` configurado (API do GitHub
  exige auth pra code search). Sem token, sempre degrada pra `grounding: null` — comportamento
  esperado e testado, só documentando pra não confundir num teste manual futuro.

### Referências rápidas

- ADR 0001 (`docs/adr/0001-*.md`): por que YAML por rede em vez de um `networks.yaml` único.
- ADR 0002 (`docs/adr/0002-*.md`): por que LangGraph (não uma chamada direta ao LLM) e por que
  OpenRouter (não um SDK de provedor específico).
- `make check` roda lint + typecheck + testes. `make db-up` sobe o Postgres do checkpointer
  (atenção: se a porta 5432 já estiver em uso por outro projeto local, suba um container avulso
  numa porta alternativa e aponte `CHAINWISE_DATABASE_URL` pra ela).

---

## 1. Contexto e Objetivo

Construir um assistente **network-agnostic** que recebe um hash de transação EVM e devolve uma explicação clara em linguagem natural, com diagnóstico de falhas quando aplicável. A mudança de rede (ex: Ethereum mainnet → CloudWalk private) deve ser feita apenas alterando arquivos de configuração.

O projeto será entregue como um repositório localmente executável, com README completo, exemplos reais e código bem estruturado.

---

## 2. Escopo do MVP

### Funcionalidades obrigatórias

- [x] **Transaction Explainer**: resumo de transação a partir do hash (chamadas, transfers, eventos). `GET /tx/{hash}/explain`, validado com txs reais em 2 redes.
- [x] **Failure Diagnostics**: diagnóstico de transações revertidas/falhas com causas prováveis e próximos passos. Nó `diagnose` dedicado em `agent/graph.py`, ramificado por `reverted` no state.
- [x] **Explorer Integration (Blockscout-compatible)**: busca de tx, receipt, logs e ABI via API configurável. `adapters/blockscout.py`.
- [x] **On-chain Context via RPC**: `eth_call` configurável para enriquecer contexto (`decimals`, `symbol` via `services/enricher.py`; `adapters/rpc.py` também expõe `eth_getCode` genérico).
- [x] **Smart Contract Repo Grounding**: integração com repositórios GitHub configurados para explicar funções e citar código-fonte. `adapters/github.py` + `services/decoder.py` + `services/repo_grounding.py`, validado ao vivo com `go-ethereum`.
- [ ] **Interface Simples**: API REST (FastAPI) pronta; frontend web minimalista ainda não iniciado (só `.gitkeep`).
- [x] **Config-driven Portability**: toda a configuração centralizada (explorer URL, RPC, repos, estratégia de ABI). Validada trocando de rede sem mudar código (ver seção 0).
- [x] **Grounded Answers**: toda resposta inclui citações/links para as fontes usadas (`source_url` do explorer + `source_url` do repo quando há grounding).
- [x] **Graceful Degradation**: o sistema continua funcionando mesmo quando ABI, RPC, explorer ou repo estão indisponíveis, informando claramente o que falta. Validado ao vivo com o explorer da Gnosis Chain fora do ar.
- [ ] **README**: setup, configuração e pelo menos 3 exemplos de queries/outputs.

### Funcionalidades bônus (se der tempo)

- [ ] Structured triage flow (perguntas esclarecedoras antes de concluir).
- [x] Modos de operação: developer / support / auditor.
- [ ] Multi-transaction analysis.
- [ ] Gas optimization suggestions.
- [ ] Security vulnerability detection baseada em padrões conhecidos (parcial via modo `auditor`).

---

## 3. Fora de Escopo (MVP)

- Suporte a redes não-EVM.
- Simulação de transações (`eth_call` com estado simulado complexo).
- Análise de traces completos (se não disponível via Blockscout).
- Deploy em produção/cloud.
- Autenticação e multi-tenancy.

---

## 4. Stack Tecnológica

| Camada | Tecnologia | Justificativa |
|--------|------------|---------------|
| Backend/API | Python + FastAPI | Produtividade, ecossistema maduro, async nativo. |
| Blockchain | `httpx` (JSON-RPC puro) + `eth_abi`/`eth_utils` | Chamadas EVM (`eth_call`) via HTTP direto, sem `web3.py` inteiro; decodificação de ABI real (selectors via `keccak256`, `eth_abi.decode`) só onde precisamos (repo grounding). |
| LLM | OpenRouter | Acesso a múltiplos modelos (GPT-4o, Claude, DeepSeek, etc.) com uma única API. |
| Agent/Pipeline | **LangGraph** | Decisão revista: o roadmap tem branches reais (triage, modos, multi-tx), então um grafo com nós/edges explícitos + checkpointing embutido ganhou de um pipeline customizado. Ver ADR 0002. |
| Cache/Storage | Postgres (checkpoints do LangGraph) + `chainwise/cache.py::ttl_cache` (in-memory, sem dependência nova) pra resposta da Blockscout. |
| Frontend | Next.js ou HTML+JS simples | Web preferencial, mas pode ser minimalista. |
| Configuração | Pydantic Settings + YAML/`.env` | Centralizada, tipada e validada. |
| Testes | pytest | Testes unitários e de integração. |
| Containerização | Docker + docker compose | Facilita execução local. |

---

## 5. Arquitetura de Alto Nível

> Diagrama do desenho original — os nomes de módulo mudaram na implementação real
> (`workflow.py` → `agent/graph.py`, sem `token_detector`/`explainer` como arquivos próprios,
> sem cache SQLite ainda). Ver seção 6 para a estrutura real e seção 0 para o status atual.

```
┌─────────────────┐
│   Frontend      │  (Next.js / HTML+JS)
│  (input hash)   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Backend — FastAPI                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   API Layer │  │   Services  │  │  Adapters           │  │
│  │  - routes   │──│  - decoder  │──│  - blockscout       │  │
│  │  - schemas  │  │  - enricher │  │  - rpc_client       │  │
│  └─────────────┘  │  - explainer│  │  - github_repo      │  │
│                   │  - token    │  └─────────────────────┘  │
│                   │    detector │                           │
│                   └─────────────┘                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │    Agent    │  │    Config   │  │  Cache/Storage      │  │
│  │  - workflow │  │  - settings │  │  - SQLite           │  │
│  │  - prompts  │  │  - networks │  │  - ABI cache        │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│              External Data Sources                          │
│  Blockscout API  │  RPC Endpoint  │  GitHub API  │ OpenRouter│
└─────────────────────────────────────────────────────────────┘
```

### Princípios aplicados

- **Separação de concerns**: adapters sabem falar com APIs externas; services contêm a lógica de negócio; API layer expõe endpoints.
- **Config-driven**: nenhuma URL de rede ou credencial hardcoded.
- **Resilience**: timeouts, retries, circuit breakers e cache nos adapters.
- **Grounded answers**: todo dado usado pelo LLM é rastreável até sua fonte.
- **Graceful degradation**: cada fonte de dados é opcional; a resposta indica o que faltou.

---

## 6. Estrutura de Pastas Proposta

```
chainwise/
├── README.md                      # Setup, config e exemplos
├── LICENSE
├── Makefile                       # Comandos úteis (run, test, lint)
├── docker-compose.yml             # Opcional: backend + frontend
├── .env.example                   # Template de variáveis de ambiente
├── .gitignore
│
├── docs/
│   ├── nimbus.md                  # Desafio original (conteúdo do site)
│   ├── planning.md                # Este documento
│   ├── architecture.md            # Arquitetura detalhada (a ser criado)
│   ├── decisions.md               # Decision log (a ser criado)
│   └── examples.md                # Exemplos de queries/outputs
│
├── src/
│   ├── backend/
│   │   ├── pyproject.toml         # Dependências Python (uv)
│   │   ├── uv.lock
│   │   ├── Dockerfile
│   │   ├── .env.example
│   │   ├── chainwise/             # Pacote Python principal
│   │   │   ├── __init__.py
│   │   │   ├── main.py            # Entrypoint FastAPI (lifespan monta o grafo + checkpointer)
│   │   │   ├── config/
│   │   │   │   ├── settings.py    # Pydantic Settings (.env)
│   │   │   │   ├── network.py     # NetworkConfig + load_network()
│   │   │   │   └── networks/      # Um YAML por rede (ver ADR 0001)
│   │   │   │       ├── ethereum-mainnet.yaml
│   │   │   │       ├── gnosis-chain.yaml
│   │   │   │       └── polygon-pos.yaml
│   │   │   ├── api/
│   │   │   │   ├── routes.py      # Endpoints HTTP + get_network/get_graph deps
│   │   │   │   └── schemas.py     # Response models (TransactionSummary, ExplanationResponse, ...)
│   │   │   ├── adapters/          # Clientes HTTP "burros" — sem interpretação de dados
│   │   │   │   ├── errors.py      # AdapterError/AdapterNotFoundError (base comum)
│   │   │   │   ├── blockscout.py  # Cliente Blockscout v2 (tx, receipt, logs)
│   │   │   │   ├── rpc.py         # Cliente JSON-RPC puro (eth_call, eth_getCode)
│   │   │   │   └── github.py      # Code search + file contents da API do GitHub
│   │   │   ├── services/          # Lógica de negócio, independente de framework web
│   │   │   │   ├── enricher.py    # Metadata ERC-20 (symbol/decimals) via RPC
│   │   │   │   ├── decoder.py     # Matemática de ABI: selectors, canonical signature, decode
│   │   │   │   └── repo_grounding.py  # Busca+match de artefato ABI nos repos configurados
│   │   │   ├── agent/
│   │   │   │   ├── graph.py       # Grafo LangGraph (hoje: 1 nó "explain")
│   │   │   │   ├── llm.py         # ChatOpenAI apontado pro OpenRouter
│   │   │   │   ├── prompts.py     # System prompt
│   │   │   │   └── checkpointer.py  # PostgresSaver do LangGraph
│   │   │   ├── models/
│   │   │   │   └── domain.py      # DTOs compartilhados entre services e api (TokenMetadata, DecodedCall, RepoGroundingResult)
│   │   │   └── observability/
│   │   │       ├── logging.py     # Logging estruturado (JSON)
│   │   │       └── middleware.py  # Request context (request_id, etc.)
│   │   └── tests/                 # 1 arquivo de teste por módulo, tudo mockado (httpx.MockTransport)
│   │
│   └── frontend/
│       └── .gitkeep                # Ainda não iniciado — próximo bloco depois do backend
│
└── scripts/                        # Ainda não criado
```

### Notas sobre a estrutura

- `src/`: agrupa todo o código-fonte da aplicação (backend + frontend) em um único lugar, separado de documentação e configuração de repo.
- `src/backend/chainwise/`: pacote Python principal. Fica diretamente em `backend/` (sem `src/` aninhado) para manter imports simples e compatíveis com `pyproject.toml`.
- `adapters/`: cada fonte de dados externa tem seu próprio adapter com interface clara — client HTTP burro, retorna dado cru, erros tipados por adapter (todos herdam de `AdapterError`/`AdapterNotFoundError`).
- `services/`: lógica pura, independente de framework web. `token_detector.py`/`explainer.py` do desenho original acabaram não virando arquivos separados — a detecção de transfer ficou inline em `api/routes.py` (é um one-liner) e a montagem do prompt virou o próprio `LLMPromptPayload` em `api/schemas.py`.
- `agent/`: orquestração do grafo LangGraph e prompts (o `workflow.py` do desenho original virou `graph.py`).
- `models/domain.py`: existe especificamente para DTOs que tanto `services/` quanto `api/` precisam — evita um ciclo de import entre as duas camadas (ver histórico de commits do `repo_grounding`/`enricher` pra contexto).
- `infrastructure/cache.py` do desenho original virou `chainwise/cache.py` (fora de
  `infrastructure/`, que nunca existiu como pasta própria) — `ttl_cache`, aplicado hoje só na
  resposta da Blockscout, não em ABI.
- `docs/`: centraliza toda a documentação do projeto, incluindo os ADRs (`docs/adr/`).

---

## 7. Fluxo de Dados de uma Requisição

> Também do desenho original. O fluxo real de hoje: Blockscout (tx+logs) → filtro de Transfer
> nos logs já decodificados → `enricher.enrich_tokens` (RPC, se houver Transfers) →
> `repo_grounding.ground_transaction` (só se `decoded_input` for null) → `LLMPromptPayload` →
> `graph.invoke` (LangGraph → OpenRouter). Não há chamadas em paralelo ainda (passo 4/5 abaixo
> são sequenciais na implementação real) nem diagnóstico como etapa separada (passo 10).

```
1. Usuário envia tx_hash via frontend
        ↓
2. FastAPI recebe e valida o request
        ↓
3. Workflow inicia o pipeline
        ↓
4. adapters.blockscout busca tx, receipt, logs e ABI (paralelo)
        ↓
5. adapters.rpc faz eth_call(s) para contexto adicional (paralelo)
        ↓
6. services.decoder decodifica input e logs usando ABI
        ↓
7. services.token_detector identifica tokens e transfers
        ↓
8. services.repo_grounding busca código-fonte relevante no GitHub
        ↓
9. services.explainer monta contexto estruturado e chama LLM
        ↓
10. Resposta grounded (com explicação, diagnóstico e citações) retorna ao usuário
```

### Cenários de fallback

| Fonte indisponível | Comportamento |
|-------------------|---------------|
| Explorer fora | Usar RPC para tx/receipt; informar limitação. |
| Sem ABI | Mostrar input hex cru; não decodificar parâmetros. |
| RPC fora | Explicar com base no explorer apenas. |
| Repo fora | Explicar com base na ABI; sem link de código. |
| LLM fora | Retornar estrutura decodificada em JSON. |

---

## 8. Fases de Implementação

### Fase 1 — Fundação ✅
- [x] Configurar projeto Python (pyproject.toml, lint, pytest) — `uv`, `ruff`, `pyright`, `pytest`.
- [x] Criar estrutura base de pastas e módulos.
- [x] Implementar `config/settings.py` com Pydantic.
- [x] Criar schemas de request/response.

### Fase 2 — Adapters ✅
- [x] Implementar `blockscout.py` (tx, receipt, logs, ABI).
- [x] Implementar `rpc.py` (`eth_call`).
- [x] Implementar `github.py` (busca de código em repos configurados).
- [x] Implementar chamada ao LLM — `agent/llm.py` (`ChatOpenAI` apontado pro OpenRouter; não virou
      um adapter próprio porque já é a interface do LangChain, ver ADR 0002).
- [x] Adicionar cache local e retries — `chainwise/cache.py::ttl_cache` em
      `_get_transaction_summary`; `httpx.HTTPTransport(retries=2)` em todos os adapters.

### Fase 3 — Serviços Core ✅ (exceto explainer.py como arquivo próprio)
- [x] Implementar `decoder.py` (decodificação de funções via ABI — selectors, structs, calldata).
- [x] Detecção de token transfers — não virou `token_detector.py` separado, ficou inline em
      `api/routes.py` (filtro de 1 linha sobre os logs decodificados).
- [x] Implementar `enricher.py` (eth_call para contexto — symbol/decimals ERC-20).
- [x] Implementar `repo_grounding.py`.
- [x] Montagem de prompt e chamada LLM — não virou `explainer.py` separado, ficou em
      `api/routes.py` (`LLMPromptPayload` + `graph.invoke`).

### Fase 4 — Pipeline/Agent ✅
- [x] Implementar o grafo orquestrando o fluxo — `agent/graph.py` (LangGraph, não um `workflow.py`
      customizado — decisão revista, ver ADR 0002).
- [x] Implementar `prompts.py` com regras claras (grounding vs explorer, tokens, revert).
- [x] Adicionar graceful degradation em cada etapa — validado ao vivo (explorer fora do ar,
      GitHub sem token, RPC de token não-padrão).
- [x] Nó/branch dedicado de failure diagnostics para transações revertidas — `explain`/`diagnose`
      com edge condicional a partir de `START`.

### Fase 5 — API + Frontend (só API feita)
- [x] Criar endpoints FastAPI — `GET /`, `GET /network`, `GET /tx/{hash}`, `GET /tx/{hash}/explain`.
- [ ] Criar frontend minimalista — não iniciado.
- [ ] Integrar frontend com backend.

### Fase 6 — Documentação e Testes (parcial)
- [ ] Escrever README completo.
- [ ] Criar `docs/examples.md` com 3+ exemplos.
- [x] Adicionar testes unitários — 70 testes, tudo mockado (`httpx.MockTransport`), sem testes de
      integração batendo em rede real (validação real foi feita manualmente, ver seção 0).
- [x] Revisar config-driven portability com pelo menos 2 redes — Ethereum mainnet e Polygon PoS
      validadas ponta a ponta; Gnosis Chain com RPC validado, explorer pendente (fora do ar).
- [x] Criar docker compose cobrindo o backend — `postgres` + `backend` juntos, `make up`/
      `make down`, validado ao vivo (`docker compose build` + `up` + `/` e `/network` respondendo).

---

## 9. Critérios de Sucesso

O projeto será considerado pronto para envio quando:

- [x] Uma transação real pode ser explicada corretamente em linguagem natural.
- [x] Transações revertidas recebem diagnóstico útil — nó dedicado com causa provável +
      próximos passos, não mais só menção ao revert_reason.
- [x] A troca de rede é feita apenas editando configuração.
- [x] Toda resposta inclui fontes/links utilizados.
- [x] O sistema funciona mesmo com algumas fontes indisponíveis.
- [ ] O README permite que alguém rode o projeto localmente em poucos minutos — README ainda é
      o placeholder padrão.
- [ ] Existem pelo menos 3 exemplos documentados — não escritos em `docs/examples.md` ainda
      (mas já temos exemplos reais rodados ao longo do desenvolvimento pra reaproveitar).
- [x] O código está testado e bem estruturado — 67 testes, 3 rodadas de code-quality review
      já aplicadas.

---

## 10. Riscos e Mitigações

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| Rate limit de explorers | Alto | Cache agressivo, retries com backoff, múltiplas fontes quando possível. |
| ABI ausente ou incompleta | Médio | Fallback para repo, degradar para exibição de dados crus. |
| LLM alucinando | Alto | Prompt engineering, contexto estruturado, grounded answers obrigatórias. |
| Dependência de RPC pública | Médio | Documentar alternativas (Alchemy, Infura, QuickNode). |
| Escopo crescer demais | Alto | Foco no MVP; bônus só após o core funcionando. |
| Setup complexo para avaliadores | Alto | Docker compose, Makefile claro, README detalhado. |

---

## 11. Próximos Passos (guia de continuidade)

Ordem sugerida pra retomar o trabalho — foco continua 100% backend antes do frontend:

1. **Failure diagnostics estruturado** — adicionar um nó/branch no grafo LangGraph
   (`agent/graph.py`) que ativa quando `summary.status == "reverted"`, com um prompt dedicado a
   causa provável + próximos passos, em vez de depender só do `revert_reason` cru dentro do
   prompt único de hoje. É o item que falta pra fechar a Fase 4 e o critério de sucesso da
   seção 9.
2. **Fechar a validação de portabilidade da Gnosis Chain** — reconferir se
   `gnosis.blockscout.com` voltou ao ar; se não, decidir entre esperar ou trocar de explorer
   pra essa rede (ver "Problemas conhecidos" na seção 0).
3. **Frontend mínimo** — interface simples (web ou CLI) consumindo `GET /tx/{hash}/explain`.
4. **README + `docs/examples.md`** — setup, config de rede, 3+ exemplos reais (já rodamos vários
   ao longo do desenvolvimento, inclusive um caso de repo grounding real contra `go-ethereum`
   com token do GitHub — dá pra reaproveitar os outputs).
5. **Bônus, um de cada vez**: modos developer/support/auditor feito; structured triage flow,
   multi-transaction analysis, gas optimization, security vulnerability detection (dedicada, além
   do que o modo `auditor` já sinaliza inline) seguem. Ver seção 0 pro estado real e atualizado —
   esta seção é o guia de continuidade original, mantido só como histórico da priorização inicial.

Pra retomar rápido numa sessão nova: leia a seção 0 (status atual) primeiro, depois `git log
--oneline` pra ver a ordem real dos commits e suas mensagens (elas documentam a motivação de
cada decisão em detalhe). Os ADRs em `docs/adr/` cobrem as duas decisões arquiteturais mais
importantes já tomadas.
