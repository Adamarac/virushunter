# 0001 — Registrar decisões de arquitetura

- **Status:** Aceita
- **Data:** 2026-08-12
- **Decidido por:** Alan M

## Contexto

O repositório de origem (`xutaodeng/virushunter`) contém dois commits, ambos de
2020-07-12: `543307f initial upload` e `7370d54 Create README.md`. Todo o
desenvolvimento anterior a essa data foi perdido — não há histórico, mensagens de
commit, issues ou documentação de projeto.

A consequência prática é que **nenhuma decisão de design do pipeline pode ser
reconstruída a partir do repositório**. Por que os filtros mascaram leituras em vez de
removê-las? Por que a taxonomia trafega dentro do cabeçalho FASTA? Por que existem cinco
orquestradores? Todas essas perguntas hoje só podem ser respondidas por leitura reversa
do código, e algumas não podem ser respondidas de forma alguma.

Como a refatoração vai tomar muitas decisões novas, é necessário não repetir esse padrão.

## Alternativas consideradas

**Comentários no código.** Ficam próximos ao código, mas registram *o quê*, não *por
quê*, e desaparecem quando o código é reescrito — exatamente o momento em que a
justificativa é mais necessária.

**Wiki do GitHub ou documento externo.** Não é versionado junto com o código, diverge
com o tempo e não aparece em revisão de pull request.

**Mensagens de commit.** São o registro natural, mas não são navegáveis nem agregáveis:
recuperar a razão de uma decisão exige arqueologia no log, e decisões que se acumulam ao
longo de vários commits ficam dispersas.

**ADR versionadas no repositório.** Ficam sob controle de versão junto ao código,
aparecem em revisão, são navegáveis por índice e sobrevivem à reescrita do código que
motivou a decisão.

## Decisão

Adotar ADRs em `docs/decisions/`, no formato descrito em
[`docs/decisions/README.md`](README.md).

Toda decisão que altere o **comportamento científico** do pipeline exige ADR. Decisões
puramente organizacionais (formatação, nomes de arquivo) não exigem.

## Consequências

- Existe custo: cada decisão relevante passa a exigir um documento curto.
- Decisões pendentes passam a ser explícitas, com a evidência já levantada anexada
  (ver [ADR-0003](0003-canonical-orchestrator.md)), em vez de permanecerem implícitas.
- O registro só tem valor se for mantido. Uma ADR desatualizada é pior que nenhuma.
