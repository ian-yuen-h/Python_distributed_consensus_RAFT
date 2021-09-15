#!/bin/bash

input="./ports.txt"
while IFS= read -r line     #read in ports
do 
    sudo kill -9 $(sudo lsof -t -i:$line)
    # docker exec -d container1 python3 /hostC/shared/cracker_service.py $line
done < "$input"

rm ./src/databases/*