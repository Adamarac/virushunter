# 0013 — Fundação do pacote e primeira extração

- **Status:** Aceita
- **Data:** 2026-08-12
- **Decidido por:** Alan M

## Contexto

O projeto não tem pacote: `script/` é um diretório plano onde nenhum arquivo importa
outro, e o mesmo código está copiado várias vezes. Duas duplicações concentram o risco:

**`CacheLines` / `getSeq`** — indexação e leitura aleatória de FASTA — está **byte a byte
idêntica em seis arquivos** do fecho vivo: `blast_filter_NR.py`, `blast_output_sort.py`,
`blast_parser.py`, `clark_result.py`, `diamond_filter_NR.py` e `samNT.py`. Cópia número
seis é o que torna a extração necessária: uma correção aplicada a uma é uma correção
ausente em cinco.

**A identidade de leitura** ([I1](../invariants.md)) é construída por três scripts, cada um
declarando no fonte que precisa concordar com os outros. Foi exatamente onde a migração
quase introduziu `@s0.25_1_lib` ([ADR-0011](0011-explicit-division.md)). A regra existia
só em comentários.

## Alternativas consideradas

**Módulo compartilhado dentro de `script/`.** Menor mudança. Descartada: `script/` é
diretório de executáveis, não pacote, e não resolve empacotamento, dependências nem testes.

**Reescrever o índice FASTA para carregar sequências em memória.** Código mais simples.
Descartada: esses arquivos chegam a dezenas de gigabytes, e evitar carregá-los é
precisamente o motivo da abordagem por intervalos de linha.

**Pacote `src/virushunter/` com `pyproject.toml`.** Layout padrão, testável, com
dependências e ferramentas declaradas.

## Decisão

Criar `src/virushunter/` com `pyproject.toml`, alvo **Python 3.12** (`requires-python
>=3.11`), Biopython como única dependência de runtime, e pytest + ruff como dependências de
desenvolvimento.

Extrair dois componentes:

| Módulo | Substitui | Papel |
|---|---|---|
| `domain/read_id.py` | lógica espalhada em 3 scripts | `ReadId` imutável; ordinal validado como `int` |
| `io/fasta.py` | `CacheLines`/`getSeq` em 6 arquivos | `FastaIndex` com contrato definido |

`ReadId` torna o invariante I1 verificável em vez de acordado: o ordinal precisa ser `int`
— um `float` levanta erro citando o defeito do ADR-0011 —, o objeto é imutável, e o
`library` pode conter `_` porque o pipeline o constrói como `<projeto>_<amostra>`.

### Equivalência provada, não assumida

`FastaIndex` substitui código em produção há anos, então passar nos próprios testes não
basta. `tests/unit/test_fasta_index_equivalence.py`
reproduz a implementação legada **verbatim** como oráculo e compara cabeçalhos, intervalos
e sequências em 13 casos de borda — FASTA quebrado em várias linhas, último registro sem
`\n` final, linhas em branco, sequência vazia, CRLF, arquivo sem cabeçalho, arquivo vazio.

Isso encontrou uma divergência real: o legado testa `line.strip().startswith('>')`, então um
cabeçalho **indentado** conta como cabeçalho. A reescrita óbvia — `line.startswith('>')` —
teria divergido em silêncio. O comportamento legado foi mantido e fixado por teste próprio.

### Ruff

O conjunto de regras (`E`, `F`, `I`, `UP`, `B`) vale para `src/` e `tests/`. **`script/`
fica de fora por enquanto**: ligar regras amplas contra 46 arquivos ainda no estilo legado
produziria milhares de achados sem ensinar nada. O conjunto cresce conforme o código migra.

Ao aplicar o linter aos verificadores já existentes, todos os quatro foram **revalidados nos
dois modos** — sucesso e detecção de defeito — porque refatorar um teste sem reconfirmar que
ele ainda falha é como não ter teste.

## Consequências

- 89 testes unitários onde não havia nenhum. Rodam em segundos, sem Docker, sem BLAST.
- A duplicação **ainda existe**: os seis arquivos seguem com sua cópia de `CacheLines`, e os
  três geradores de identidade com sua aritmética. Este incremento cria o substituto e prova
  que é equivalente; **não religa nada**.
- **Religar os workers é decisão de implantação, não de estilo.** Hoje eles são executáveis
  autocontidos, invocados por caminho absoluto (`/mnt/cluster/xdeng/script/recodeID.py`).
  Importar `virushunter` exige o pacote instalado ou no `PYTHONPATH` de cada nó do cluster.
  Fica registrado como pendente.
- `pyproject.toml` fixa o alvo em Python 3.12 e declara Biopython, respondendo à parte de
  gerenciamento de dependências que não existia.
