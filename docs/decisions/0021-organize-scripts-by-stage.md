# 0021 — Organizar `script/` por etapa do pipeline

- **Status:** Aceita
- **Data:** 2026-08-15
- **Decidido por:** Alan M

## Contexto

Depois da poda ([ADR-0020](0020-prune-to-the-migrated-version.md)), `script/` tinha 33
arquivos numa pasta plana. Ler os 24 scripts — não só os nomes — revelou três problemas
distintos.

**Os nomes descrevem o meio, não o fim.** `blast_output_sort.py`, o maior arquivo do
projeto com 352 linhas, não ordena saída do BLAST: gera o relatório HTML da amostra,
extrai FASTA por vírus e conta por barcode. `sam2fq_bac.py` sugere bactéria, mas esvazia
tudo que alinhou no hospedeiro, humano incluído. `polyA.py` mede qualquer homopolímero.
O par pior é `partition.py` / `splitQuery.py`: os dois quebram arquivo, com estratégias
diferentes (lotes de *k* leituras contra *n* arquivos alternando sequências), e nada nos
nomes diz qual é qual.

**Duplicação medida.** Os dois filtros NR compartilhavam 78 linhas. `CacheLines` e
`getSeq` eram byte a byte idênticas; `readVirusXML1` 91% igual; `OutputVirus` 86%. Isso é
55% do arquivo menor. A consequência prática apareceu duas vezes nesta refatoração: K1 e
K27 tiveram de ser corrigidos separadamente nas duas cópias.

**A camada web não era do pipeline.** Seis `.php` mais `catAlignFA.py`, `tablestyle.css` e
`wait.gif` estavam ali por proximidade, e só entravam no fecho porque a regra `publish`
copia `*.php` por glob.

## Decisão

Quatro subpastas espelhando as etapas que o `Snakefile` já nomeia:

```
script/reads/      preparo das leituras       (8 arquivos)
script/search/     busca viral e filtro NR    (3)
script/assembly/   montagem                   (3)
script/report/     relatório e métricas       (8)
web/               aplicação PHP, fora de script/
```

Renomeados 20 arquivos pela finalidade real. Fundidos os dois filtros NR em
`search/filter_nr.py`, que recebe o método como sétimo argumento.

**Sem camadas por tipo.** Nada de `io/`, `utils/`, `common/` — seria a mesma inversão
corrigida na [ADR-0017](0017-simplify-the-package.md). A ordem do pipeline é a única
estrutura que este projeto realmente tem; qualquer outro critério seria inventado.

**Sem mover para `src/virushunter/`.** Estes são executáveis de linha de comando invocados
pelo Snakemake, não biblioteca. Só `reads.py` e `config.py` são importados, e já estavam no
lugar certo.

## A fusão dos filtros

As duas rotas divergiam em quatro pontos, todos preservados:

| | `blast` | `diamond` |
|---|---|---|
| Critério | `expect >= nrE[query]` | `query in nrE` |
| `LNVNRE` na saída | valor real, ou `no-hit` | `-` |
| Erro de XML | propaga | engolido, imprime `XML format bad` |
| Falha ao ler o NR | `nrE = {}` | `nrE = set()`, imprime `no diamond` |

O `except` nu da rota `diamond` é um defeito pelo padrão deste projeto — falha silenciosa
disfarçada de sucesso. **Foi mantido**, porque removê-lo mudaria comportamento e essa é
decisão separada. Está isolado num `if metodo != 'diamond': raise`, que torna a divergência
visível em vez de escondida em dois arquivos.

### Verificação da fusão

Não por leitura. Gerei XML de BLAST **real** com o `blastx` 2.17 instalado em `tools/bin/`,
sobre bancos sintéticos, e comparei a saída do arquivo fundido contra cada original:

| Caso | Resultado |
|---|---|
| `diamond`, candidato passa | **idêntico**, 11 linhas |
| `diamond`, candidato na lista negra | **idêntico**, 0 linhas |
| `blast`, comparação de e-values | **idêntico**, 11 linhas |

O teste tem poder: os três casos produzem saídas diferentes entre si, então a igualdade não
é trivial.

## Defeitos corrigidos no caminho

- **`build_report.py` chamava os irmãos sem interpretador.**
  `os.system(dirscr + 'faSort.py ...')` depende do shebang, que **não funciona no
  Windows**, e o retorno era ignorado — a etapa falharia em silêncio. Agora usa
  `sys.executable`.
- **`cat.php` apontava para `E:\wamp64\www\catAlignFA.py`**, caminho absoluto de um
  servidor WAMP em outra máquina. Trocado por `__DIR__`.
- **`catAlignFA.py` usava `print >>arquivo, texto`.** Isso **parseia** em Python 3 — é lido
  como `print >> arquivo` seguido de uma tupla — e só quebra na execução. Foi o único resto
  de Python 2 que passou pelas verificações de compilação, e obriga a corrigir uma
  afirmação anterior minha: "24/24 compilam" não provava "100% portado". Varri os demais
  padrões (`has_key`, `xrange`, `iteritems`, `unicode`) e não havia outros.
- **`blastdb_alias.py` invocava `blastdb_aliastool` como nome nu**, fora da configuração.
  O binário existe em `tools/bin/` mas não no `PATH`, então a regra falhava. Agora recebe o
  caminho por argumento, como `makeblastdb` já recebia.

## O que deliberadamente não mudei

**Os nomes das funções internas** (`polyA`, `firstpage`, `mergeTable`). O ganho seria
cosmético e há risco real: `num_polyA_reads` é uma chave de métrica que acopla
`homopolymer_hist.py` a `index_page.py`, então esses nomes vazam para os dados.

## Consequências

- Quem lê uma regra do `Snakefile` sabe em que pasta procurar o script.
- Uma correção nos filtros NR passa a valer para as duas rotas de uma vez.
- 48 links da documentação foram **reapontados** para os caminhos novos, não degradados
  para texto: os arquivos continuam existindo, só mudaram de lugar.
- `web/README.md` registra que aquela aplicação **não funciona como está** — todas as
  dependências de front-end estão ausentes do repositório — e que `blast_run.php` e
  `price_run.php` montam comandos a partir de entrada de formulário, o que merece revisão
  de segurança antes de ir ao ar.
- Nada foi executado de ponta a ponta; continua valendo a
  [ADR-0009](0009-no-execution-environment.md).
