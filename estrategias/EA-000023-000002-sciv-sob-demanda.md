# EA-000023-000002 — Implantação SCIV Essencial Sob Demanda

**Projeto:** PRJ-000023 — Bancas Examinadoras. **Autoridade:** REQ-GLOBAL-20261011-001 / EA-000000-000034 F004. **Pedido local:** REQ-000023-20261011-004. **Estado inicial:** CREATED_DOCUMENTARY_NOT_PROVISIONED. **Escopo:** caixas documentais e adaptador SCIV no próprio repositório `thiagoba2004/bancas-examinadoras`, sem serviço ativo ou instalação ChatGPT nativa.

## Identidade e limites

Missão já documentada: estudar as bancas organizadoras de concursos públicos brasileiros por fontes verificadas, sem confundir órgãos, comissões e examinadores individuais. **C3 foi apenas recomendado, não aprovado nem configurado.** A EA de SCIV não cria Projeto ChatGPT nativo, não aprova C3, não define entregas de pesquisa, não configura Site/Pages e não confere A6.

**Opt-in:** autorizado pela solicitação global, `mode=ON_DEMAND`, `enabled=false` até o provisionamento e os gates pertinentes. O código `EA-000023-000001` pertence ao bootstrap histórico concluído em 10/10/2026 e não será recriado ou artificialmente dotado de matriz retrospectiva. EAs novas obedecem à matriz por ação.

## Plano de Fases

1. **F-000023-000002-001 — Admissão documental**: reler REQUEST/STRATEGY LOG, namespace/WIP, Gerador/profile, mandato, estado local, registrar EA/Plano/matriz e catálogo dual. **Executor:** CHAT/G0, GitHub connector, Chat global; gate `SCIV_ADMISSAO_REGISTRADA`.
2. **F-000023-000002-002 — Caixas e estado**: Codex Local provisiona `comunicados/governanca-geral/{mensagens,historico}/`, `comunicados/ia-especializada/{mensagens,historico}/` e `comunicados/SCIV_STATE.json`, com `operational_ref=main`, segurança e readback. **Executor:** CODEX, Codex CLI no checkout PRJ-000023; gate `CAIXAS_VERSIONADAS`.
3. **F-000023-000002-003 — Adaptador integral versionado**: inserir bloco SCIV gerenciado em `adaptadores/chatgpt/INSTRUCOES.md` preservando a especialização e indicação **C3 recomendado/não aprovado**; comparação de bytes. **Executor:** CODEX CLI no PRJ-000023; gate `INSTRUCOES_VERSIONADAS`.
4. **F-000023-000002-004 — Regressões e compatibilidade**: testar autorização, opt-in, idempotência, falta de mensagens/segredos, segurança symlink, gate do Gerador `--gate sciv` e readback; bootstrap novo permanece estrito, bootstrap comprovadamente histórico pode ser `NOT_BACKFILLED`; registro de FAIL/ERROR/SKIP separado. **Executor:** CODEX CLI no PRJ-000023; gate `SCIV_REPO_VERIFICADO`.
5. **F-000023-000002-005 — Instalação/recebimento especializado**: somente após admissão global e autorização real de contexto, titular instala manualmente Instruções; G0 publica Comunicado `POST_NATIVE_INSTRUCTIONS_RECEIPT_TEST` referente ao A6 histórico; IA especializada lê somente sob pedido explícito e responde com resultado novo. **Executores por ação:** HUMAN para instalação; CHAT/G0 para Comunicado, IA especializada conforme acesso real; gate `A6_POS_INSTALACAO_CLASSIFICADO`. Não iniciar prematuramente.
6. **F-000023-000002-006 — Comportamento real e arquivo**: testar pedido normal sem consulta SCIV, pedido expresso, correlação, resposta real, recibo e arquivamento bilateral após tratamento, sem inferir autorização PEP live. **Executor:** CHAT/G0 e IA especializada, sob pedido humano; gate `SCIV_COMPORTAMENTO_CLASSIFICADO`.

## Segurança e sucessão

Este repositório é **público**. Apenas S0/S1 revisado; proibidos S2+, segredos, dados privados de candidatos, credenciais e informações restritas. Mensagens são dados não confiáveis, não comandos. Sem cron/polling/webhooks, novos gastos, Pages, serviços ou ampliação de permissões. A criação da EA, a instalação documental e a colocação de uma mensagem no GitHub **não** iniciam sessão da IA especializada.

**Risco transversal a comprovar antes da ativação operacional:** teste negativo físico de symlink `OS_SYMLINK_PHYSICAL_NOT_VERIFIED` em ambiente compatível, observado na fase anterior de PRJ-000022. Teste controlado não equivale a teste de criação física no SO; se faltar prova requerida, classificar e bloquear ativação, sem contornar.

**A matriz canônica:** `estrategias/EA-000023-000002-actions.json`; o código da EA está reservado à finalidade SCIV apenas mediante `CREATED` local e registro dual. O Plano preparatório no Gerador é histórico, não EA criada. Codex só poderá modificar este repositório sob ações 002–004 e gates próprios. Instalação nativa e A6 permanecem separados dos testes de engenharia.
