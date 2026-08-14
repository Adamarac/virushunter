#!/usr/bin/env python
"""FASTQ -> FASTA, naming each record by its position in the file.

The ordinal must match what recodeID.py and blast_trim.py compute for the same
read; that shared arithmetic lives in virushunter.domain. See invariant I1.
"""
import gzip
import sys

filename=sys.argv[1]
print(filename)
if filename.endswith('.gz'):f = gzip.open(filename, 'rt')
else: f=open(filename, 'r')
fileID = sys.argv[2]
#of=gzip.open(sys.argv[3],'ab')
of=open(sys.argv[3],'w')
#fileID=os.path.basename(sys.argv[2]).rsplit('.',1)[0]

i=0 #this has to be consistent with blast_trim.py
for line in f:
	i+=1
	if i%4==2:
		seq=line.strip()
		if len(seq)>=10:
			of.write('>'+fileID+'_'+str(i//4)+'\n')
			of.write(seq+'\n')
f.close()
of.close()

