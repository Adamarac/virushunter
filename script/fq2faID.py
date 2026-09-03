#!/usr/bin/env python
# Muda o formato do arquivo e da a cada sequencia um nome baseado na posicao dela.
import gzip
import sys

filename=sys.argv[1]
print(filename)
if filename.endswith('.gz'):f = gzip.open(filename, 'rt')
else: f=open(filename, 'r')
fileID = sys.argv[2]
of=open(sys.argv[3],'w')

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

