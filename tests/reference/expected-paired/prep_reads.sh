ssh bsidna4 cat /mnt/work/fastq/S1_1_sequence.txt  > /mnt/work/fastq/S1.1.fq &
ssh bsidna4 cat /mnt/work/fastq/S1_2_sequence.txt  > /mnt/work/fastq/S1.2.fq &
ssh bsidna5 cat /mnt/work/fastq/S2_1_sequence.txt  > /mnt/work/fastq/S2.1.fq &
ssh bsidna5 cat /mnt/work/fastq/S2_2_sequence.txt  > /mnt/work/fastq/S2.2.fq &
ssh bsidna4 cat /mnt/work/fastq/S1_1_sequence.txt /mnt/work/fastq/S1_2_sequence.txt > /mnt/work/fastq/S1.fq &
ssh bsidna5 cat /mnt/work/fastq/S2_1_sequence.txt /mnt/work/fastq/S2_2_sequence.txt > /mnt/work/fastq/S2.fq &
wait
ssh bsidna4 /mnt/cluster/xdeng/script/fq2fa.py /mnt/work/fastq/S1.fq /mnt/work/fastq/S1.fa 50 &
ssh bsidna5 /mnt/cluster/xdeng/script/fq2fa.py /mnt/work/fastq/S2.fq /mnt/work/fastq/S2.fa 50 &
wait
ssh bsidna4 /mnt/cluster/xdeng/script/fqLenFilter.py /mnt/work/fastq/S1.fq  /mnt/work/fastq/S1abyss.fq 35 &
ssh bsidna5 /mnt/cluster/xdeng/script/fqLenFilter.py /mnt/work/fastq/S2.fq  /mnt/work/fastq/S2abyss.fq 35 &
wait
