{ time ssh bsidna4 "cd /mnt/work && /mnt/cluster/tools/abyss/bin/abyss-pe -C /mnt/work/abyss_S1 name=S1 k=31 se=/mnt/work/fastq/S1abyss.fq" ; } 2> /mnt/work/S1_abyss.time &
{ time ssh bsidna5 "cd /mnt/work && /mnt/cluster/tools/abyss/bin/abyss-pe -C /mnt/work/abyss_S2 name=S2 k=31 se=/mnt/work/fastq/S2abyss.fq" ; } 2> /mnt/work/S2_abyss.time &
