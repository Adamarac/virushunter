#!/usr/bin/env python
"""Replace every FASTQ header with the read's positional identity.

The identifier the sequencer assigned is discarded; what identifies a read from
here on is where it sits in the file. See docs/invariants.md, invariant I1.

The identity format and the ordinal arithmetic now live in
virushunter.domain.ReadId, shared with fq2faID.py and blast_trim.py, which have
to agree with this file exactly.
"""

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
