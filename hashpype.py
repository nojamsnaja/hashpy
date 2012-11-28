#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  hashpype.py
#
# by Mark Williams 2012.313
# First motion focal mechanism classes for running HASH

# import all Fortran subroutines and common blocks from the mod
# plus my custom utils and numpy arrays

import numpy as np
import os.path
from libhashpy import *
from hash_utils import fortran_include, get_sta_coords

# for HASH compatiblity, change later.
degrad = 180. / np.pi
rad = 1. / degrad


class HashPype(object):
	'''Object which holds all data from a HASH instance for one event
	
	The variables are named and structured as close to the original code
	as possible. Methods act on the variables within this namespace and
	most are accessible as attributes.
	
	One can make a "HASH" driver program by calling the methods of this
	class on the data held within it.
	'''
	# These MUST be the same as the fortran includes!!
	# (They are compiled into the Fortran subroutines)
	npick0, nmc0, nmax0 = None, None, None
	dang0, ncoor        = None, None
	
	# initialize arrays
	
	# Input arrays
	sname     = None
	scomp     = None
	snet      = None
	pickpol   = None
	pickonset = None
	p_pol     = None
	p_qual    = None
	spol      = None
	p_azi_mc  = None
	p_the_mc  = None
	index     = None
	qdep2     = None
	
	# Output arrays
	f1norm  = None
	f2norm  = None
	strike2 = None
	dip2    = None
	rake2   = None
	str_avg = None
	dip_avg = None
	rak_avg = None
	var_est = None
	var_avg = None
	mfrac   = None
	stdr    = None
	prob    = None
	qual    = None
	
	# Chosen fm run setings: (pf file should look like this:)
	# dbhash.pf -----------------------------------------------------
	# Defaults
	npolmin  = 8    # Enter mininum number of polarities (e.g., 8)
	max_agap = 90   # Enter maximum azimuthal gap (e.g., 90)
	max_pgap = 60   # Enter maximum takeoff angle gap (e.g., 60)
	dang     = 5    # Enter grid angle for focal mech search, in degrees 5(min {0})
	nmc      = 30   # Enter number of trials (e.g., 30)
	maxout   = 500  # Enter maxout for focal mech. output (e.g., 500)
	badfrac  = 0.1  # Enter fraction of picks presumed bad (e.g., 0.10)
	delmax   = 500  # Enter maximum allowed source-station distance, in km (e.g., 120)
	cangle   = 45   # Enter angle for computing mechanisms probability, in degrees (e.g., 45)
	prob_max = 0.1  # Enter probability threshold for multiples (e.g., 0.1)
	#----------------------------------------------------------------
	
	# Mark's spec'd object variables
	vmodel_dir = None # string of directory containing velocity models
	vmodels = []      # list of string names of velocity model files
	vtables = None    # actual travel time tables in common block
	fplane = []
	s2 = None
	d2 = None
	r2 = None
	
	# Variables HASH keeps internally, for ref and passing to fxns
	ntab = 0     # number of tables loaded
	npol = 0     # number of polarity picks
	dist = None  # distance from source im km
	qazi = None  # azimuth from event to station
	flat = None  # pick station lat
	flon = None  # pick station lon
	felv = None  # pick station elv
	nf2 = None   # number of fm's returned
	nmult = None # number of fm solutions returned
	
	tstamp  = None
	qlat    = None
	qlon    = None
	qdep    = None
	qmag    = None
	icusp   = None
	seh     = None
	sez     = None
	
	# polarity reversals, [-1,1] stub for now
	spol = 1
	
	def __init__(self, **kwargs):
		'''
		Make an empty HASH run object.
		
		Initialize all the arrays needed for a HASH run. They are based
		on the maximum size of the arrays passed to the FORTRAN
		subroutines.
		
		Example
		-------
		>>> h = HashPype()
		'''
		
		directory = os.path.dirname(__file__)
		param_inc_file = os.path.join(directory,'src','param.inc')
		rot_inc_file   = os.path.join(directory,'src','rot.inc')
		
		npick0, nmc0, nmax0 = fortran_include(param_inc_file)
		dang0, ncoor        = fortran_include(rot_inc_file)
		
		# initialize arrays
		self.dang2=max(dang0, self.dang)
		
		# Input arrays
		self.sname     = np.empty(npick0, 'a6', 'F')
		self.scomp     = np.empty(npick0, 'a3', 'F')
		self.snet      = np.empty(npick0, 'a2', 'F')
		self.pickpol   = np.empty(npick0, 'a1', 'F')
		self.pickonset = np.empty(npick0, 'a1', 'F')
		self.p_pol     = np.empty(npick0, int, 'F')
		self.p_qual    = np.empty(npick0, int, 'F')
		self.spol      = np.empty(npick0, int, 'F')
		self.p_azi_mc  = np.empty((npick0,nmc0), float, 'F')
		self.p_the_mc  = np.empty((npick0,nmc0), float, 'F')
		self.index     = np.empty(nmc0, int, 'F')
		self.qdep2     = np.empty(nmc0, float, 'F')
		
		# Output arrays
		self.f1norm  = np.empty((3,nmax0), float, 'F')
		self.f2norm  = np.empty((3,nmax0), float, 'F')
		self.strike2 = np.empty(nmax0, float, 'F')
		self.dip2    = np.empty(nmax0, float, 'F')
		self.rake2   = np.empty(nmax0, float, 'F')
		self.str_avg = np.empty(5, float, 'F')
		self.dip_avg = np.empty(5, float, 'F')
		self.rak_avg = np.empty(5, float, 'F')
		self.var_est = np.empty((2,5), float, 'F')
		self.var_avg = np.empty(5, float, 'F')
		self.mfrac   = np.empty(5, float, 'F')
		self.stdr    = np.empty(5, float, 'F')
		self.prob    = np.empty(5, float, 'F')
		self.qual    = np.empty(5, 'a', 'F')
		
		# Other (added for Python classiness)
		self.dist    = np.empty(npick0, float)
		self.qazi    = np.empty(npick0, float)
		self.flat    = np.empty(npick0, float)
		self.flon    = np.empty(npick0, float)
		self.felv    = np.empty(npick0, float)
		self.esaz    = np.empty(npick0, float)
		
		# Save include vars for other fucntions to access
		self.npick0 = npick0
		self.nmc0   = nmc0
		self.nmax0  = nmax0
		self.dang0  = dang0
		self.ncoor  = ncoor
		
		
		self.fplane = [] # This cancels out inherited one
		
		if kwargs:
			self.__dict__.update(kwargs)
			
		# add pf check for defaults
	
	def __repr__(self):
		'''String saying what for'''
		if self.icusp:
			id = self.icusp
		else:
			id = 'empty'
		return '{0}({1})'.format(self.__class__.__name__, id)
	
	def load_pf(self, pffile='dbhash.pf'):
		'''Update some run settings from a pf file
		
		This could be expanded to control the whole HASH run
		if one really wanted.
		
		Right now these settings are inherited from the class, and
		are not instance attributes.
		'''
		
		from antelope.stock import pfget
		
		pf_settings = pfget(pffile)
		
		# Little hack to do type conversions 
		for key in pf_settings:
			pfi = pf_settings[key]
			if key in ['badfrac','prob_max']:
				pfi = float(pfi)
			elif key in ['npolmin','max_agap','max_pgap','dang','nmc','maxout', 'delmax','cangle']:
				pfi = int(pfi)
			else:
				pass
			self.__setattr__(key, pfi)
		
		if 'vmodel_dir' in pf_settings and 'vmodels' in pf_settings:
			self.vmodels = [os.path.join(self.vmodel_dir, table) for table in self.vmodels]
	
	def load_velocity_models(self, model_list=None):
		'''load velocity model data'''
		# Future -- allow adding on fly, check and append to existing
		#
		# THIS LOADS INTO hashpy.angtable.table (nx,nd,nindex) !!!
		
		# take care of 
		if model_list:
			models = model_list
		else:
			models = self.vmodels
		
		for n,v in enumerate(models):
			self.ntab = mk_table_add(n+1,v)
			self.vtable = angtable.table
	
	def get_phases_from_db(self, dbname, evid=None, orid=None, pf=None):
		'''Input HASH data from Antelope database'''
		
		from aug.contrib import AttribDbptr, open_db_or_string
		
		db, oflag = open_db_or_string(dbname)
		if orid is None:
			dbv = dbprocess(dbv,['dbopen event', 'dbsubset evid == '+str(evid)])
			dbv.record = 0
			orid = dbv.getv('prefor')[0]
		db = dbprocess(db,[ 'dbopen origin', 'dbsubset orid == '+str(orid),
						'dbjoin origerr', 'dbjoin assoc',  'dbjoin arrival',
						'dbjoin affiliation', 'dbjoin site',
						'dbsubset iphase =~ /.*[Pp].*/',
						'dbsubset (ondate <= time)',
						'dbsubset (time <= offdate) || (offdate == -1)']
						)
		
		phases = AttribDbptr(db)
		self.nrecs = len(phases)
		assert len(phases) > 0, "No picks for this ORID: {0}".format(orid)
		ph = phases[0]
		self.tstamp = ph['origin.time']
		self.qlat   = ph['origin.lat']
		self.qlon   = ph['origin.lon']
		self.qdep   = ph['origin.depth']
		self.qmag   = ph['origin.ml']
		self.icusp  = ph['origin.orid']
		self.seh    = ph['origerr.smajax']
		self.sez    = ph['origerr.sdepth']
		
		aspect = np.cos(self.qlat / degrad) # convert using python later.
		
		# The index 'k' is deliberately non-Pythonic to deal with the fortran
		# subroutines which need to be called and the structure of the original HASH code.
		# May be able to update with a rewrite... YMMV
		k = 0
		for ph in phases:
			# load up params
			# in future, could use the acol() method?
			self.sname[k]     = ph.sta
			self.snet[k]      = ph.net
			self.scomp[k]     = ph.chan
			self.pickonset[k] = 'I'
			self.pickpol[k]   = ph.fm
			
			flat,flon,felv = ph['site.lat'],ph['site.lon'],ph['site.elev']
			self.esaz[k] = ph['esaz']
			#print '{0} {1} {2} {3} {4} {5} {6} {7}'.format(k, sname[k], snet[k], scomp[k], pickonset[k], pickpol[k], flat, flon)
			
			# dist @ azi, get from db OR obspy or another python mod (antelope) could do this on WGS84
			dx = (flon - self.qlon) * 111.2 * aspect
			dy = (flat - self.qlat) * 111.2
			dist = np.sqrt(dx**2 + dy**2)
			qazi = 90. - np.arctan2(dy,dx) * degrad
			
			if (qazi < 0.):
				qazi = qazi + 360.
			if (dist > self.delmax):
				continue
			if (self.pickpol[k] in 'CcUu'):
				self.p_pol[k] = 1
			elif (self.pickpol[k] in 'RrDd'):
				self.p_pol[k] = -1
			else:
				continue
			
			# save them for other functions -MCW
			self.dist[k] = dist
			self.qazi[k] = qazi
			self.flat[k] = flat
			self.flon[k] = flon
			self.felv[k] = felv
			
			if (self.pickonset[k] in 'Ii'):
				self.p_qual[k] = 0
			else:
				self.p_qual[k] = 1
			
			# polarity check in original code... doesn't work here
			#self.p_pol[k] = self.p_pol[k] * self.spol
			k += 1
		#npol = k - 1
		self.npol = k # k is zero indexed in THIS loop
		db.close()
		
	def generate_trial_data(self):
		'''Make data for running trials MUST have loaded data and vel mods alreday
		
		Algorithm NOT written by me (From HASH driver script)
		'''
		# choose a new source location and velocity model for each trial
		self.qdep2[0] = self.qdep
		self.index[0] = 1
		for nm in range(1,self.nmc):
			val = ran_norm()
			self.qdep2[nm] = abs(self.qdep + self.sez * val) # randomly perturbed source depth
			self.index[nm] = (nm % self.ntab) + 1  # index used to choose velocity model
			
	def calculate_takeoff_angles(self):
		'''Use HASH fortran subroutine to calulate takeoff angles for each trial'''
		# loop over k picks b/c I broke it out -- NOTE: what does iflag do?
		#
		# find azimuth and takeoff angle for each trial
		for k in range(self.npol):
			for nm in range(self.nmc):
				self.p_azi_mc[k,nm] = self.qazi[k]
				self.p_the_mc[k,nm], iflag = get_tts(self.index[nm],self.dist[k],self.qdep2[nm])
	
	def view_polarity_data(self):
		'''Print out a list of polarity data for interactive runs'''
		for k in range(self.npol):
			print '{0}   {1} {2} {3} {4}'.format(k,self.sname[k],self.p_azi_mc[k,0],self.p_the_mc[k,0],self.p_pol[k])
	
	def check_minimum_polarity(self):
		if self.npol >= self.npolmin:
			return True
		else:
			return False
	
	def check_maximum_gap(self):
		magap,mpgap = get_gap(self.p_azi_mc[:self.npol,0],self.p_the_mc[:self.npol,0],self.npol)
		if ((magap > self.max_agap) or (mpgap > self.max_pgap)):
			return False
		else:
			return True
	
	def calculate_hash_focalmech(self):
		# determine maximum acceptable number misfit polarities
		nmismax = max(int(self.npol * self.badfrac),2)        # nint
		nextra  = max(int(self.npol * self.badfrac * 0.5),2)  # nint
		
		# find the set of acceptable focal mechanisms for all trials
		self.nf2, self.strike2, self.dip2, self.rake2, self.f1norm, self.f2norm = focalmc(self.p_azi_mc, self.p_the_mc, self.p_pol[:self.npol], self.p_qual[:self.npol], self.nmc, self.dang2, self.nmax0, nextra, nmismax, self.npol)
		self.nout2 = min(self.nmax0, self.nf2)  # number mechs returned from sub
		self.nout1 = min(self.maxout, self.nf2) # number mechs to return
		
		# find the probable mechanism from the set of acceptable solutions
		self.nmult, self.str_avg, self.dip_avg, self.rak_avg, self.prob, self.var_est = mech_prob(self.f1norm[:,:self.nout2], self.f2norm[:,:self.nout2], self.cangle, self.prob_max, self.nout2) # nout2
		
		for imult in range(self.nmult):
			self.var_avg[imult] = (self.var_est[0,imult] + self.var_est[1,imult]) / 2.
			#print 'cid = {0} {1}  mech = {2} {3} {4}'.format(self.icusp, imult, self.str_avg[imult], self.dip_avg[imult], self.rak_avg[imult])
			# find misfit for prefered solution
			self.mfrac[imult], self.stdr[imult] = get_misf(self.p_azi_mc[:self.npol,0], self.p_the_mc[:self.npol,0], self.p_pol[:self.npol], self.p_qual[:self.npol], self.str_avg[imult], self.dip_avg[imult], self.rak_avg[imult], self.npol) # npol
			
			# HASH default solution quality rating
			if ((self.prob[imult] > 0.8) and (self.var_avg[imult] < 25) and (self.mfrac[imult] <= 0.15) and (self.stdr[imult] >= 0.5)):
				self.qual[imult]='A'
			elif ((self.prob[imult] > 0.6) and (self.var_avg[imult] <= 35) and (self.mfrac[imult] <= 0.2) and (self.stdr[imult] >= 0.4)):
				self.qual[imult]='B'
			elif ((self.prob[imult] > 0.5) and (self.var_avg[imult] <= 45) and (self.mfrac[imult] <= 0.3) and (self.stdr[imult] >= 0.3)):
				self.qual[imult]='C'
			else:
				self.qual[imult]='D'
				
		# NEED to get other plane here!!! (check Fortran utils...)
		# make this a Dbrecord eventually?
		fline = {'orid': self.icusp, 'str1': self.str_avg[0],
			'dip1': self.dip_avg[0], 'rake1': self.rak_avg[0],
			'str2': self.s2, 'dip2': self.d2, 'rake2': self.r2,
			'algorithm':'HASH', 'mechid': None
			}
		self.fplane.append(fline)
	
	def save_result_to_db(self, dbout=None, solution=0):
		'''Write the preferred HASH solution to the fplane table.'''
		from obspy.imaging.beachball import AuxPlane
		from aug.contrib import AttribDbptr, open_db_or_string
		
		assert len(self.fplane) is not 0, 'No solutions to write!!'
		fp = self.fplane[solution]
		
		d, oflag = open_db_or_string(dbout, perm='r+')
		d = d.lookup(table='fplane')
		d.record = d.addnull()
		d.putv('orid', fp['orid'],
			   'str1', round(fp['str1'],1) ,
			   'dip1', round(fp['dip1'],1) ,
			   'rake1',round(fp['rake1'],1),
			   'algorithm', fp['algorithm'],
			   'mechid', d.nextid('mechid')
			   )
		if True:
			fp['str2'],fp['dip2'],fp['rake2'] = AuxPlane(fp['str1'],fp['dip1'],fp['rake1'])
			d.putv('str2', round(fp['str2'],1) ,
			   'dip2', round(fp['dip2'],1) ,
			   'rake2',round(fp['rake2'],1),
			   )
		d.close()
		
	def read_result_from_db(self, dbin=None, orid=None):
		'''Read in a mechanism from the fplane table'''
		from aug.contrib import open_db_or_string, DbrecordList
		if orid is None:
			orid = self.icusp
		d = open_db_or_string(dbin)
		d = d.lookup(table='fplane')
		d = d.subset('orid == {0}'.format(self.icusp))
		assert d.nrecs() is not 0, 'No solution for this ORID: {0}'.format(orid)
		self.fplane = DbrecordList(d)
		
	def print_solution_line(self, solution=0):
		'''Print the best solution'''
		fp = self.fplane[solution]
		fpline = "ORID:{0} STRIKE:{1} DIP:{2} RAKE:{3}"
		solution = fp['str1'],fp['dip1'],fp['rake1']
		sol = [int(x) for x in solution]
		print fpline.format(fp['orid'],*sol)
	
	def plot_beachball(self, labels=False):
		'''
		test_stereo(self.p_azi_mc[:self.npol,0], self.p_the_mc[:self.npol,0], self.p_pol[:self.npol], sdr=[self.str_avg[0], self.dip_avg[0], self.rak_avg[0]])
		azimuths,takeoffs,polarities,sdr=[]
		'''
		from matplotlib import pyplot as plt
		import mplstereonet
		from obspy.imaging.beachball import AuxPlane
		
		fig = plt.figure()
		ax = fig.add_subplot(111, projection='stereonet')
		
		# pull out variables from mechanism
		azimuths = self.p_azi_mc[:self.npol,0]
		# HASH takeoffs are 0-180 from vertical UP!!
		# Stereonet angles 0-90 inward (dip)
		# Classic FM's are toa from center???
		takeoffs = abs(self.p_the_mc[:self.npol,0] - 90)
		polarities = self.p_pol[:self.npol]
		strike1,dip1,rake1 = self.str_avg[0], self.dip_avg[0], self.rak_avg[0]
		strike2,dip2,rake2 = AuxPlane(strike1, dip1, rake1)
		up = polarities > 0
		dn = polarities < 0
		if False:
			# plot trial planes (nout2) OR avg planes (nmult)
			for n in range(self.nout2):
				s1, d1, r1 = self.strike2[n], self.dip2[n], self.rake2[n]
				s2, d2, r2 = AuxPlane(s1, d1, r1)
				h_rk = ax.plane(s1,d1, color='#999999')
				h_rk = ax.plane(s2,d2,'#888888')
		# plot best fit average plane
		h_rk = ax.plane(strike1, dip1, color='black', linewidth=3)
		h_rk = ax.rake( strike1, dip1, -rake1, 'k^', markersize=8)
		h_rk = ax.plane(strike2, dip2, color='black', linewidth=3)
		# plot station takeoffs
		h_rk = ax.rake(azimuths[up]-90.,takeoffs[up],90, 'wo', markersize=8, markeredgewidth=2, markerfacecolor=None)
		h_rk = ax.rake(azimuths[dn]-90.,takeoffs[dn],90, 'ko', markersize=8, markeredgewidth=2)
		#h_t  = ax.set_title("ORID: {0}".format(self.icusp))
		# hack to throw in station names for temp debugging...
		if labels:
			for i in range(self.npol):
				h_rk = ax.rake(azimuths[i]-90,takeoffs[i]+5,90, marker='$   {0}$'.format(self.sname[i]), color='black',markersize=20)
		# and go.
		plt.show()
	
	def quick_station_map(self):
		'''Quick and dirty station map'''
		import matplotlib.pyplot as plt
		
		fig = plt.figure()
		ax = fig.add_subplot(111)
		ax.plot(self.flon[:foo.npol],self.flat[:self.npol],'o')
		for i in range(self.npol):
			ax.text(self.flon[i], self.flat[i], self.sname[i])
		ax.plot(self.qlon, self.qlat, 'ro')
		plt.show()

