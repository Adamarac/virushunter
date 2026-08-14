# Registro de decisões de arquitetura (ADR)

Cada arquivo desta pasta registra **uma** decisão: o contexto em que foi tomada, as
alternativas consideradas, a escolha e suas consequências.

O objetivo não é burocracia. É que, daqui a dois anos, seja possível responder
"por que isto está assim?" sem depender da memória de quem estava presente — o problema
central deste projeto, cujo código chegou até aqui sem nenhum registro de intenção.

## Formato

Arquivos são nomeados `NNNN-slug-curto.md`, numerados sequencialmente.

```markdown
# NNNN — Título

- **Status:** Proposta | Aceita | Pendente | Substituída por ADR-XXXX | Revogada
- **Data:** AAAA-MM-DD
- **Decidido por:** quem

## Contexto
O que motivou a decisão. Fatos, com evidência.

## Alternativas consideradas
Cada opção real, com prós e contras honestos.

## Decisão
O que foi escolhido.

## Consequências
O que passa a ser verdade, incluindo o que fica pior.
```

## Regras

- ADRs são **imutáveis** depois de aceitas. Mudou de ideia? Nova ADR que substitui a
  anterior, e a antiga passa a `Status: Substituída por ADR-XXXX`.
- Uma decisão ainda em aberto pode ser registrada com `Status: Pendente`. É preferível
  registrar a pendência com a evidência já levantada a deixá-la implícita.
- Decisão que altera o **comportamento científico** do pipeline exige ADR. Sem exceção.

## Índice

| ADR | Título | Status |
|---|---|---|
| [0001](0001-record-architecture-decisions.md) | Registrar decisões de arquitetura | Aceita |
| [0002](0002-working-base-and-fork.md) | Base de trabalho e fork | Aceita |
| [0003](0003-canonical-orchestrator.md) | Orquestrador canônico | Substituída por 0004 |
| [0004](0004-virus-hunter-as-reference.md) | `virus_hunter.py` é a referência científica | Aceita |
| [0005](0005-nr-filter-strategy.md) | Estratégia do filtro contra NR | **Pendente** |
| [0006](0006-no-import-side-effects.md) | Sem efeitos colaterais em tempo de importação | Aceita |
| [0007](0007-inert-evalue-threshold.md) | Limiar de e-value inerte nos filtros | Aceita |
| [0008](0008-repository-scope.md) | Escopo do repositório | Aceita |
| [0009](0009-no-execution-environment.md) | Não há ambiente de execução | **Pendente** |
| [0010](0010-dict-ordering-behaviour-change.md) | Mudança forçada: ordem de iteração de dicionário | Aceita |
| [0011](0011-explicit-division.md) | Divisão explícita | Aceita |
| [0012](0012-gzip-text-mode.md) | Modo texto no gzip | Aceita |
| [0013](0013-package-foundation.md) | Fundação do pacote e primeira extração | Aceita |
| [0014](0014-workers-import-the-package.md) | Workers passam a importar o pacote | Aceita |
