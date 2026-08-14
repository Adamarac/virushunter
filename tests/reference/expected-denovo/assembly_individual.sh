source partition.sh
wait
source soap.sh
wait
source meta_velvet.sh
wait
source abyss.sh
wait
source abyss_partition.sh
wait
source abyss_combine.sh
wait
echo Welcome39 |find . "*" -print0 | sudo xargs -0 chmod 777
source moveContig.sh
