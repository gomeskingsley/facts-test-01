import numpy as np
import os
import fnmatch
import re
import time
import argparse
import shutil
from netCDF4 import Dataset


def sample_from_quantiles(qvals, q, nsamps, seed, missing_value=np.iinfo(np.int16).min):

	if np.all(qvals==missing_value):
		pool = np.full((nsamps), np.nan)
	else:
		np.random.seed(seed)
		pool = np.interp(np.linspace(0,1,nsamps), q, qvals)
		np.random.shuffle(pool)
	return(pool)


def total_global(directory, pyear_start, pyear_end, pyear_step, nsamps):

	# Years of interest
	years = np.arange(pyear_start, pyear_end+1, pyear_step)

	# Output directory
	outdir = os.path.dirname(__file__)

	# Define a running total
	totalsl = np.full((len(years), nsamps), 0.0)

	# Define the output file
	outfilename = "total-workflow_globalsl.nc"
	outfile = os.path.join(outdir, outfilename)

	# Get the list of input files
	infiles = [file for file in os.listdir(directory) if file.endswith(".nc")]

	# Loop through these files
	for infile in infiles:

		# Skip this file if it appears to be a total file already
		if(re.search(r"^total", infile)):
			print("Skipped a total file - {}".format(infile))
			continue

		# Append directory to input file name
		infile = os.path.join(directory, infile)

		# Open the netCDF file
		nc = Dataset(infile, 'r')

		# Get the global projection data
		globalsl = nc.variables['samps'][:]
		ncyears = nc.variables['year'][:]

		# Find where the nc years match the requested years
		(overlap_years, year_idx, ncyears_idx) = np.intersect1d(years, ncyears, return_indices=True)

		# Add this to the running total
		totalsl[year_idx,:] = totalsl[year_idx,:] + globalsl[ncyears_idx,:]

		# Close the netCDF file
		nc.close()

	# Write the combined projections to a netcdf file
	rootgrp = Dataset(outfile, "w", format="NETCDF4")

	# Define Dimensions
	year_dim = rootgrp.createDimension("years", len(years))
	samp_dim = rootgrp.createDimension("samples", nsamps)

	# Populate dimension variables
	year_var = rootgrp.createVariable("years", "i4", ("years",))
	samp_var = rootgrp.createVariable("samples", "i8", ("samples",))

	# Create a data variable
	samps = rootgrp.createVariable("samps", "i2", ("years", "samples"), zlib=True, complevel=4)
	#samps.scale_factor = 0.1

	# Assign attributes
	rootgrp.description = "Total SLR for workflow"
	rootgrp.history = "Created " + time.ctime(time.time())
	rootgrp.source = "FACTS: Post-processed total among available contributors: {}".format(", ".join(infiles))
	samps.units = "mm"

	# Put the data into the netcdf variables
	year_var[:] = years
	samp_var[:] = np.arange(0,nsamps)
	samps[:,:] = totalsl

	# Close the netcdf
	rootgrp.close()

	# Put a copy of the total file back into the shared directory
	shutil.copy2(outfile, directory)

	return(0)



def total_local(directory, pyear_start, pyear_end, pyear_step, nsamps, seed):

	# Define the years of interest
	years = np.arange(pyear_start, pyear_end+1, pyear_step)

	# Output directory
	outdir = os.path.dirname(__file__)

	# Define the output file
	outfilename = "total-workflow_localsl.nc"
	outfile = os.path.join(outdir, outfilename)

	# Get the list of input files
	infiles = [file for file in os.listdir(directory) if file.endswith(".nc")]

	# Is this the first file being parsed?
	first_file = True

	# Seed offset for each component to avoid spurious correlation
	seed_offset = 1000

	# Loop through these files
	file_counter = 0
	for infile in infiles:

		# Skip this file if it appears to be a total file already
		if(re.search(r"^total", infile)):
			print("Skipped a total file - {}".format(infile))
			continue

		# Increment the file counter
		file_counter += 1

		# Full file path
		infile = os.path.join(directory, infile)

		# Open the netCDF file
		nc = Dataset(infile, 'r')

		# Get the years available from this file
		ncyears = nc.variables['years'][:]

		# Find where the nc years match the requested years
		(overlap_years, year_idx, ncyears_idx) = np.intersect1d(years, ncyears, return_indices=True)

		# Get the local projection data
		localsl_quantiles = nc.variables['localSL_quantiles'][:,:,ncyears_idx]
		localsl_quantiles = np.array(localsl_quantiles.filled(np.iinfo(np.int16).min))	# Added to handle components with masked values

		if(first_file):
			ids = nc.variables['id'][:]
			lats = nc.variables['lat'][:]
			lons = nc.variables['lon'][:]
			quantiles = nc.variables['quantiles'][:]
			years = years[year_idx]

		# Close the netCDF file
		nc.close()

		# Produce the summed quantiles
		this_seed = seed + (seed_offset * file_counter)
		localsl_samples = np.apply_along_axis(sample_from_quantiles, axis=0, arr=localsl_quantiles, q=quantiles, nsamps=nsamps, seed=this_seed)
		if(first_file):
			total_samples = localsl_samples
			first_file = False
		else:
			total_samples += localsl_samples
		

	# Calculate the quantiles of the summed up samples
	total_quantiles = np.quantile(total_samples, quantiles, axis=0)

	# Write the total to a netcdf file -------------------------------------
	# Write the localized projections to a netcdf file
	rootgrp = Dataset(outfile, "w", format="NETCDF4")

	# Missing values
	nc_missing_value = np.iinfo(np.int16).min

	# Define Dimensions
	nsites = len(ids)
	nyears = len(years)
	nq = len(quantiles)
	site_dim = rootgrp.createDimension("nsites", nsites)
	year_dim = rootgrp.createDimension("years", nyears)
	q_dim = rootgrp.createDimension("quantiles", nq)

	# Populate dimension variables
	lat_var = rootgrp.createVariable("lat", "f4", ("nsites",))
	lon_var = rootgrp.createVariable("lon", "f4", ("nsites",))
	id_var = rootgrp.createVariable("id", "i4", ("nsites",))
	year_var = rootgrp.createVariable("years", "i4", ("years",))
	q_var = rootgrp.createVariable("quantiles", "f4", ("quantiles",))

	# Create a data variable
	localslq = rootgrp.createVariable("localSL_quantiles", "i2", ("quantiles", "nsites", "years"), zlib=True, complevel=4)
	localslq.missing_value = nc_missing_value
	#localslq.scale_factor = 0.1

	# Assign attributes
	rootgrp.description = "Total SLR for workflow"
	rootgrp.history = "Created " + time.ctime(time.time()) + "; Seed Value {}".format(seed)
	rootgrp.source = "FACTS: Post-processed total among available contributors: {}".format(",".join(infiles))
	lat_var.units = "Degrees North"
	lon_var.units = "Degrees East"
	localslq.units = "mm"

	# Apply the missing value mask to the totals
	total_quantiles[np.isnan(total_quantiles)] = nc_missing_value

	# Put the data into the netcdf variables
	lat_var[:] = lats
	lon_var[:] = lons
	id_var[:] = ids
	year_var[:] = years
	q_var[:] = quantiles
	localslq[:,:,:] = total_quantiles

	# Close the netcdf
	rootgrp.close()

	# Put a copy of the total file back into the shared directory
	shutil.copy2(outfile, directory)

	return(0)



if __name__ == "__main__":

	# Initialize the command-line argument parser
	parser = argparse.ArgumentParser(description="Total up the contributors for a particular workflow.",\
	epilog="Note: This is meant to be run as part of the Framework for the Assessment of Changes To Sea-level (FACTS)")

	# Define the command line arguments to be expected
	parser.add_argument('--directory', help="Directory containing files to aggregate", required=True)
	parser.add_argument('--local', help="Are the listed files local or global files?", action='store_true')
	parser.add_argument('--nsamps', help="Number of samples produced in the individual contributors", default=20000, type=int)
	parser.add_argument('--pyear_start', help="Year for which projections start [default=2000]", default=2000, type=int)
	parser.add_argument('--pyear_end', help="Year for which projections end [default=2100]", default=2100, type=int)
	parser.add_argument('--pyear_step', help="Step size in years between pyear_start and pyear_end at which projections are produced [default=10]", default=10, type=int)
	parser.add_argument('--seed', help="Seed value for random number generator", default=1234, type=int)

	# Parse the arguments
	args = parser.parse_args()

	# Are these global or local files
	if(args.local):
		total_local(args.directory, args.pyear_start, args.pyear_end, args.pyear_step, args.nsamps, args.seed)
	else:
		total_global(args.directory, args.pyear_start, args.pyear_end, args.pyear_step, args.nsamps)


	exit()
