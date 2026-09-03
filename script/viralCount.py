#!/usr/bin/env python
import sys
from collections import defaultdict

def getBarcode(line, cwd):
	parts=line.strip().split()
	readid=parts[0]
	barcode=readid[(readid.find(cwd)+1+len(cwd)):]
	return barcode

def ViralCount(infile, outfile, base, virname):
	counts=defaultdict(int)
	f = open(infile, 'r')
	of = open(outfile, 'a')
	for line in f:
		if line.strip().startswith('>'):
			barcode =getBarcode(line, base)
			counts[barcode]+=1
	f.close()
	for barcode in list(counts.keys()):
		of.write(barcode+'\t'+virname+'\t'+str(counts[barcode])+'\n')
	of.close()

if __name__ == '__main__':
	infile, outfile, cwd, virname= sys.argv[1:5]
	ViralCount(infile, outfile, cwd, virname)

