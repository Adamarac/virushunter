#!/usr/bin/env python
# Troca o cabecalho de cada leitura por um nome baseado na posicao dela no arquivo.

import sys

from virushunter.reads import LINES_PER_RECORD, read_id

f = open(sys.argv[1])  # fq dup file
of = open(sys.argv[2], 'w')  # sequence.txt with recoded read ID
label = sys.argv[3]  # library label
try:
    pair_end = sys.argv[4]  # pair 1 or 2
except IndexError:
    pair_end = '1'

i = 0
for line in f:
    i += 1
    if i % LINES_PER_RECORD == 1:
        print(read_id(i, pair_end, label), file=of)
    else:
        print(line.strip(), file=of)
f.close()
of.close()
