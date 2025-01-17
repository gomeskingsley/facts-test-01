#!/bin/bash

python FittedISMIP_preprocess_icesheet.py --pipeline_id icesheets-FittedISMIP-icesheets-ssp585 --scenario ssp585 --tlm_data 1
python FittedISMIP_fit_icesheet.py --pipeline_id icesheets-FittedISMIP-icesheets-ssp585
python FittedISMIP_project_icesheet.py --pipeline_id icesheets-FittedISMIP-icesheets-ssp585 --nsamps 20000 --baseyear 2005 --pyear_start 2020 --pyear_end 2300 --pyear_step 10 --seed 4321 --crateyear_start 2080 --crateyear_end 2100
python FittedISMIP_postprocess_icesheet.py --pipeline_id icesheets-FittedISMIP-icesheets-ssp585 --chunksize 6619 --locationfile $LFILE
