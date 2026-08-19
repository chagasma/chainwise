# Chainwise — Planejamento Inicial

> Assistente de IA configurável para explicar e diagnosticar transações EVM e contratos Solidity.
> Desafio: AnyChain Transaction Assistant (CloudWalk Nimbus 1.4)

---

## 1. Contexto e Objetivo

Construir um assistente **network-agnostic** que recebe um hash de transação EVM e devolve uma explicação clara em linguagem natural, com diagnóstico de falhas quando aplicável. A mudança de rede (ex: Ethereum mainnet → CloudWalk private) deve ser feita apenas alterando arquivos de configuração.

O projeto será entregue como um repositório localmente executável, com README completo, exemplos reais e código bem estruturado.

---

## 2. Escopo do MVP

### Funcionalidades obrigatórias

- [ ] **Transaction Explainer**: resumo de transação a partir do hash (chamadas, transfers, eventos).
- [ ] **Failure Diagnostics**: diagnóstico de transações revertidas/falhas com causas prováveis e próximos passos.
- [ ] **Explorer Integration (Blockscout-compatible)**: busca de tx, receipt, logs e ABI via API configurável.
- [ ] **On-chain Context via RPC**: `eth_call` configurável para enriquecer contexto (ex: `decimals`, `symbol`, `balanceOf`).
- [ ] **Smart Contract Repo Grounding**: integração com repositórios GitHub configurados para explicar funções e citar código-fonte.
- [ ] **Interface Simples**: API REST (FastAPI) + frontend web minimalista.
- [ ] **Config-driven Portability**: toda a configuração centralizada (explorer URL, RPC, repos, estratégia de ABI).
- [ ] **Grounded Answers**: toda resposta inclui citações/links para as fontes usadas.
- [ ] **Graceful Degradation**: o sistema continua funcionando mesmo quando ABI, RPC, explorer ou repo estão indisponíveis, informando claramente o que falta.
- [ ] **README**: setup, configuração e pelo menos 3 exemplos de queries/outputs.

### Funcionalidades bônus (se der tempo)

- [ ] Structured triage flow (perguntas esclarecedoras antes de concluir).
- [ ] Modos de operação: developer / support / auditor.
- [ ] Multi-transaction analysis.
- [ ] Gas optimization suggestions.
- [ ] Security vulnerability detection baseada em padrões conhecidos.

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
| Blockchain | `web3.py`, `eth_abi`, `eth_utils` | Decodificação de ABI, eventos e chamadas EVM. |
| LLM | OpenRouter | Acesso a múltiplos modelos (GPT-4o, Claude, DeepSeek, etc.) com uma única API. |
| Agent/Pipeline | Pipeline customizado em Python | Fluxo determinístico e explícito; LangGraph pode ser overkill para esse escopo. |
| Cache/Storage | SQLite (local) + opcional Redis | Cache de ABI, código de contrato e respostas sem dependências externas pesadas. |
| Frontend | Next.js ou HTML+JS simples | Web preferencial, mas pode ser minimalista. |
| Configuração | Pydantic Settings + YAML/`.env` | Centralizada, tipada e validada. |
| Testes | pytest | Testes unitários e de integração. |
| Containerização | Docker + docker compose | Facilita execução local. |

---

## 5. Arquitetura de Alto Nível

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
│   │   ├── pyproject.toml         # Dependências Python
│   │   ├── requirements.txt       # Alternativa/congelamento
│   │   ├── Dockerfile
│   │   ├── .env.example
│   │   ├── chainwise/             # Pacote Python principal
│   │   │   ├── __init__.py
│   │   │   ├── main.py            # Entrypoint FastAPI
│   │   │   ├── config/
│   │   │   │   ├── __init__.py
│   │   │   │   └── settings.py    # Pydantic Settings + networks.yaml
│   │   │   ├── api/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── routes.py      # Endpoints HTTP
│   │   │   │   └── schemas.py     # Pydantic request/response models
│   │   │   ├── adapters/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── blockscout.py  # Cliente Blockscout v2
│   │   │   │   ├── rpc.py         # Cliente RPC (eth_call, etc.)
│   │   │   │   ├── github.py      # Busca de código em repos
│   │   │   │   └── openrouter.py  # Cliente LLM
│   │   │   ├── services/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── decoder.py     # Decodificação de ABI/input/logs
│   │   │   │   ├── token_detector.py  # Detecção ERC-20/721/1155
│   │   │   │   ├── enricher.py    # Coleta de contexto on-chain
│   │   │   │   ├── repo_grounding.py  # Grounding em repos GitHub
│   │   │   │   └── explainer.py   # Montagem do contexto + chamada LLM
│   │   │   ├── agent/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── workflow.py    # Pipeline de execução
│   │   │   │   └── prompts.py     # Prompts em Jinja2/string
│   │   │   ├── models/
│   │   │   │   ├── __init__.py
│   │   │   │   └── domain.py      # Modelos de domínio (Transaction, Log, etc.)
│   │   │   └── infrastructure/
│   │   │       ├── __init__.py
│   │   │       └── cache.py       # Cache local (SQLite/dict)
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── conftest.py
│   │       ├── test_adapters.py
│   │       ├── test_services.py
│   │       └── test_api.py
│   │
│   └── frontend/
│       ├── package.json
│       ├── Dockerfile
│       ├── src/
│       │   ├── app/
│       │   │   ├── page.tsx       # Tela principal
│       │   │   └── layout.tsx
│       │   └── components/
│       │       ├── TransactionInput.tsx
│       │       ├── ExplanationCard.tsx
│       │       └── SourceList.tsx
│       └── public/
│
└── scripts/
    └── setup.sh                   # Script de setup inicial
```

### Notas sobre a estrutura

- `src/`: agrupa todo o código-fonte da aplicação (backend + frontend) em um único lugar, separado de documentação e configuração de repo.
- `src/backend/chainwise/`: pacote Python principal. Fica diretamente em `backend/` (sem `src/` aninhado) para manter imports simples e compatíveis com `pyproject.toml`.
- `src/frontend/src/`: código-fonte do Next.js/React.
- `adapters/`: cada fonte de dados externa tem seu próprio adapter com interface clara.
- `services/`: lógica pura, independente de framework web.
- `agent/`: orquestração do pipeline e prompts.
- `infrastructure/`: detalhes técnicos como cache e persistência.
- `docs/`: centraliza toda a documentação do projeto.

---

## 7. Fluxo de Dados de uma Requisição

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

### Fase 1 — Fundação
- [ ] Configurar projeto Python (pyproject.toml, lint, pytest).
- [ ] Criar estrutura base de pastas e módulos.
- [ ] Implementar `config/settings.py` com Pydantic.
- [ ] Criar schemas de request/response.

### Fase 2 — Adapters
- [ ] Implementar `blockscout.py` (tx, receipt, logs, ABI).
- [ ] Implementar `rpc.py` (`eth_call`, `getCode`, etc.).
- [ ] Implementar `github.py` (busca de código em repos configurados).
- [ ] Implementar `openrouter.py` (chamada ao LLM).
- [ ] Adicionar cache local e retries.

### Fase 3 — Serviços Core
- [ ] Implementar `decoder.py` (decodificação de funções e eventos).
- [ ] Implementar `token_detector.py`.
- [ ] Implementar `enricher.py` (eth_call para contexto).
- [ ] Implementar `repo_grounding.py`.
- [ ] Implementar `explainer.py` (montagem de prompt e chamada LLM).

### Fase 4 — Pipeline/Agent
- [ ] Implementar `workflow.py` orquestrando todo o fluxo.
- [ ] Implementar `prompts.py` com templates claros.
- [ ] Adicionar graceful degradation em cada etapa.

### Fase 5 — API + Frontend
- [ ] Criar endpoints FastAPI (`POST /explain`, `GET /health`, etc.).
- [ ] Criar frontend minimalista.
- [ ] Integrar frontend com backend.

### Fase 6 — Documentação e Testes
- [ ] Escrever README completo.
- [ ] Criar `docs/examples.md` com 3+ exemplos.
- [ ] Adicionar testes unitários e de integração.
- [ ] Revisar config-driven portability com pelo menos 2 redes.
- [ ] Criar docker compose opcional.

---

## 9. Critérios de Sucesso

O projeto será considerado pronto para envio quando:

- [ ] Uma transação real pode ser explicada corretamente em linguagem natural.
- [ ] Transações revertidas recebem diagnóstico útil.
- [ ] A troca de rede é feita apenas editando configuração.
- [ ] Toda resposta inclui fontes/links utilizados.
- [ ] O sistema funciona mesmo com algumas fontes indisponíveis.
- [ ] O README permite que alguém rode o projeto localmente em poucos minutos.
- [ ] Existem pelo menos 3 exemplos documentados.
- [ ] O código está testado e bem estruturado.

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

## 11. Próximos Passos

1. Aprovar/revisar este planejamento.
2. Criar a estrutura de pastas no repositório.
3. Começar pela Fase 1: configuração e schemas.
4. Selecionar 2-3 redes de teste (ex: Ethereum mainnet + Sepolia) e transações exemplo para validação.
