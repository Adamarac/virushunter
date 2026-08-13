ssh bsidna4 /mnt/cluster/xdeng/script/trim_quality.py /mnt/work/fastq/S1_1.ada /mnt/work/fastq/S1_1.trim 33 /mnt/work/fastq/A_S1_L001_R1_001.fastq.gz &
ssh bsidna5 /mnt/cluster/xdeng/script/trim_quality.py /mnt/work/fastq/S1_2.ada /mnt/work/fastq/S1_2.trim 33 /mnt/work/fastq/A_S1_L001_R2_001.fastq.gz &
ssh bsidna6 /mnt/cluster/xdeng/script/trim_quality.py /mnt/work/fastq/S2_1.ada /mnt/work/fastq/S2_1.trim 33 /mnt/work/fastq/B_S2_L001_R1_001.fastq.gz &
ssh bsidna7 /mnt/cluster/xdeng/script/trim_quality.py /mnt/work/fastq/S2_2.ada /mnt/work/fastq/S2_2.trim 33 /mnt/work/fastq/B_S2_L001_R2_001.fastq.gz &
