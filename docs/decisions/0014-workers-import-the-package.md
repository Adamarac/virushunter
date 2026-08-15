# 0014 — Workers passam a importar o pacote

- **Status:** Aceita
- **Data:** 2026-08-12
- **Decidido por:** Alan M

## Contexto

A [ADR-0013](0013-package-foundation.md) extraiu `ReadId` e `FastaIndex` e provou
equivalência com o código legado, mas deixou os workers intactos — religá-los dependia de
uma questão em aberto: os workers são executáveis autocontidos, invocados por caminho
absoluto, e importar `virushunter` exigiria o pacote disponível em cada nó de execução.

**A execução passou a ser local, não em cluster.** Isso dissolve a objeção: `pip install -e .`
resolve, e não há distribuição de ambiente para gerenciar.

## Decisão

Religar os três geradores de identidade — `recodeID.py`, `fq2faID.py` e `blast_trim.py` —
para usarem `virushunter.domain`. A aritmética do ordinal e o formato do identificador
passam a existir em um lugar só.

Os harnesses em container montam `src/` como `/pkg` e expõem via `PYTHONPATH`, em vez de
instalar o pacote: assim os testes rodam contra a árvore de trabalho, não contra o que
estiver instalado.

## Consequências

- O invariante I1 deixa de depender de três implementações concordarem por acordo.
- Rodar um worker exige o pacote disponível. Localmente, `pip install -e .`.
- **As seis cópias de `CacheLines` seguem sem religar.** `FastaIndex` está pronto e provado,
  mas aqueles arquivos têm mais lógica em volta e nenhuma cobertura comportamental própria;
  religá-los merece incremento separado.

### Duas regressões que eu introduzi, e como apareceram

Ao reescrever o bloco de imports do `blast_trim.py`, removi `from collections import
defaultdict`, ainda usado adiante. E ao substituir o cálculo do ordinal, removi a variável
`lineno`, que a linha 101 usa para indexar a tabela de hits de adaptador.

A primeira foi pega por `tests/test_read_identity.sh`,
que falhou com `NameError`. A segunda **não** foi — só apareceu numa varredura de nomes não
definidos por AST, porque o teste morria antes de chegar lá.

Isso expõe um limite real da cobertura atual: os testes comportamentais exercitam o caminho
feliz de cada worker, não seus ramos. `lineno` só é lido no ramo da linha de sequência
quando existem hits de adaptador — e a fixture usa uma tabela vazia.
