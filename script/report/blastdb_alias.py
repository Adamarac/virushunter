#!/usr/bin/env python

import sys
import os
import os.path
from os import listdir
from os.path import isfile, join

if __name__ == '__main__': 
	directory=sys.argv[1]
	wd=sys.argv[2]
	aliastool=sys.argv[3]
	gooddb1 = [ f[0:(len(f)-4)] for f in listdir(wd) if (isfile(join(wd,f)) and f.endswith('.nal')) ]
	gooddb2 = [ f[0:(len(f)-4)] for f in listdir(wd) if (isfile(join(wd,f)) and f.endswith('_blastdb.nhr')) ]
	gooddb = gooddb1+gooddb2
	os.chdir(wd)
	cmd =aliastool+' -dblist '+'\"'+' '.join(gooddb)+'\" -dbtype nucl -out '+directory+'_blastdb -title \"'+directory+'_blastdb\"'
	print(cmd)
	os.system(cmd)