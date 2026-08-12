# Problemas conhecidos

Levantamento sobre o código no estado de 2020. Cada item traz **problema → evidência →
impacto → recomendação**. As recomendações são propostas; nenhuma foi aplicada.

Severidade:

- **Crítica** — compromete execução, confiabilidade ou reprodutibilidade
- **Alta** — dificulta significativamente manutenção ou evolução
- **Média** — melhoria importante, não urgente
- **Baixa** — organização e qualidade

---

## Críticas

### K1 — O limiar de e-value do filtro é inerte

**Evidência.** [`diamond_filter_NR.py:132`](../script/diamond_filter_NR.py#L132) e
[`blast_filter_NR.py:169`](../script/blast_filter_NR.py#L169):

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

**Recomendação.** `E_VALUE_THRESH = float(sys.argv[5])`. Antes de aplicar, verificar se
alguma análise do grupo declarou um limiar diferente de 0,01 nesta etapa — nesse caso os
resultados divergem do documentado e precisam ser reprocessados. Correção pequena, mas
**altera comportamento**: exige ADR e validação.

### K2 — `samNT.py` dessincroniza os arquivos SAM

**Evidência.** [`samNT.py:56-69`](../script/samNT.py#L56-L69) — o `break` no primeiro
acerto deixa os demais handles sem avançar. Viola
[I2](invariants.md#i2--arquivos-paralelos-são-lidos-em-correspondência-posicional).

**Impacto.** A partir da primeira leitura classificada, os 14 arquivos SAM ficam
desalinhados e leituras diferentes passam a ser comparadas entre si. **As contagens
taxonômicas da rota NT são não confiáveis.** A rota está desligada no estado commitado,
mas o código sugere que já foi usada.

**Recomendação.** Ler uma linha de **todos** os handles antes de avaliar acertos; só então
decidir. Acrescentar verificação de que todos os SAMs têm a mesma contagem de linhas.

### K3 — Troca silenciosa de modo de análise

**Evidência.** [`sam2fq_bac.py:152-153`](../script/sam2fq_bac.py#L152-L153):

```python
try: processBacSAM(...)             # paired-end
except: processSingleBacSAM(...)    # single-end
```

**Impacto.** Qualquer exceção — `IndexError`, `ZeroDivisionError`, arquivo faltando,
defeito no código — **troca o modo de análise**, possivelmente depois de já ter escrito
parte da saída. Não há registro algum da troca.

**Recomendação.** Decidir o modo por parâmetro explícito e falhar alto em erro.

### K4 — Credenciais em texto claro e `chmod 777`

**Evidência.** [`virus_hunter.py:1950`](../script/virus_hunter.py#L1950)
(`password='Welcome39'`, usada em `echo <senha> | sudo` em cinco pontos);
credenciais FTP em comentários nas linhas 146, 150, 159 e 160; e em
[`script/readme.txt:44`](../script/readme.txt#L44).

**Impacto.** Segredos públicos desde 2020. `chmod 777 -R` recursivo torna dados e bancos
graváveis por qualquer usuário do cluster.

**Recomendação.** Tratar todas as credenciais como **comprometidas** e rotacioná-las —
removê-las do código não desfaz a exposição. Substituir `777` por grupo Unix com `775`/`664`.

### K5 — Falha é indistinguível de sucesso

**Evidência.** [`schedule2.py:14-25`](../script/schedule2.py#L14-L25) decide conclusão por
existência e tamanho do arquivo de saída, não por código de saída;
[`blast_parser.py:88`](../script/blast_parser.py#L88) engole XML truncado com
`except: print 'bad xml'`; 39 `except:` nus só em `virus_hunter.py`.

**Impacto.** Um BLAST morto por falta de memória depois de escrever XML parcial conta como
sucesso, e o pipeline segue com dados incompletos produzindo relatório de aparência normal.

**Recomendação.** Código de saída como critério primário; `set -euo pipefail` nos shells
gerados; substituir `except:` nus por exceções específicas; validar contagens de registro
entre etapas.

### K6 — Bancos de dados sem versionamento

**Evidência.** [`script/readme.txt:6-9`](../script/readme.txt#L6-L9):

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

### K7 — Não-determinismo dependente do nó de execução

**Evidência.** [`virus_hunter.py:1680`](../script/virus_hunter.py#L1680):

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

**Recomendação.** Fixar o limite de memória na configuração, nunca derivá-lo do nó.
Ordenar `seeds` deterministicamente. Registrar nó, semente e versões em cada execução.

---

## Altas

| # | Problema | Evidência | Impacto |
|---|---|---|---|
| K8 | Cinco forks do orquestrador; `soap_single()` duplicada | [`orchestrators.md`](orchestrators.md); `readseeds2.py:421` e `:594` | Correções não se propagam; readme aponta para um, o superset é outro |
| K9 | Configuração dentro do código | [`virus_hunter.py:1950-1992`](../script/virus_hunter.py#L1950-L1992) | Cada análise é um patch no fonte; parâmetros não versionáveis com o resultado |
| K10 | `serverInfo()` em tempo de import | [`virus_hunter.py:205`](../script/virus_hunter.py#L205) | Nada é importável, testável ou analisável estaticamente |
| K11 | Formato posicional de 11 linhas | [I4](invariants.md#i4--um-resultado-é-um-bloco-posicional-de-exatamente-11-linhas) | Corrupção silenciosa a qualquer mudança de formato |
| K12 | Python 2 sem suporte desde 01/01/2020 | 119 de 155 arquivos usam `print` statement | Sem patches; **K1 só é possível por causa da semântica do Py2** |
| K13 | Caminhos absolutos divergentes entre workers | `blast_filter_NR.py:28` vs `diamond_filter_NR.py:28` | Possível uso de referências diferentes pelos dois filtros |
| K14 | `argv[4]` usado duas vezes | [`blast_output_sort.py:427-428`](../script/blast_output_sort.py#L427-L428) | `cwd` recebe o valor de `base`; afeta rótulos na tabela final |
| K15 | Duplicação de `CacheLines()` e `Node` | 5 cópias de `CacheLines`; `Node` divergente entre `acc_tax.py:16` e `nr_virus3.py:42` | Correção precisa ser aplicada N vezes |

## Médias

| # | Problema | Evidência |
|---|---|---|
| K16 | ~68% dos `.py` são de outros domínios | [`architecture.md`](architecture.md) |
| K17 | Nenhuma dependência declarada | Biopython, R e ~17 ferramentas externas sem manifesto |
| K18 | Nenhum teste ou dado de exemplo | Repositório inteiro |
| K19 | `readVirusGI()` lê o FASTA viral e o resultado é descartado | [`diamond_filter_NR.py:139`](../script/diamond_filter_NR.py#L139) |
| K20 | `gzip.sopen` — método inexistente | [`dedup.py:113`](../script/dedup.py#L113); mascarado pelo `except` nu |
| K21 | `clean_dir()` apaga todo arquivo não-`.gz` | [`virus_hunter.py:797-801`](../script/virus_hunter.py#L797-L801) |
| K22 | Constante mágica `if zz<40` no trim de qualidade | [`trim_quality.py:127`](../script/trim_quality.py#L127) |
| K23 | Nomenclatura enganosa (`trinity` executa SPAdes) | [`virus_hunter.py:1667`](../script/virus_hunter.py#L1667) |

## Baixas

`.pyc` e `.gif` versionados, sem `.gitignore` · `.xls` que é HTML renomeado
([`blast_output_sort.py:239`](../script/blast_output_sort.py#L239)) · ativos front-end
referenciados mas ausentes (`sorttable.js`, `ajax_select.js`, `DataTables-1.9.4/`), de modo
que os relatórios HTML não renderizam só com este repositório · ~30% de
`virus_hunter.py` é código comentado · indentação mista · typo `cahche` em
[`samNT.py:40`](../script/samNT.py#L40) · imports duplicados.

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
