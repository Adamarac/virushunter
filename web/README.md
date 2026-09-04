# web/ — interface de consulta (separada do pipeline)

Estes arquivos **não fazem parte do pipeline**. São uma aplicação PHP que rodava num
servidor web próprio, para consultar os resultados depois de prontos.

Foram separados de `script/` porque estavam lá apenas por proximidade: a regra `publish`
do workflow copia os `.php` para a pasta do relatório, e isso os fazia parecer parte da
execução.

## Estado: não funciona como está

Evidência levantada ao ler os arquivos:

- **Todas as dependências de front-end estão ausentes** do repositório. Os `.php` e o HTML
  gerado por `report/build_report.py` carregam `jquery.js`, `jquery.dynatree.js`,
  `jquery.cookie.js`, `ui.dynatree.css`, `DataTables-1.9.4/`, `sorttable.js` e
  `ajax_select.js`. Nenhum desses arquivos existe aqui, e não há registro de onde vinham.
- `cat.php` apontava para `E:\wamp64\www\catAlignFA.py` — caminho absoluto de um servidor
  **WAMP em outra máquina**. Trocado por `__DIR__`, que resolve para esta pasta.
- `catAlignFA.py` usava `print >>arquivo, texto`, sintaxe de Python 2. Isso **parseia** em
  Python 3 sem erro (é lido como `print >> arquivo` seguido de uma tupla) e só quebra na
  execução — por isso passou despercebido nas verificações de compilação. Corrigido.

## O que cada arquivo faz

| Arquivo | Função |
|---|---|
| `blast.php`, `blast_run.php` | formulário de busca BLAST interativa e execução |
| `price.php`, `price_run.php` | mesma ideia para o montador PRICE |
| `cat.php` | filtra alinhamentos por faixa de e-value, chamando `catAlignFA.py` |
| `update.php` | atualização de arquivos pela interface |
| `catAlignFA.py` | ordena alinhamento HTML e FASTA por e-value, dentro de uma faixa |
| `tablestyle.css`, `wait.gif` | usados pelo relatório gerado pelo pipeline |

`tablestyle.css` e `wait.gif` ficam aqui porque a página HTML que o pipeline gera os
referencia. A regra `publish` copia os dois junto com os `.php`.

## Para colocar no ar

Faltam três coisas, nesta ordem: obter as bibliotecas de front-end ausentes, um servidor
PHP apontando para esta pasta, e revisar `blast_run.php` e `price_run.php` — eles executam
comandos montados a partir de entrada do formulário, o que merece uma olhada de segurança
antes de ficar acessível.
