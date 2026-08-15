# 0017 — Simplificar o pacote: sem camadas, sem objetos de domínio

- **Status:** Aceita
- **Data:** 2026-08-15
- **Decidido por:** Alan M
- **Substitui parcialmente:** [ADR-0013](0013-package-foundation.md), [ADR-0014](0014-workers-import-the-package.md)

## Contexto

O pacote em `src/virushunter/` tinha crescido numa direção que o projeto não pediu:
subpacotes `domain/` e `io/`, cada um com um `__init__.py` só para reexportar, um objeto
de domínio imutável (`ReadId`) e um índice de arquivo com protocolo completo
(`FastaIndex`). No total, 457 linhas.

Medido contra o uso real:

| Peça | Linhas | Consumidores reais |
|---|---|---|
| `io/fasta.py` + `io/__init__.py` | 85 | **nenhum** |
| `domain/read_id.py` + `__init__.py` | 87 | 2 scripts, que usam `at_line()` e `str()` |
| `Config.as_dict()`, `__repr__` | — | só o próprio pacote |
| `load(path=...)`, `VIRUSHUNTER_CONFIG_OVERLAY` | — | **nenhum** |

`FastaIndex` foi escrito para substituir as seis cópias de `CacheLines`/`getSeq`, mas
esses seis workers continuam em Python 2 e nunca foram religados — a ADR-0014 já
registrava isso como pendência. Ou seja: uma abstração pronta, testada e sem uso.

`ReadId` era um dataclass congelado com validação, `parse()`, `mate()` e uma função
auxiliar `fasta_ordinal()`. Os dois pontos de chamada precisam de duas coisas: o número
da leitura e o texto `@s<n>_<par>_<biblioteca>`.

A validação em `__post_init__` existia para rejeitar ordinal fracionário — sintoma da
divisão real do Python 3. Ela só fazia sentido enquanto o objeto pudesse ser construído
em qualquer lugar. Com uma função que usa `//` internamente, não há o que validar: o
resultado é `int` por construção.

## Decisão

Achatar o pacote e cortar o que não tem consumidor.

```
src/virushunter/
    __init__.py     versão
    config.py       lê e valida config/default.yaml
    reads.py        LINES_PER_RECORD, read_ordinal(), read_id()
    workflow.py     descobre amostras, resolve a configuração
```

- `io/` removido inteiro. Recuperável do histórico se a migração dos seis workers
  acontecer; até lá, código morto.
- `domain/` achatado em `reads.py`: 87 linhas viram 15, duas funções, nenhuma classe.
- `Config` mantido — a consulta por caminho (`cfg["params.evalue"]`) aparece cerca de
  cem vezes no Snakefile e paga o próprio custo. Removidos `as_dict()` e `__repr__`.
- Sobreposição de configuração reduzida de quatro caminhos para dois: o arquivo padrão
  (com `VIRUSHUNTER_CONFIG` apontando outro) e o `--configfile` do Snakemake. O parâmetro
  `path=` e a variável `VIRUSHUNTER_CONFIG_OVERLAY` não eram usados por nada.
- `discover_samples()` agora deriva de `fastq_files()` em vez de varrer o diretório de
  novo com a mesma lógica.

Resultado: 457 → 264 linhas, 7 arquivos → 4, 2 subpacotes → 0.

## Alternativas consideradas

**Manter `FastaIndex` para a migração futura.** Custo: mantém 85 linhas sem uso e uma
pasta inteira só para elas. O histórico do Git guarda o mesmo código sem custo diário.

**Trocar `Config` por uma função `get(dados, "a.b.c")`.** Removeria a classe, mas
trocaria `cfg["x"]` por `get(cfg, "x")` em cem lugares — mais ruído, não menos.

**Manter `domain/` como pasta com um arquivo só.** O nome anuncia uma arquitetura que o
projeto não tem, e a indireção `virushunter.domain` → `virushunter.domain.read_id` não
entrega nada.

## Consequências

- Quem abre `src/` vê quatro arquivos e entende o escopo do pacote sem navegar.
- A verificação do invariante I1 deixa de ser feita em tempo de execução por
  `__post_init__` e passa a ser garantida pela própria aritmética (`//` só devolve
  inteiro). É menos código para o mesmo efeito, mas também é menos alarde: se alguém
  construir o identificador à mão em outro lugar, nada avisa.
- Se os seis workers forem migrados, `FastaIndex` precisa ser recuperado do histórico ou
  reescrito. A decisão aposta que isso é mais barato que carregar código morto.

## Verificação

As quatro rotas do fluxo continuam resolvendo o mesmo número de tarefas antes e depois:
padrão 349, paired 355, adaptor 357, denovo 369. `recodeID.py` produz saída idêntica
sobre a mesma entrada. `ruff check src` passa. Os 21 avisos do `ruff` em
`script/blast_trim.py` são anteriores a esta mudança — conferido com `git stash`.
