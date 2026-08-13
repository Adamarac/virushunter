# Referência de comportamento do gerador

Rede de segurança da migração para Python 3.

## Por que isto existe

Não há ambiente onde o pipeline possa ser executado
([ADR-0009](../../docs/decisions/0009-no-execution-environment.md)): faltam Python 2, BLAST,
bowtie2 e os bancos de dados. Sem isso, validação comportamental seria impossível — e
migrar um pipeline científico sem ela é inaceitável.

Mas o `virus_hunter.py` **não executa o pipeline: ele o gera**. Escreve ~50 scripts shell
que descrevem, comando a comando, tudo que o pipeline faria. Gerar esses scripts não exige
nenhuma ferramenta de bioinformática — apenas Python.

Então capturamos essa saída com o código Python 2 original e a congelamos. Qualquer versão
migrada que produza os mesmos arquivos byte a byte preservou o comportamento.

## Como usar

```sh
sh tests/reference/verify.sh     # compara a saída atual com a referência
sh tests/reference/capture.sh    # regrava a referência (só com mudança intencional)
```

Requer Docker. Usa `python:2.7-slim`; nada é instalado no host.

## Como funciona

`capture.sh` roda o gerador **sem modificar o fonte**. Dois ajustes acontecem só no
container:

1. **`ssh` falso no PATH.** `serverInfo()` consulta CPU e RAM de cada nó via
   `ssh <nó> get_CPU.py <nó>`. O substituto responde valores fixos (48 CPUs, 64 GB). Isso
   também elimina da referência a não-determinação do [K7](../../docs/known-issues.md) — o
   teto de memória do SPAdes deixa de depender de qual nó pegou o job.
2. **`/mnt/work` como symlink para `/work`.** O gerador calcula `wd = "/mnt" + cwd` e
   escreve parte dos artefatos por esse caminho absoluto e parte relativa ao cwd. O symlink
   faz os dois resolverem para o mesmo lugar.

`fixture/` traz um `samples.txt` com quatro arquivos seguindo a convenção de nomes do
sequenciador (`A_S1_L001_R1_001.fastq.gz`), que `readSeeds2()` agrupa em duas amostras,
`S1` e `S2`. O conteúdo dos FASTQ é irrelevante — o gerador só olha os nomes.

`_stderr.txt` fica fora da comparação: carrega ruído do ambiente que varia entre execuções
enquanto todo artefato gerado permanece idêntico.

## Versão do Python

A referência foi congelada inicialmente com `python:2.7-slim` e **re-congelada** com
`python:3.12-slim` após a Fase 1 da migração — ver
[ADR-0010](../../docs/decisions/0010-dict-ordering-behaviour-change.md) para por quê e para
a prova de que o conjunto de trabalho não mudou. A captura Python 2 continua acessível:

```sh
git show 2705fa7:tests/reference/expected/clonetrim.sh
```

Para re-congelar com outro interpretador:

```sh
VH_PY_IMAGE=python:2.7-slim sh tests/reference/capture.sh
```

## Garantias verificadas

- **Determinística.** Duas capturas consecutivas produzem artefatos idênticos.
- **Detecta desvio.** Alterar `EVALUE` de `0.01` para `0.001` — um caractere — faz a
  verificação falhar e aponta os arquivos afetados. Confirmado antes de aceitar a
  referência; um teste que nunca falhou não valida nada.
- **A própria verificação já falhou de forma silenciosa uma vez.** Um erro de aspas em
  `capture.sh` fazia a captura produzir zero artefatos, e comparar dois diretórios vazios
  dava "idêntico". Por isso `verify.sh` e as comparações passaram a conferir também a
  contagem de artefatos, e não apenas o diff.

## Limites

- Cobre o **gerador**, não os ~45 scripts worker. Estes precisam de testes próprios.
- Cobre uma única configuração: a commitada (`doAssembly='no'`, `pair=False`, e demais
  valores de [`virus_hunter.py`](../../script/virus_hunter.py)). Caminhos como `denovo`,
  CLARK, NT e HMMER **não** são exercidos. Ampliar exige capturar referências adicionais
  com outras configurações — recomendado antes de mexer nas etapas correspondentes.
- Prova que os **comandos** são os mesmos, não que produzem o mesmo resultado científico.
  Para isso só executando o pipeline de verdade.

## Papel na migração para Snakemake

Com a decisão de adotar Snakemake, os scripts capturados deixam de ser saída esperada e
passam a ser **especificação**: as regras Snakemake precisam emitir comandos equivalentes.
A referência continua sendo a descrição mais precisa que existe do que este pipeline faz.
