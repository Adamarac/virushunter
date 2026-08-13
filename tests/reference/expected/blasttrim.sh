ssh bsidna4 /mnt/cluster/xdeng/script/blast_trim.py /mnt/work/fastq/S2_1.dup /mnt/work/fastq/S2_1.tab /mnt/work/fastq/S2_1.ada work_S2 1 &
ssh bsidna5 /mnt/cluster/xdeng/script/blast_trim.py /mnt/work/fastq/S2_2.dup /mnt/work/fastq/S2_2.tab /mnt/work/fastq/S2_2.ada work_S2 2 &
ssh bsidna6 /mnt/cluster/xdeng/script/blast_trim.py /mnt/work/fastq/S1_1.dup /mnt/work/fastq/S1_1.tab /mnt/work/fastq/S1_1.ada work_S1 1 &
ssh bsidna7 /mnt/cluster/xdeng/script/blast_trim.py /mnt/work/fastq/S1_2.dup /mnt/work/fastq/S1_2.tab /mnt/work/fastq/S1_2.ada work_S1 2 &
