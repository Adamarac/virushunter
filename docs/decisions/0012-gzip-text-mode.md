# 0012 — Modo texto no gzip

- **Status:** Aceita
- **Data:** 2026-08-12
- **Decidido por:** Alan M

## Contexto

Pendência aberta pela [ADR-0011](0011-explicit-division.md).

Em Python 2, `gzip.open` devolvia byte strings, e byte string **era** `str`. Todo o
trabalho de string que vem depois — `line.strip()`, comparação com `'>'` ou `'@'`,
concatenação em arquivos de saída de texto — simplesmente funcionava.

Em Python 3 isso deixa de valer, e a armadilha é que os modos óbvios não ajudam:

```
gzip.open(f)          -> bytes
gzip.open(f, 'r')     -> bytes
gzip.open(f, 'rb')    -> bytes
gzip.open(f, 'rt')    -> str
```

Isso não é caso de borda: dados de sequenciamento chegam comprimidos, e o
`virus_hunter.py` passa `.fastq.gz` direto para esses workers. É o caminho normal.

Onze ocorrências no fecho vivo, em sete arquivos — dez leituras e uma escrita.

## Alternativas consideradas

**`'rt'` com codificação padrão.** Idiomático e correto para os formatos envolvidos, que
são ASCII (FASTQ, FASTA, SAM).

**`'rt'` com `encoding='latin-1'`.** Mapeia byte a caractere 1:1, nunca levanta erro, e é
o equivalente mais próximo do Python 2 — que repassava bytes sem interpretar. Descartada:
acrescenta ruído em onze pontos para proteger contra entrada malformada que este pipeline
não deveria aceitar em silêncio.

**Manter binário e decodificar em cada uso.** Espalharia `.decode()` por dezenas de linhas
e converteria uma correção local em refatoração ampla.

## Decisão

Todo `gzip.open` no fecho vivo usa modo texto: `'rt'` para leitura, `'at'` para a escrita
em [`sra.py:8`](../../script/sra.py#L8). Verificado por
[`tests/check_gzip_text_mode.py`](../../tests/check_gzip_text_mode.py), que rejeita modo
omitido, `'r'` e também `'rb'` — este último é explícito, mas explicitamente errado, e
passaria por intencional numa revisão.

| Arquivo | Linhas |
|---|---|
| `dedup.py` | 113, 138 |
| `fq2fa.py` | 6 |
| `fq2faID.py` | 7 |
| `polyA.py` | 14 |
| `sam2count.py` | 34 |
| `sampleFastq.py` | 6, 7, 21 |
| `sra.py` | 5, 8 |

### Corrige também K20

[`dedup.py:113`](../../script/dedup.py#L113) chamava `gzip.sopen`, um método que **não
existe**. Qualquer entrada `.gz` levantava `AttributeError`, capturado pelo `except` nu do
`__main__`, que imprimia *"usage: dedup.py ..."* e saía como se estivesse tudo bem — a
deduplicação silenciosamente não acontecia. O verificador rejeita qualquer `gzip.<nome>`
que não seja `open`.

## Consequências

- Workers voltam a ler `.gz`, que é como os dados chegam.
- Surge [`tests/test_gzip_input.sh`](../../tests/test_gzip_input.sh): comprime um FASTQ,
  passa pelos workers e exige que `.gz` e texto puro produzam saída idêntica. Verificado
  nos dois sentidos — revertendo `fq2fa.py` para `'rb'`, falha com
  `TypeError: can only concatenate str (not "bytes") to str`.
- **Mudança de comportamento com entrada malformada.** Python 2 repassava bytes sem
  interpretar; `'rt'` decodifica, então um `.gz` que não seja UTF-8 válido passa a levantar
  `UnicodeDecodeError` em vez de atravessar silenciosamente. Para FASTQ/FASTA/SAM legítimos
  não há diferença. Considero preferível: dado corrompido virar erro é exatamente o oposto
  do padrão que torna este projeto difícil de confiar. Se surgir dado histórico que dependa
  do comportamento antigo, `encoding='latin-1'` restaura o repasse byte a byte.
- **Fora do fecho vivo nada foi corrigido.** Outros arquivos ainda usam `gzip` em modo
  binário e continuam em Python 2.
