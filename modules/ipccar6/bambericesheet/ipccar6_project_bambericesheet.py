import numpy as np
import argparse
import pickle
import os
import re
import time
from netCDF4 import Dataset

''' ipccar6_project_bambericesheet.py

This is the projection stage for the Bamber et al. 2019 ice sheet component of the IPCC AR6 module set.

Parameters: 
nsamps              Number of samples to produce
replace             Allow sampling with replacement
rngseed             Seed for the random number generator
pipeline_id         Unique identifier to attach to this pipeline


Output:
"{pipeline_id}_projections.pkl" = User requested samples
"{pipeline_id}_(AIS|EAIS|WAIS|GIS)_globalsl.nc" = Sampled global projections in netCDF file

'''

def ipccar6_project_bambericesheet(nsamps, pipeline_id, replace, rngseed):
	
	# Load the data file
	datafilename = "{}_data.pkl".format(pipeline_id)
	datafile = os.path.join(os.path.dirname(__file__), datafilename)
	
	with open(datafile, 'rb') as f:
		my_data = pickle.load(f)

	years = my_data["targyears"]
	scenario = my_data["scenario"]
	ais_samples = my_data["ais_samps"]
	eais_samples = my_data["eais_samps"]
	wais_samples = my_data["wais_samps"]
	gis_samples = my_data["gis_samps"]
	
	# Generate the sample indices
	np.random.seed(rngseed)
	sample_inds = np.random.choice(ais_samples.shape[0], size=nsamps, replace=replace)
	
	# Store the samples for AIS components
	eais_samps = eais_samples[sample_inds,:]
	wais_samps = wais_samples[sample_inds,:]
	ais_samps = ais_samples[sample_inds,:]
	gis_samps = gis_samples[sample_inds,:]
	   
    # Store the variables in a pickle
	output = {'eais_samps': eais_samps, 'wais_samps': wais_samps, \
				'ais_samps': ais_samps, 'gis_samps': gis_samps, 'years': years, 'scenario': scenario}
	outfilename = "{}_projections.pkl".format(pipeline_id)
	outfile = open(os.path.join(os.path.dirname(__file__), outfilename), 'wb')
	pickle.dump(output, outfile)
	outfile.close()	
	
	# Write the projections to the netCDF files
	WriteNetCDF(pipeline_id, eais_samps, years, nsamps, "EAIS", scenario)
	WriteNetCDF(pipeline_id, wais_samps, years, nsamps, "WAIS", scenario)
	WriteNetCDF(pipeline_id, ais_samps, years, nsamps, "AIS", scenario)
	WriteNetCDF(pipeline_id, gis_samps, years, nsamps, "GIS", scenario)
	
	return(0)


def WriteNetCDF(pipeline_id, global_samps, years, nsamps, ice_source, scenario):
	
	# Write the total global projections to a netcdf file
	nc_filename = os.path.join(os.path.dirname(__file__), "{0}_{1}_globalsl.nc".format(pipeline_id, ice_source))
	rootgrp = Dataset(nc_filename, "w", format="NETCDF4")

	# Define Dimensions
	year_dim = rootgrp.createDimension("years", len(years))
	samp_dim = rootgrp.createDimension("samples", nsamps)

	# Populate dimension variables
	year_var = rootgrp.createVariable("year", "i4", ("years",))
	samp_var = rootgrp.createVariable("sample", "i8", ("samples",))

	# Create a data variable
	samps = rootgrp.createVariable("samps", "f4", ("years", "samples"), zlib=True, least_significant_digit=2)	
	
	# Assign attributes
	rootgrp.description = "Global SLR contribution from {0} from the Bamber et al. 2019 IPCC AR6 workflow".format(ice_source)
	rootgrp.history = "Created " + time.ctime(time.time())
	rootgrp.source = "FACTS: {0} - {1}. ".format(pipeline_id, scenario)
	year_var.units = "[-]"
	samp_var.units = "[-]"
	samps.units = "mm"

	# Put the data into the netcdf variables
	year_var[:] = years
	samp_var[:] = np.arange(nsamps)
	samps[:,:] = global_samps.T

	# Close the netcdf
	rootgrp.close()	

if __name__ == '__main__':
	
	# Initialize the command-line argument parser
	parser = argparse.ArgumentParser(description="Run the IPCC AR6 Bamber et al. 2019 ice sheet projection stage.",\
	epilog="Note: This is meant to be run as part of the ipccar6 module set within the Framework for the Assessment of Changes To Sea-level (FACTS)")
	
	# Define the command line arguments to be expected
	parser.add_argument('--nsamps', help="Number of samples to draw (default = 10)", default=10, type=int)
	parser.add_argument('--replace', help="Allow sampling with replacement (default = 1)", choices=(0,1), type=int, default=1)
	parser.add_argument('--seed', help="Seed for the random number generator (default = 1234)", default=1234, type=int)
	parser.add_argument('--pipeline_id', help="Unique identifier for this instance of the module")

	# Parse the arguments
	args = parser.parse_args()
	
	# Run the projection stage with the provided arguments
	ipccar6_project_bambericesheet(args.nsamps, args.pipeline_id, args.replace, args.seed)
	
	exit()