#!/usr/bin/env python
#clean the fastq file into equal length
import sys
f1=open(sys.argv[1], 'r')
f2=open(sys.argv[2], 'r')
of1=open(sys.argv[3],'w')
of2=open(sys.argv[4],'w')

i=0
for line1 in f1:
	line2=f2.readline()
	i+=1
	if i%4==1:
		id1=line1.strip()
		id2=line2.strip()
	elif i%4==2:
		seq1=line1.strip()
		seq2=line2.strip()
	elif i%4==3:
		qid1=line1.strip()
		qid2=line2.strip()
	elif i%4==0:
		qseq1=line1.strip()
		qseq2=line2.strip()
		if len(seq1) >= 20 and len(seq2)>=20:
			#if len(seq1)<20: seq1='N'; qseq1='B'
			#if len(seq2)<20: seq2='N'; qseq2='B'
			#kept=min(len(seq1), len(seq2))
			print(id1, file=of1)
			print(seq1, file=of1)#[0:kept]
			print(qid1, file=of1)
			print(qseq1, file=of1)#[0:kept]
			print(id2, file=of2)
			print(seq2, file=of2)#[0:kept]
			print(qid2, file=of2)
			print(qseq2, file=of2)#[0:kept]
f1.close()
of1.close()
f2.close()
of2.close()