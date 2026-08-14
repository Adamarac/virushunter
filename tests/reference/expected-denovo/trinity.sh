{ time ssh bsidna4 "/mnt/cluster/tools/SPAdes-3.11.1-Linux/bin/spades.py -m 64 -k 21,33,55,77 --careful -t 48 -s /mnt/work/fastq/S1.1.fq -o /mnt/work/trinity_S1/"  ; } 2> /mnt/work/S1_trinity.time &
{ time ssh bsidna5 "/mnt/cluster/tools/SPAdes-3.11.1-Linux/bin/spades.py -m 64 -k 21,33,55,77 --careful -t 48 -s /mnt/work/fastq/S2.1.fq -o /mnt/work/trinity_S2/"  ; } 2> /mnt/work/S2_trinity.time &
