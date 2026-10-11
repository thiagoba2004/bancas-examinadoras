# Recebimentos operacionais — PRJ-000023 — Bancas Examinadoras

**Pasta canônica:** `governanca/recebimentos/`.  
**Uso:** relatórios de diagnóstico e evidências dos Gates de transferência de titularidade `A6`, sem confundir teste documental com aceite integral.  
**Política transversal:** `thiagoba2004/gerador-de-agents/GERADOR_WORKFLOW.md`, seção de padronização de recebimentos A6/B8 (`REQ-20261010-007`).

## Relatórios versionados

- [Teste documental de 10/10/2026 — PRJ-000023 — Gate A6](2026-10-10-prj-000023-gate-a6.md) — **HANDOFF_PENDING / NÃO HOMOLOGADO** na data do teste. A consulta às fontes, por si só, não atesta configuração de memória ou aceite operacional.

**Caminho anterior preservado por compatibilidade:** `relatorios/2026-10-10-recuperacao-inicial.md`. O arquivo antigo agora é um ponteiro para a evidência integral aqui, com histórico Git preservado.

## Padrão obrigatório para futuros recebimentos

```text
governanca/recebimentos/AAAA-MM-DD-prj-NNNNNN-gate-a6.md
governanca/recebimentos/AAAA-MM-DD-prj-NNNNNN-gate-b8.md
```

Usar **somente** o Gate aplicável ao Projeto. Para várias avaliações no mesmo dia, acrescentar `-r02`, `-r03` etc. antes de `.md` e preservar cada diagnóstico anterior (não sobrescrever o resultado de teste anterior para simular avanço). O nome não indica sucesso: o status real deve constar do relatório e do estado comprovado por evidências.

Para cada avaliação: registrar o pedido de persistência; indicar Projeto, data, Gate, fontes lidas (commit/SHA quando disponíveis), testes executados, critérios cumpridos/não verificados, pendências, próxima ação, ausência de mudança de memória/site/gastos, e realizar **leitura de retorno no GitHub**. Linkar em `AGENTS.md` e/ou `PROJECT_STATE.json` apenas quando atualizações forem autorizadas e auditadas. Não converter esta pasta em origem de GitHub Pages `/docs`.

**Fontes da verdade:** `AGENTS.md`, `PROJECT_STATE.json`, `ROADMAP.md`, `REQUEST_LOG.jsonl`, `STRATEGY_LOG.jsonl` e planos pertinentes. Um relatório histórico pode descrever uma pendência já sanada futuramente; ele não é um estado dinâmico. Revalidar o estado antes de afirmar progresso.
