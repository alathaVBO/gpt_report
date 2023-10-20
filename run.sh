#!/bin/bash
source activate my_environment
jupyter notebook --ip=0.0.0.0 --port=8888 --no-browser --allow-root
