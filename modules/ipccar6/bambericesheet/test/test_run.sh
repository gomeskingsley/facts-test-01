#!/bin/bash

python ipccar6_preprocess_bambericesheet.py --pipeline_id icesheets-ipccar6-bambericesheet-ssp585 --scenario rcp85 --baseyear 2005 --pyear_start 2020 --pyear_end 2300 --pyear_step 10
python ipccar6_fit_bambericesheet.py --pipeline_id icesheets-ipccar6-bambericesheet-ssp585
python ipccar6_project_bambericesheet_dev.py --pipeline_id icesheets-ipccar6-bambericesheet-ssp585 --nsamps 20000 --seed 4321
python ipccar6_postprocess_bambericesheet_dev.py --pipeline_id icesheets-ipccar6-bambericesheet-ssp585 --chunksize 662 --locationfile $LFILE
