# 0009 — Não há ambiente de execução

- **Status:** Contexto registrado; a mudança de estratégia que ele exige está **Pendente**
- **Data:** 2026-08-12
- **Decidido por:** — (constatação confirmada por Alan M; a decisão decorrente segue aberta)

## Contexto

Foi confirmado que **não existe nenhum ambiente onde este pipeline possa ser executado** —
nem o cluster original, nem uma montagem local ou em container com Python 2, BLAST+,
bowtie2, SPAdes e os bancos de dados.

Isso invalida parte da estratégia de validação proposta em
[`docs/known-issues.md`](../known-issues.md):

| Nível | Descrição | Situação |
|---|---|---|
| 0 | Verificação estrutural (contagens, formato) | Parcialmente viável estaticamente |
| 1 | Testes unitários dos parsers | **Bloqueado** — exige Python 2 |
| 2 | Dado sintético ponta a ponta | **Bloqueado** — exige as ferramentas e os bancos |
| 3 | Regressão sobre dado real | **Bloqueado** — e não se sabe se há execução preservada |

Os dois testes existentes
([`check_no_import_side_effects.py`](../../tests/check_no_import_side_effects.py) e
[`check_argv_numeric_comparison.py`](../../tests/check_argv_numeric_comparison.py)) rodam
em Python 3 justamente porque são **léxicos**: nunca importam nem executam o alvo. Foi o
que permitiu corrigir [K1](../known-issues.md) e [K10](../known-issues.md) com evidência
real.

### A circularidade

Os críticos restantes — [K2](../known-issues.md) (dessincronização em `samNT.py`),
[K3](../known-issues.md) (troca silenciosa de modo), [K5](../known-issues.md) (detecção de
falha), [K7](../known-issues.md) (não-determinismo do SPAdes) — **alteram a saída do
pipeline**. Corrigi-los sem poder executar nada significa alterar comportamento científico
às cegas.

Mas construir validação comportamental exige executar o código, e o código não roda em
nenhuma máquina atual porque é Python 2, sem suporte desde 01/01/2020 — antes mesmo do
commit inicial deste repositório.

### A saída

A migração para Python 3 ([K12](../known-issues.md)) é o que rompe o ciclo, porque é a
única mudança grande cuja correção **é verificável sem executar o pipeline**:

1. `python3 -m py_compile` valida a sintaxe de cada arquivo — hoje impossível, já que
   nenhum arquivo compila em Python 3.
2. As armadilhas semânticas do 2→3 são **enumeráveis e detectáveis estaticamente**:
   divisão inteira (`lineno = i/4` em [`recodeID.py`](../../script/recodeID.py#L16), que
   sustenta o invariante [I1](../invariants.md)), `dict.has_key()`, `xrange`, comparações
   entre tipos distintos (a causa de K1), `sort(cmp=)`, `print`, texto vs. bytes.
   Cada categoria admite um verificador do mesmo tipo dos dois já existentes.
3. Depois da migração o código volta a ser **executável em qualquer máquina**, o que
   desbloqueia os Níveis 1 a 3 e, com eles, os críticos restantes.

Ou seja: a migração deixa de ser um item de modernização e passa a ser **pré-requisito de
todo o resto**.

## Alternativas consideradas

**Corrigir os críticos restantes sem validação.** Rápido, e irresponsável em pipeline
científico: são exatamente as mudanças que alteram resultado.

**Reconstruir um ambiente Python 2.** Possível via container, mas exige também BLAST+,
bowtie2, SPAdes, HMMER e bancos de vários terabytes. Investe em uma plataforma morta.

**Migrar para Python 3 primeiro, guiado por verificadores estáticos por categoria de
armadilha.** Converte um problema não verificável em vários verificáveis, e o resultado é
um código que roda.

## Decisão

**Pendente.** O registro do impedimento e do raciocínio é feito aqui; a decisão de adotar a
migração para Python 3 como próxima frente estrutural é sua.

Enquanto pendente, valem duas regras:

1. **Nenhuma correção que altere a saída do pipeline** sem validação comportamental —
   isso inclui K2, K3, K5 e K7.
2. Priorizar trabalho verificável estaticamente ou puramente organizacional.

## Consequências

- O trabalho já feito seguiu essa regra: K1 e K10 foram escolhidos por serem
  estaticamente verificáveis, e [ADR-0008](0008-repository-scope.md) não toca em
  comportamento.
- [K6](../known-issues.md) (versionamento de bancos) fica fora de alcance por outro motivo:
  não há bancos aos quais aplicar. O que se pode fazer é especificar o formato do manifesto
  para quando houver.
- Se um ambiente aparecer depois, esta ADR deve ser revista — a ordem de prioridades muda
  substancialmente.
- **Não determinado:** se existe alguma execução real preservada (entrada + saída) acessível
  ao grupo. Se existir, o Nível 3 volta a ser possível após a migração, e é a validação mais
  valiosa disponível. Vale confirmar.
