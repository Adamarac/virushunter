# 0011 — Divisão explícita

- **Status:** Aceita
- **Data:** 2026-08-12
- **Decidido por:** Alan M

## Contexto

Em Python 2, `7/4` é `1`. Em Python 3, é `1.75`. O operador não mudou de grafia, então
uma migração que corrige apenas sintaxe deixa **cada uma dessas divisões devolvendo um
valor diferente, em silêncio**. O `2to3` não as toca, por não haver como decidir a
intenção automaticamente.

Neste projeto isso atinge o invariante central. A identidade de uma leitura é a sua
posição no arquivo ([I1](../invariants.md)), e três scripts a constroem a partir de `i/4`
sobre o contador de linhas — cada um declarando no próprio fonte que precisa concordar com
os outros:

| Script | Formato | Comentário no fonte |
|---|---|---|
| [`recodeID.py:14`](../../script/recodeID.py#L14) | `@s<n>_<par>_<lib>` | *"this is to be consistent with fq2faID.py"* |
| [`fq2faID.py:14`](../../script/fq2faID.py#L14) | `><fileID>_<n>` | *"this has to be consistent with blast_trim.py"* |
| [`blast_trim.py:86`](../../script/blast_trim.py#L86) | `@s<n>_<par>_<lib>` | *"this is to be consistent with fq2faID.py"* |

Sem correção, o `recodeID.py` emite **`@s0.25_1_lib`** — não `@s0.0`, porque `1/4` é
`0.25`. O pipeline roda até o fim e apenas deixa de casar leituras com seus pares.

Nove ocorrências foram encontradas no fecho vivo, em cinco arquivos.

## Alternativas consideradas

**`from __future__ import division` e revisar caso a caso.** Torna o comportamento
uniforme, mas exige a mesma análise local — sem ganho.

**Corrigir apenas as três geradoras de identidade.** Menor diff. Descartada: as demais
(contagens de adaptador, de leituras, índice comparado a conjunto de inteiros) sofrem do
mesmo problema, e deixar metade corrigida convida a regressão.

**Exigir divisão explícita em todo o fecho vivo**, verificado automaticamente. Custa um
caractere por ocorrência e elimina a classe inteira de defeito.

## Decisão

Toda divisão envolvendo literal inteiro, no fecho vivo, deve declarar a intenção: `//`
para divisão inteira, `float()` num operando para divisão real. `/` puro é rejeitado por
[`tests/check_integer_division.py`](../../tests/check_integer_division.py).

As nove ocorrências viraram `//`. Todas operam sobre contadores não-negativos — contadores
de linha e contagens — onde `//` reproduz exatamente a semântica do Python 2. Para valores
negativos `//` e a divisão do Python 2 divergiriam de `int()`, mas esse caso não ocorre
aqui.

| Arquivo | Linha | Papel |
|---|---|---|
| `recodeID.py` | 16 | ordinal da leitura (I1) |
| `fq2faID.py` | 20 | ordinal do FASTA (I1) |
| `blast_trim.py` | 91 | ordinal da leitura (I1) |
| `blast_trim.py` | 122, 123 | contagem de adaptadores 3' e 5' |
| `clark_result.py` | 103 | contagem; já vinha embrulhada em `int()` |
| `sampleFastq.py` | 15, 39 | contagem de leituras e índice |

## Consequências

- O comportamento do Python 2 fica preservado nos nove pontos. Não é mudança científica:
  é a correção que **evita** uma.
- Surge o primeiro teste comportamental de um worker:
  [`tests/test_read_identity.sh`](../../tests/test_read_identity.sh) roda os três
  geradores sobre um FASTQ mínimo e exige ordinais inteiros e concordantes. Verificado nos
  dois sentidos — revertendo uma divisão, ele falha e mostra `@s0.25_1_lib`.
- A regra é mais estrita do que o estritamente necessário: `clark_result.py:103` já estava
  correta, pois o `int()` externo truncava. Foi normalizada mesmo assim, porque uma regra
  com exceções não é verificável automaticamente.
- **Fora do fecho vivo nada foi corrigido.** `mira_shortenID.py` também gera identidade com
  `str(i/4)` e continua em Python 2. Se voltar a ser usado, precisa da mesma correção.

## Pendente nesta frente

O problema de texto vs. bytes no `gzip` foi resolvido em seguida — ver
[ADR-0012](0012-gzip-text-mode.md).
