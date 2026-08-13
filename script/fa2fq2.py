#!/usr/bin/env python
import sys
f=open(sys.argv[1], 'r')
of=open(sys.argv[2],'w')
i=0
seq=[]
for line in f:
	if line.strip().startswith('>'):
		i+=1
		id='@seq'+str(i)
		seq1=''.join(seq)
		if seq1!='':
			print(id, file=of)
			print(seq1, file=of)
			print('+', file=of)
			print(''.join(len(seq1)*['I']), file=of)
			seq=[]
	else:
		seq.append(line.strip())

print(id, file=of)
print(seq1, file=of)
print('+', file=of)
print(''.join(len(seq1)*['I']), file=of)

f.close()
of.close()