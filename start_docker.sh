#!/bin/bash

docker run --runtime=nvidia -p 8888:8888 -v /home/ubuntu/pollutemenot-ai:/pmn-ai -v /home/ubuntu/data:/data -ti --gpus all -d trainer_1

