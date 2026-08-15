cat /mnt/work/fastq/A_S1_L001_R1_001.fasta.gz > /mnt/work/fastq/S1_c 
/mnt/cluster/xdeng/script/splitQuery.py /mnt/work/fastq/S1_c  50
cat /mnt/work/fastq/B_S2_L001_R1_001.fasta.gz > /mnt/work/fastq/S2_c 
/mnt/cluster/xdeng/script/splitQuery.py /mnt/work/fastq/S2_c  50
