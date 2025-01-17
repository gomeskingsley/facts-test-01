import numpy as np
import sys
import os
import pickle
import time
import argparse
import re
from netCDF4 import Dataset
from AssignFP import AssignFP
from read_locationfile import ReadLocationFile


''' ar5_postprocess_glacierscmip6.py

This script runs the glacier post-processing task for the AR5 Glaciers CMIP6 workflow.

Parameters: 
locationfile = File that contains points for localization
pipeline_id = Unique identifier for the pipeline running this code

Output: NetCDF file containing local contributions from GIC

'''

def ar5_postprocess_glacierscmip6(locationfilename, pipeline_id):
	
	# Read in the global projections
	projfile = "{}_projections.pkl".format(pipeline_id)
	try:
		f = open(projfile, 'rb')
	except:
		print("Cannot open projfile\n")
		sys.exit(1)
	
	# Extract the projection data from the file
	my_data = pickle.load(f)
	gicsamps = my_data["gicsamps"]
	glac_region_names = my_data["glac_region_names"]
	data_years = my_data["data_years"]
	f.close()
	
	# Read in the configuration information
	configfile = "{}_data.pkl".format(pipeline_id)
	try:
		f = open(configfile, 'rb')
	except:
		print("Cannot open configfile\n")
		sys.exit(1)
	
	# Extract the configuration data
	my_data = pickle.load(f)
	scenario = my_data["scenario"]
	include_models = my_data['include_models']
	include_scenarios = my_data['include_scenarios']
	nmodels = len(include_models)
	f.close()
	
	# Produce the included model string
	model_string_pieces = ["{0}-{1}".format(include_models[x], include_scenarios[x]) for x in np.arange(nmodels)]
	model_string = "Models and scenarios included: " + ", ".join(model_string_pieces)
	
	# Load the site locations	
	locationfile = os.path.join(os.path.dirname(__file__), locationfilename)
	(_, site_ids, site_lats, site_lons) = ReadLocationFile(locationfile)
	
	# Initialize variable to hold the localized projections
	(nsamps, nregions, ntimes) = gicsamps.shape
	nsites = len(site_ids)
	local_sl = np.full((nsites, nsamps, ntimes), 0.0) 
	
	# Loop through the GIC regions
	for i in np.arange(0,nregions):
		
		# Get the fingerprint file name for this region
		thisRegion = glac_region_names[i]
		
		# Get the fingerprints for these sites from this region
		regionfile = os.path.join(os.path.dirname(__file__), "FPRINT", "fprint_{0}.nc".format(thisRegion))
		regionfp = AssignFP(regionfile, site_lats, site_lons)
		
		# Multiply the fingerprints and the projections and add them to the running total
		# over the regions
		local_sl += np.transpose(np.multiply.outer(gicsamps[:,i,:], regionfp), (2,0,1))
	
	# Calculate the quantiles
	out_q = np.unique(np.append(np.linspace(0,1,101), (0.001, 0.005, 0.01, 0.05, 0.167, 0.5, 0.833, 0.95, 0.99, 0.995, 0.999)))
	nq = len(out_q)
	local_sl_q = np.nanquantile(local_sl, out_q, axis=1)
		
	# Write the localized projections to a netcdf file
	rootgrp = Dataset(os.path.join(os.path.dirname(__file__), "{}_localsl.nc".format(pipeline_id)), "w", format="NETCDF4")

	# Define Dimensions
	site_dim = rootgrp.createDimension("nsites", nsites)
	year_dim = rootgrp.createDimension("years", ntimes)
	q_dim = rootgrp.createDimension("quantiles", nq)

	# Populate dimension variables
	lat_var = rootgrp.createVariable("lat", "f4", ("nsites",))
	lon_var = rootgrp.createVariable("lon", "f4", ("nsites",))
	id_var = rootgrp.createVariable("id", "i4", ("nsites",))
	year_var = rootgrp.createVariable("years", "i4", ("years",))
	q_var = rootgrp.createVariable("quantiles", "f4", ("quantiles",))

	# Create a data variable
	localslq = rootgrp.createVariable("localSL_quantiles", "i2", ("quantiles", "nsites", "years"), zlib=True, complevel=4)
	#localslq.scale_factor = 0.1

	# Assign attributes
	rootgrp.description = "Local SLR contributions from glaciers and ice caps according to AR5 glacier_cmip6 workflow"
	rootgrp.history = "Created " + time.ctime(time.time())
	rootgrp.source = "FACTS: AR5 Glacier-CMIP6 workflow - {0}. ".format(scenario) + model_string
	lat_var.units = "Degrees North"
	lon_var.units = "Degrees East"
	localslq.units = "mm"

	# Put the data into the netcdf variables
	lat_var[:] = site_lats
	lon_var[:] = site_lons
	id_var[:] = site_ids
	year_var[:] = data_years
	q_var[:] = out_q
	localslq[:,:,:] = local_sl_q

	# Close the netcdf
	rootgrp.close()
	

if __name__ == '__main__':
	
	# Initialize the command-line argument parser
	parser = argparse.ArgumentParser(description="Run the post-processing stage for the glaciers component of the AR5 SLR projection workflow",\
	epilog="Note: This is meant to be run as part of the Framework for the Assessment of Changes To Sea-level (FACTS)")
	
	# Define the command line arguments to be expected	
	parser.add_argument('--locationfile', help="File that contains name, id, lat, and lon of points for localization", default="location.lst")
	parser.add_argument('--pipeline_id', help="Unique identifier for this instance of the module")
		
	# Parse the arguments
	args = parser.parse_args()
	
	# Run the postprocessing for the parameters specified from the command line argument
	ar5_postprocess_glacierscmip6(args.locationfile, args.pipeline_id)
	
	# Done
	exit()