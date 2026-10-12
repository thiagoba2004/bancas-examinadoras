# Evidências CODEX — PRJ-000023 / EA-000023-000002

153 testes selecionados: 151 PASS, 2 SKIP_ENV_NOT_SUPPORTED, zero FAIL/ERROR.
Gate SCIV documental PASS; bootstrap estrito retorna FAIL esperado. Não houve ensaio A6,
instalação nativa, Site, alteração de contexto, PEP live ou ativação operacional.

Os arquivos Python são snapshots de código de auditoria, não serviços instalados.
Para reprodução, usar checkout isolado do commit-base 189763dc611b2eb5817773330c7e9d66a2576a3a,
dependências nos SHAs registrados em dependencias.json e venv com pins em logs/dependencies.log.
Restaurar sciv_delivery.py sob .codex/ e run_validation_guarded.py sob .sciv-stage-20261012/;
os caminhos relativos originais fazem parte do envelope. Os artefatos locais originais
e resultados protegidos permanecem no estágio deste executor. Não executar snapshots
como operação produtiva nem presumir que os hashes anteriores aceitem outro HEAD.

Logs publicados têm prefixos de máquina sanitizados; hashes original/derivado estão
em log-sanitization.json. Os hashes SHA-256 documentais preservam bytes locais,
incluindo finais de linha. O commit deve usar core.autocrlf=false na inclusão explícita
destes arquivos para preservar os bytes revisados; nenhuma configuração global muda.
O baseline local recuperado usa CRLF e equivale ao baseline Git após normalização de
finais de linha. Fora do bloco inserido, os bytes locais são exatamente preservados.

Esta verificação é do CODEX. Readback por outro transporte não é assurance independente.
Dois SKIPs de symlink físico Windows WinError 1314 mantêm a ativação bloqueada.
