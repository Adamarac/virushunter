# Problemas conhecidos

Levantamento iniciado sobre o código no estado de 2020. Cada item traz **problema →
evidência → impacto → recomendação**. Itens já corrigidos aparecem riscados, com a
resolução e a ADR correspondente; os demais são propostas ainda não aplicadas.

Severidade:

- **Crítica** — compromete execução, confiabilidade ou reprodutibilidade
- **Alta** — dificulta significativamente manutenção ou evolução
- **Média** — melhoria importante, não urgente
- **Baixa** — organização e qualidade

---

## Críticas

### ~~K1~~ — O limiar de e-value do filtro é inerte — **RESOLVIDO**

**Evidência** (linhas anteriores à correção): `diamond_filter_NR.py:132` e
`blast_filter_NR.py:169`, além de `diamond_filter.py:162`:

```python
E_VALUE_THRESH = sys.argv[5]          # permanece string
...
if float(hsp.expect) < E_VALUE_THRESH:   # float < str
```

Em Python 2, comparar tipos diferentes usa uma ordenação total artificial em que valores
numéricos são sempre menores que qualquer string. A condição é **sempre verdadeira**.

**Impacto.** O limiar declarado nesta etapa nunca é aplicado; todos os HSPs presentes no
XML passam (sujeitos apenas ao filtro NR, que funciona normalmente).

*Honestidade sobre a magnitude:* na configuração padrão o efeito prático é **atenuado**,
porque `virus_hunter.py` passa o mesmo `EVALUE` ao BLAST a montante, e o XML já contém
apenas hits com e-value ≤ 0,01. O problema real é outro: **endurecer o limiar do filtro
não tem efeito nenhum, silenciosamente.** Quem ajustar esse parâmetro esperando um
resultado mais restritivo obterá exatamente o mesmo resultado, sem qualquer aviso.

**Resolução.** Corrigido para `E_VALUE_THRESH = float(sys.argv[5])` nos três arquivos
afetados ([ADR-0007](decisions/0007-inert-evalue-threshold.md)). Coberto por
`tests/check_argv_numeric_comparison.py`, que
falhava antes e passa agora. A verificação dos pontos de chamada revelou [K24](#k24).

Segue pendente: as chamadas DIAMOND não passam `--evalue`, então nessa rota o limiar
efetivo ainda é o padrão da ferramenta. Decisão separada, registrada na ADR-0007.

### ~~K2~~ — `samNT.py` dessincroniza os arquivos SAM — **RESOLVIDO**

**Evidência.** `samNT.py:56-69` — o `break` no primeiro
acerto deixa os demais handles sem avançar. Viola
[I2](invariants.md#i2--arquivos-paralelos-são-lidos-em-correspondência-posicional).

**Impacto.** A partir da primeira leitura classificada, os 14 arquivos SAM ficam
desalinhados e leituras diferentes passam a ser comparadas entre si. **As contagens
taxonômicas da rota NT são não confiáveis.** A rota está desligada no estado commitado,
mas o código sugere que já foi usada.

**Resolução.** Corrigido em `report/nt_counts.py` (2026-08-15): todos os handles avançam
juntos antes de qualquer avaliação, e o primeiro acerto continua vencendo. Acrescentada a
verificação de contagem de linhas — SAMs de tamanhos diferentes agora abortam com mensagem.

Demonstrado com três SAM sintéticos, onde só o primeiro classifica a leitura 1 e só o
terceiro classifica a leitura 3:

| Versão | Saída |
|---|---|
| antes | `Bacteria 1, NA 3` — **o acerto viral foi perdido** |
| depois | `Bacteria 1, NA 1, Virus 1` |

Some-se que o código antigo contava um `NA` extra ao chegar no fim dos arquivos.

### ~~K3~~ — Troca silenciosa de modo de análise — **RESOLVIDO**

**Evidência.** [`sam2fq_bac.py:152-153`](../script/reads/host_mask.py#L152-L153):

```python
try: processBacSAM(...)             # paired-end
except: processSingleBacSAM(...)    # single-end
```

**Impacto.** Qualquer exceção — `IndexError`, `ZeroDivisionError`, arquivo faltando,
defeito no código — **troca o modo de análise**, possivelmente depois de já ter escrito
parte da saída. Não há registro algum da troca.

**Resolução.** Corrigido em `reads/host_mask.py` (2026-08-15): o modo vem de
`len(sys.argv)`, e qualquer erro dentro do modo par agora propaga.

A correção expôs um segundo defeito no mesmo arquivo: os tratadores faziam
`except: print(line)`, mas a variável se chama `line1`/`line2` — **o próprio tratador
estourava com `NameError`**. Um registro SAM curto, que deveria ser tolerado, virava
exceção; e com o código antigo essa exceção causava justamente a troca silenciosa de modo.
Os dois pontos foram corrigidos para a variável certa, conferindo qual `parts` cada um
trata.

Encontrado por varredura de nomes indefinidos com `ast` — o compilador não pega isso, a
mesma lição do [K28](#k28). A varredura hoje acusa zero ocorrências em `script/`.

### K4 — Credenciais em texto claro e `chmod 777`

**Evidência.** `virus_hunter.py:1950`
(`password='Welcome39'`, usada em `echo <senha> | sudo` em cinco pontos);
credenciais FTP em comentários nas linhas 146, 150, 159 e 160; e em
`script/readme.txt:44`.

**Impacto.** Segredos públicos desde 2020. `chmod 777 -R` recursivo torna dados e bancos
graváveis por qualquer usuário do cluster.

**Recomendação.** Tratar todas as credenciais como **comprometidas** e rotacioná-las —
removê-las do código não desfaz a exposição. Substituir `777` por grupo Unix com `775`/`664`.

### K5 — Falha é indistinguível de sucesso

**Evidência.** `schedule2.py:14-25` decide conclusão por
existência e tamanho do arquivo de saída, não por código de saída;
[`blast_parser.py:88`](../script/search/parse_hits.py#L88) engole XML truncado com
`except: print 'bad xml'`; 39 `except:` nus só em `virus_hunter.py`.

**Impacto.** Um BLAST morto por falta de memória depois de escrever XML parcial conta como
sucesso, e o pipeline segue com dados incompletos produzindo relatório de aparência normal.

**Recomendação.** Código de saída como critério primário; `set -euo pipefail` nos shells
gerados; substituir `except:` nus por exceções específicas; validar contagens de registro
entre etapas.

### K6 — Bancos de dados sem versionamento

**Evidência.** `script/readme.txt:6-9`:

```
mv .../blastdb/nr     .../blastdb/nr_today
mv .../blastdb/virus  .../blastdb/virus_today
```

O sufixo é literalmente `_today`, sobrescrito na atualização seguinte. Os scripts sempre
apontam para o caminho não-versionado.

**Impacto.** **Nenhuma análise anterior pode ser reproduzida** — o banco contra o qual foi
gerada não existe mais. Em descoberta viral isso é decisivo: o resultado é literalmente
"o melhor hit no banco naquele momento". Reexecutar após uma atualização trimestral produz
resultado diferente sem nenhuma mudança de código.

**Recomendação.** Diretórios imutáveis datados (`blastdb/virus/2026-01-15/`) com symlink
`current`; `MANIFEST.json` com data, origem, checksum, número de sequências e versão da
taxonomia; registrar o caminho **resolvido** em cada saída.

### ~~K7~~ — Não-determinismo dependente do nó de execução — **RESOLVIDO**

**Evidência.** `virus_hunter.py:1680`:

```python
spades.py -m ' + SI[servers[job%nservers]][1] + ' --meta ...
```

O teto de memória do SPAdes vem da RAM física do nó sorteado, medida em runtime por
`get_CPU.py`. O cluster é heterogêneo.

**Impacto.** A mesma entrada pode produzir **montagens diferentes** conforme o nó que
pegar o job — e a atribuição depende de ordem de dicionário e disponibilidade. É a fonte
de não-determinismo mais difícil de perceber do projeto.

Outras fontes: ordem de iteração de dicionário em Python 2 (afeta atribuição de nós,
índices de fatia e ordem de concatenação); reexecução dupla do `schedule2.py`; mutação de
banco in-place; não-determinismo dos assemblers multi-thread.

**Resolução.** A causa saiu com `virus_hunter.py`: nenhuma regra do workflow deriva
limite de memória do nó — a varredura por `SI[servers` no código vivo dá zero. As amostras
são descobertas em ordem alfabética por `discover_samples()`, e o Snakemake resolve o grafo
por dependência, não por ordem de dicionário.

**Segue valendo** a parte que não era do gerador: registrar versões em cada execução, e o
não-determinismo dos próprios montadores multi-thread.

---

## Altas

| # | Problema | Evidência | Impacto |
|---|---|---|---|
| ~~K8~~ | ~~Cinco forks do orquestrador~~ — **resolvido** ([ADR-0008](decisions/0008-repository-scope.md)) | [`orchestrators.md`](orchestrators.md) | Os quatro legados foram removidos; recuperáveis na tag `legacy-2020` |
| ~~K9~~ | ~~Configuração dentro do código~~ — **resolvido** ([ADR-0015](decisions/0015-declarative-configuration.md)) | `config/default.yaml` | Os 65 literais viraram configuração; `virus_hunter.py` saiu da árvore |
| ~~K24~~ | ~~Legados passam argumento errado ao filtro NR~~ — **resolvido** ([ADR-0008](decisions/0008-repository-scope.md)) | — | Os arquivos afetados foram removidos |
| ~~K10~~ | ~~`serverInfo()` em tempo de import~~ — **resolvido** ([ADR-0006](decisions/0006-no-import-side-effects.md)) | era `virus_hunter.py:205` | Chamada movida para `__main__`; guardado por `tests/check_no_import_side_effects.py` |
| K11 | Formato posicional de 11 linhas | [I4](invariants.md#i4--um-resultado-é-um-bloco-posicional-de-exatamente-11-linhas) | Corrupção silenciosa a qualquer mudança de formato |
| ~~K12~~ | ~~Python 2 sem suporte~~ — **resolvido** | verificado por `ast.parse` | Os 31 scripts restantes analisam em Python 3. Compilar não bastava, ver [K28](#k28) |
| ~~K13~~ | ~~Caminhos absolutos divergentes~~ — **resolvido** junto com [K27](#k27) | — | Zero `/mnt/cluster` no código; os filtros foram fundidos e leem da configuração |
| ~~K14~~ | ~~`argv[4]` usado duas vezes~~ — **resolvido** | `report/build_report.py` | `cwd` passou a ler `argv[5]`. Sem efeito prático: a referência sempre passou o mesmo valor duas vezes (`work work`), então a armadilha era latente |
| ~~K15~~ | ~~Duplicação de `CacheLines()` e `Node`~~ — **resolvido** | `src/virushunter/fasta.py` | `Node` saiu com a poda. `CacheLines`/`getSeq` viraram `index_headers`/`sequence`, importados pelos 4 scripts que os usavam |

**Progresso.** K10 foi resolvido — era o bloqueador de toda validação local, porque
alcançava também `readseeds2.py` através do `firstpage.py`. Com ele fora do caminho, o
Nível 1 da estratégia de validação (adiante) passa a ser executável.

K1 também foi resolvido, pelo mesmo padrão de verificação: um teste que falha no código
defeituoso e passa após a correção. A verificação dos pontos de chamada durante essa
correção revelou [K24](#k24).

### K24 — Orquestradores legados passam o argumento errado ao filtro NR

**Evidência.** Apenas o orquestrador de referência passa o e-value na posição correta:

| Orquestrador | `argv[5]` recebe |
|---|---|
| `virus_hunter.py:1825` — referência | `EVALUE` ✓ |
| `readseeds2.py:792` — legado | **`hsp`** (`'NO'`) |
| `readseeds_denovo.py:713` — legado | **`hsp`** |
| `readseeds_cloud.py:416` — legado | **`hsp`** |
| `readseeds.py:166` — legado | só 3 argumentos |

**Impacto.** Nos legados, `'NO'` era usado como limiar (comparação sempre verdadeira) e
`hsp_only` caía no `except`, virando `'NO'`. Ambos os parâmetros estavam errados, em
silêncio. Após a correção de K1, esses orquestradores falham alto com `ValueError` —
resultado desejado, mas é mudança de comportamento para eles.

**Recomendação.** Nenhuma correção: são legado por
[ADR-0004](decisions/0004-virus-hunter-as-reference.md) e serão removidos em incremento
próprio. Registrado para que a falha, quando ocorrer, seja reconhecível.

### K25 — A configuração commitada não roda até o fim

**Evidência.** Na referência capturada, `bowtiesam2fq.sh` produz apenas `S1_1.fil`, porque
`sam2fq_bac.py` recebe 4 argumentos (modo single-end). Mas `clonetrim.sh` deduplica
`S1_1.fil` **e** `S1_2.fil`, e `skipbowtie.sh` — único produtor de `_2.fil` — não entra
neste caminho, já que `keep_human=false` desvia para o `bowtieBac`.

A cadeia quebra em seguida: sem `_2.fil` não há `_2.dup`, sem `_2.dup` não há `_2.trim`, e
`fq_pair_clean.py` é chamado em modo par exigindo os dois.

**Causa.** `pair=false` faz `sam2fq()` emitir a forma de arquivo único, mas `trim()` e
`skip_adaptor()` iteram sobre **todos** os arquivos da amostra, ignorando o flag.

**Impacto.** Reforça o que [ADR-0004](decisions/0004-virus-hunter-as-reference.md) já
concluíra por outro caminho: o estado commitado é de teste, não de produção. Também explica
por que o efeito é invisível — o `except` nu do `dedup.py` imprime *"usage"* e sai com
sucesso quando o arquivo não existe.

**Só ocorre em single-end.** Com `pair=true` o `sam2fq_bac.py` recebe 5 argumentos, entra
em modo par e produz os dois arquivos — a cadeia fecha. Verificado capturando a referência
`expected-paired`: `bowtiesam2fq` passa a produzir `S1_1.fil` **e** `S1_2.fil`, exatamente
o que o `clonetrim` consome.

**Recomendação.** Nenhuma correção no gerador legado. O workflow Snakemake deriva o
conjunto de pares da configuração (`PAIRS`), então cada etapa roda exatamente sobre os
arquivos que existem — em single-end só `_1`, em paired-end os dois. A inconsistência não
tem como se reproduzir.

## Médias

| # | Problema | Evidência |
|---|---|---|
| ~~K16~~ | ~~68% dos `.py` são de outros domínios~~ — **resolvido** ([ADR-0020](decisions/0020-prune-to-the-migrated-version.md)) | restam 31 scripts, todos alcançáveis pelo `Snakefile` |
| ~~K17~~ | ~~Nenhuma dependência declarada~~ — **resolvido** | `pyproject.toml` declara as duas bibliotecas importadas; `environment.yml` fixa as 12 ferramentas externas |
| K18 | Nenhum teste ou dado de exemplo | Repositório inteiro |
| ~~K19~~ | ~~`readVirusGI()` lê o FASTA viral e o resultado é descartado~~ — **resolvido** junto com [K27](#k27) | a chamada morta foi removida da rota `diamond`; na rota `blast` o conjunto **é** usado |
| ~~K20~~ | ~~`gzip.sopen` — método inexistente~~ — **resolvido** ([ADR-0012](decisions/0012-gzip-text-mode.md)) | era `dedup.py:113`; a deduplicação silenciosamente não ocorria com entrada `.gz` |
| ~~K21~~ | ~~`clean_dir()` apaga todo arquivo não-`.gz`~~ — **resolvido** | a função saiu com `virus_hunter.py`; o workflow não apaga nada por conta própria |
| ~~K22~~ | ~~Constante mágica `if zz<40` no trim de qualidade~~ — **resolvido** | virou `params.quality_skip_front`, com o padrão 40 preservado |
| ~~K23~~ | ~~Nomenclatura enganosa (`trinity` executa SPAdes)~~ — **documentado** | `config/default.yaml` diz `"trinity" (usa SPAdes)` na própria linha |

## Baixas

`.pyc` e `.gif` versionados, sem `.gitignore` · `.xls` que é HTML renomeado
([`blast_output_sort.py:239`](../script/report/build_report.py#L239)) · ativos front-end
referenciados mas ausentes (`sorttable.js`, `ajax_select.js`, `DataTables-1.9.4/`), de modo
que os relatórios HTML não renderizam só com este repositório · ~30% de
`virus_hunter.py` é código comentado · indentação mista · imports duplicados.

---

## Proposta de validação

Hoje **não existe nenhuma forma de demonstrar que uma mudança preservou o comportamento**
(ver [`architecture.md`](architecture.md)). Enquanto isso for verdade, qualquer alteração
em código de pipeline é uma aposta — inclusive as correções críticas acima.

Proposta, em ordem de custo crescente:

**Nível 0 — verificação estrutural (imediata, sem infraestrutura).**
Rodar os workers com entradas mínimas construídas à mão e conferir invariantes:
contagem de registros preservada entre etapas (I1, I2), bloco de saída múltiplo de 11
linhas (I4). Não valida ciência, mas pega regressões estruturais e já cobriria K2 e K14.

**Nível 1 — testes unitários dos parsers.**
Os workers de parsing (`blast_parser.py`, `blast_filter_NR.py`, `diamond_filter_NR.py`,
`blast_output_sort.py`) são funções de arquivo-para-arquivo e podem ser testados com XML e
`.m8` sintéticos pequenos, sem banco nem cluster. **É aqui que K1 se torna demonstrável**:
um teste com dois hits de e-values diferentes e um limiar entre eles falha hoje e passa
depois da correção.

**Nível 2 — dado sintético ponta a ponta.**
Um conjunto mínimo — genoma viral conhecido, algum hospedeiro, ~1000 leituras simuladas —
com bancos BLAST reduzidos construídos localmente. Permite rodar o pipeline inteiro em
minutos e comparar a saída contra uma referência. Torna qualquer refatoração verificável.

**Nível 3 — regressão sobre dado real.**
Se existir uma execução real preservada (entrada + saída), congelá-la como referência.
É a única validação que cobre o comportamento científico de verdade.

*Não determinado:* se existe alguma execução real preservada acessível ao grupo. Essa
resposta define se o Nível 3 é viável.

### K26

**`-max_target_seqs 1` não devolve o melhor hit.** Aberta. Descoberta ao testar o BLAST+
2.17 recém-instalado ([ADR-0019](decisions/0019-local-tools.md)): a própria ferramenta
avisa.

```
$ blastx -max_target_seqs 1 -outfmt 5 -db protdb -query leitura.fa -out out.xml
Warning: [blastx] Examining 5 or more matches is recommended
```

O parâmetro é largamente entendido como "me dê o melhor hit". Não é o que ele faz: o BLAST
interrompe a busca ao acumular o número pedido de alinhamentos, **antes** de ordenar por
qualidade. Com `1`, o hit devolvido é o primeiro encontrado na ordem em que o banco foi
percorrido, que só coincide com o melhor por acaso.

O pipeline usa `-max_target_seqs 1` em **todas** as buscas: 4 ocorrências no `Snakefile`,
11 em `virus_hunter.py`. Inclui a busca viral e a busca contra o NR.

**Por que isso morde aqui em particular.** O filtro contra NR compara o hit viral com o
melhor hit não viral. Se nenhum dos dois lados é de fato o melhor, a comparação perde o
sentido — nas duas rotas, `diamond` e `blast`. É uma questão independente do limiar de
e-value ([K1](#k1)) e independente da escolha entre as rotas
([ADR-0005](decisions/0005-nr-filter-strategy.md)).

**Não é regressão desta refatoração.** Está no código desde 2015 e o valor foi preservado
como estava. O que mudou é que agora existe evidência direta, emitida pela ferramenta.

**Não determinado:** se a versão 2.2.31 usada no cluster tinha o mesmo comportamento. O
aviso é recente, mas o comportamento subjacente é antigo — foi documentado publicamente em
2018 (Shah et al., *Bioinformatics*, "Misunderstood parameter of NCBI BLAST impacts the
correctness of bioinformatics workflows"), três anos depois do artigo do pipeline.

**Correção requer decisão científica**, não técnica: subir `-max_target_seqs` (o BLAST
sugere 5 ou mais) muda o resultado de todas as buscas. Fica registrado, não corrigido.

### K27

**Caminhos de cluster fixos dentro dos filtros NR.** Corrigida em 2026-08-15.

Os dois filtros abriam o FASTA viral por caminho absoluto, apesar de a configuração já
trazer o valor em `databases.virus_fasta`:

```python
# diamond_filter_NR.py
f = open('/mnt/cluster/xdeng/blastdb/virus.fa', 'r')
# blast_filter_NR.py -- caminho diferente, para o mesmo arquivo
f = open('/mnt/cluster/xdeng/blastdb/virus/virus.fa', 'r')
```

Nenhuma das duas chamadas tinha proteção, então em qualquer máquina sem `/mnt/cluster` o
filtro morria com `FileNotFoundError`. Como `diamond_filter_NR.py` é o filtro ativo por
padrão, **a rota padrão inteira não chegava ao fim** — o defeito ficou escondido enquanto o
pipeline só rodou no cluster de origem.

Os dois casos exigiam correções diferentes:

- **`diamond_filter_NR.py`:** o retorno de `readVirusGI()` **nunca era usado**. A função
  lia um arquivo grande, montava um conjunto de GIs e o descartava. Removidas a função e a
  chamada — a saída é a mesma, sem o arquivo e sem o custo.
- **`blast_filter_NR.py`:** ali o conjunto **é** usado, passado a `readNRXML` para impedir
  que um hit viral entre no conjunto "não viral" e seja usado contra si mesmo. Passou a ler
  `databases.virus_fasta` da configuração.

Descoberto ao investigar por que a seção `cluster:` continuava em `config/default.yaml`.
A seção foi removida no mesmo commit: nada a lia depois que `virus_hunter.py` saiu da
árvore ([ADR-0020](decisions/0020-prune-to-the-migrated-version.md)). Os valores originais
seguem em `config/cluster-legacy.yaml`.

**Não verificado:** por que os dois caminhos diferiam (`blastdb/virus.fa` e
`blastdb/virus/virus.fa`). Se apontavam para arquivos diferentes, as duas rotas do filtro
nunca compararam contra o mesmo conjunto viral.

### K28

**`print >>arquivo, texto` sobrevive ao compilador.** Corrigida em 2026-08-15.

`web/catAlignFA.py` usava a sintaxe de Python 2 para escrever em arquivo. Ela **parseia**
em Python 3 sem erro — o interpretador a lê como `print >> arquivo` seguido de uma tupla —
e só falha na execução, com `TypeError`.

Isso invalida uma verificação que eu vinha usando: compilar em Python 3 **não** prova que
um arquivo foi portado. A afirmação "24 de 24 compilam, logo 100% portado", registrada na
[ADR-0020](decisions/0020-prune-to-the-migrated-version.md), era forte demais.

Varredura dos demais padrões que passam pelo compilador (`has_key`, `xrange`, `iteritems`,
`unicode`, `basestring`): nenhum outro caso no código restante.

### K29

**Ferramentas invocadas como nome nu, fora da configuração.** Corrigida em 2026-08-15.

Três casos, todos encontrados ao reorganizar `script/`:

| Onde | Invocava | Consequência |
|---|---|---|
| `report/blastdb_alias.py` | `blastdb_aliastool` | o binário está em `tools/bin/`, não no `PATH`; a regra falhava |
| `report/build_report.py` | `faSort.py` e `viralCount.py` sem interpretador | depende do shebang, que **não funciona no Windows**; o retorno era ignorado, então falhava em silêncio |
| `web/cat.php` | `E:\wamp64\www\catAlignFA.py` | caminho absoluto de outra máquina |

Os três passaram a receber o caminho da configuração ou a usar `sys.executable`/`__DIR__`.
O padrão de fundo é o mesmo: uma ferramenta externa referida por nome, sem passar pela
configuração, que só funciona na máquina onde foi escrita.

### K30

**O `.gitignore` escondeu o fixture de teste, e eu o apaguei.** Corrigido em 2026-08-15.

A linha `fastq/` do `.gitignore` — pensada para os dados de entrada reais, que não devem
ser versionados — casava também com `tests/reference/fixture/fastq/`. O fixture **nunca
esteve no Git**, em nenhum commit.

Ao reorganizar `tests/`, um `git mv` da pasta falhou justamente por ela não ser rastreada,
e o `rm -rf` seguinte a apagou do disco. Não havia de onde recuperar.

O fixture foi recriado a partir do que a documentação registrava: quatro FASTQ com a
convenção de nomes do sequenciador e um `samples.txt`. A equivalência funcional foi provada
pelo único critério que importa aqui — as seis rotas do DAG voltaram a resolver nos mesmos
números: 349, 355, 357, 369, 445 e 349.

Causa raiz corrigida: `!tests/fixture/fastq/**` abre a exceção, e a checagem
`git check-ignore` confirma que o fixture passou a ser versionável.

É a segunda vez que uma regra ampla demais no `.gitignore` esconde algo que importava — a
primeira foi o commit `1a9ce92`, que corrigiu a exclusão da referência congelada. A lição
que ficou: depois de qualquer `git mv` ou `git rm` numa pasta, conferir que ela estava
rastreada **antes** de remover qualquer coisa do disco.

### K31

**`fasta_to_fastq.py` escreve a última sequência errada.** Aberta.

Depois do laço, o script repete o bloco de escrita usando `id` e `seq1` — mas `seq1` só é
atribuído dentro do `if`, então guarda a sequência **anterior**, enquanto a última fica em
`seq` e nunca é usada. O último registro do arquivo sai duplicando o penúltimo.

Encontrado ao restaurar a rota `fasta-input` do histórico. **Não corrigido:** é alteração
de comportamento numa rota que nunca foi exercida, e a decisão de mudar a saída é sua.

### K32

**Vários `--configfile` não se combinam.** Contornada em 2026-08-15.

O Snakemake substitui a seção inteira em vez de fundir. Passar
`--configfile denovo.yaml --configfile contigs-only.yaml` faz o pipeline enxergar apenas
`{"skip_reads": true}` — a montagem some **sem nenhum aviso**.

Verificado imprimindo o `config` que o workflow recebe. Contornado com
`--config routes=a,b`, que usa a fusão profunda de `virushunter.config.merge`.

### K33

**Duas rotas do gerador original quebram quando ligadas.** Aberta, herdada.

Descoberto ao recapturar a referência de cada rota com o gerador recuperado do histórico:

| Configuração | Erro |
|---|---|
| `host_filter.keep_human: true` com `keep_bacteria: true` (o padrão) | `UnboundLocalError: bowindex` |
| `merge_pairs: true` com `paired_end: true` | `IndexError: list index out of range` |

**`keep_human`:** as linhas 910-912 de `virus_hunter.py` cobrem três das quatro
combinações. Falta justamente "manter os dois", em que não sobra nada contra o que alinhar,
e `bowindex` nunca é atribuído. O workflow migrado agora recusa essa combinação com uma
mensagem explícita, em vez de estourar.

**`merge_pairs`:** depois que o FLASH funde o par, existe um arquivo só, mas a linha 870
indexa `fqfils[1]` quando `pair` é verdadeiro. A combinação é contraditória — fundidas, as
leituras deixam de ser um par — e o código não trata isso.

As variantes que fazem sentido funcionam: `keep_human: true` com `keep_bacteria: false`
gera 57 artefatos sem erro, e `merge_pairs` com `paired_end: false` gera 58.

### K34

**A rota HMMER/vFam nunca funcionou.** Aberta, herdada. Descoberta em 2026-08-15.

Ao capturar a referência da rota com `steps.hmmer: true` e `steps.mystery: true`, o
`pipeline_run.sh` gerado manda executar **sete arquivos que o gerador nunca cria**:

```
dna2protmys.sh   hmmer_nr_filter.sh   hmmer_nr_mystery.txt
hmmer_nr_mystery_filter.sh   hmmer_output_sort.sh   hmmer_virus.txt
hmmer_virus_parser.sh
```

Na rota padrão, esse mesmo teste não acusa nenhum ausente — o problema é específico da
rota.

Cada um desses nomes aparece **uma única vez** em `virus_hunter.py`: na linha
`sf.write('source X.sh...')` que o coloca dentro do `pipeline_run.sh`. Não existe, em
lugar nenhum do arquivo, código que os escreva. A execução falharia na primeira linha,
com "No such file or directory".

Pior: dos três scripts que a rota **de fato** produz, o que roda o HMMER —
`vfam.sh`, com a chamada `hmmsearch --cpu 48 -E 0.001 -A ... --tblout ...` — **não é
executado** pelo `pipeline_run.sh`. São executados apenas `dna2prot.sh`, que só prepara a
entrada, e `vfam_annot.sh`, que anota uma saída que nunca foi produzida.

**Consequência para a migração:** não há comportamento original a preservar. Migrar esta
rota seria **escrever uma rota nova**, não portar uma existente — decisão científica, não
técnica, e portanto de quem conhece o método. Fica como está: a chave `steps.hmmer`
continua na guarda de não implementadas.

Some-se a isso que `hmmsearch` não tem build para Windows e o banco vFam não está
disponível, então nem haveria como conferir o resultado.

### K35

**`steps.mystery` nunca controlou a fusão dos contigs.** Chave removida em 2026-08-15.

O nome sugere ligar e desligar a investigação das sequências que não se pareceram com nada.
Não era isso: no gerador, `doMyth` aparece em dois lugares, ambos dentro da cadeia
HMMER/vFam que [K34](#k34) mostrou nunca ter funcionado.

A fusão dos contigs sem hit — `merge_mystery` e `merge_mystery_all` — sempre aconteceu,
com a chave ligada ou desligada. Confirmado na referência: `blast_output_merge.sh`, que o
`pipeline_run.sh` executa em qualquer configuração, faz o `cat` dos `_m.fasta`.

A chave saiu da configuração. As saídas continuam sendo produzidas, como no original.
Mantê-la seria oferecer um interruptor ligado a nada.

### K36

**A montagem da pseudo-amostra da rota `reassemble` lê um arquivo que ninguém escreve.**
Aberta, herdada.

Ao capturar a referência da rota, o `soap_config/reAssemble_soap.config` aponta para
`fastq/reAssemble_1_sequence.txt`. Mas o `fq_clean.sh` da mesma captura produz apenas
`S1_1_sequence.txt` e `S2_1_sequence.txt` — o arquivo da pseudo-amostra **nunca é criado**.

A causa está na ordem do gerador: depois de `reAssemble()`, a linha `seeds={'reAssemble':[]}`
substitui o conjunto de amostras por uma pseudo-amostra **com lista de arquivos vazia**.
Os scripts de montagem escritos em seguida referem-se a ela, mas nada gera as leituras.

**Diferença para o [K34](#k34):** ali a rota inteira era inexecutável. Aqui só essa parte
é. O núcleo da rota — juntar os contigs de todas as amostras, fazer o consenso com CAP3,
mapear cada amostra de volta e contar — parte de `fastq/{amostra}_contig4`, que existe, e
funciona.

Foi isso que se migrou. A montagem espúria da pseudo-amostra ficou de fora, por não ter
entrada. Quem quiser uma remontagem de leituras, e não de contigs, precisa defini-la — não
há comportamento original a preservar.

### K37

**`diamond.fa` recebe identificadores duplicados.** Aberta, herdada.

O contador `total` reinicia a cada chamada de `addTaxon`, e as duas chamadas — proteínas
virais do RefSeq e depois o NR — escrevem no **mesmo** arquivo, a segunda em modo de
acréscimo. A primeira sequência de cada passagem sai como `>VIRUS_1_...`.

Observado no fixture da [ADR-0022](decisions/0022-migrate-taxonomy-split.md): `diamond.fa`
tem duas entradas `VIRUS_1`.

Não quebra o filtro: [`filter_nr.py`](../script/search/filter_nr.py) lê apenas o prefixo
até o primeiro `_`. Mas um banco com identificadores repetidos é defeito: o
`makeblastdb -parse_seqids` recusaria, e qualquer rastreamento de qual sequência gerou um
acerto fica ambíguo.

Corrigir é mudança de comportamento — os identificadores do banco mudariam — e portanto
decisão de quem vai usar o resultado.

### ~~K38~~ — `steps.nr_filter` não desligava nada — **RESOLVIDO**

A chave existia no `default.yaml` desde a ADR-0015, era lida na linha 66 do `Snakefile`
para a variável `FILTRO_NR`, e **nunca era usada em lugar nenhum**. Pôr `false` não mudava
uma única tarefa do DAG: a busca contra o NR acontecia sempre.

Ficou escondida porque o levantamento anterior de chaves inertes procurou chaves sem
menção no `Snakefile`, e esta *era* mencionada — só não surtia efeito. Uma chave lida e
ignorada é pior que uma nunca lida: parece funcionar.

Descoberta ao procurar como rodar o pipeline numa máquina com 425 GB livres, onde o banco
do DIAMOND (mais de 500 GB) não cabe.

**Resolvido** na [ADR-0024](decisions/0024-optional-nr-filter.md): `false` agora remove do
DAG a busca contra o NR e o passo que a alimenta, e o filtro passa a operar em modo
`nenhum`, que não descarta nada. Verificado: 350 → 346 tarefas, e as outras dezenove rotas
mantêm a contagem de antes.

### K39 — O `except` nu disfarçou um erro de tipo de "XML mal formado"

Ao implementar o modo `nenhum`, o campo `LNVNRE` caiu num ramo que chamava `.get()` sobre
um **conjunto**. O `AttributeError` resultante foi capturado pelo `except Exception:` do
`OutputVirus`, que imprimiu `XML format bad` e seguiu — produzindo um arquivo vazio com a
mensagem `n_hits = 1` na tela.

A mensagem apontava para o arquivo errado: o XML estava perfeito, verificado com um parser
independente. Foram quatro tentativas de diagnóstico até instrumentar o código e ver o erro
real.

É a demonstração concreta do custo do [K5](#k5--falha-é-indistinguível-de-sucesso), num
caso em que o defeito era meu e recente. Num dado científico o mesmo `except` transformaria
um erro de leitura em "nenhum vírus encontrado".
