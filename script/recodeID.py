#!/usr/bin/env python
"""Substitui cada cabecalho FASTQ pela identidade posicional da leitura (I1)."""

import sys

from virushunter.domain import LINES_PER_RECORD, ReadId

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
        print(ReadId.at_line(i, pair_end, label), file=of)
    else:
        print(line.strip(), file=of)
f.close()
of.close()
