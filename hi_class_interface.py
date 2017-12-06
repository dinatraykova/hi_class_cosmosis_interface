import os
from cosmosis.datablock import names, option_section
import sys
import traceback

#add class directory to the path
dirname = os.path.split(__file__)[0]
#enable debugging from the same directory
if not dirname.strip(): dirname='.'
install_dir = dirname+"/hi_class_devel/classy_install/lib/python2.7/site-packages/"
sys.path.insert(0, install_dir)

import classy
import numpy as np

#These are pre-defined strings we use as datablock
#section names
cosmo = names.cosmological_parameters
distances = names.distances
cmb_cl = names.cmb_cl
#configpars.read('test/test_vals_p.ini')

def setup(options):
    #Read options from the ini file which are fixed across
    #the length of the chain
    config = {
        'lmax': options.get_int(option_section,'lmax', default=2000),
        'zmax': options.get_double(option_section,'zmax', default=4.0),
        'kmax': options.get_double(option_section,'kmax', default=50.0),
        'debug': options.get_bool(option_section, 'debug', default=False),
        'lensing': options.get_string(option_section, 'lensing', default = 'no'),
        'expansion_model': options.get_string(option_section, 'expansion_model', default = 'lcdm'),
        'gravity_model':   options.get_string(option_section, 'gravity_model', default = 'propto_omega'),
        #'modes':  options.get_string(option_section, 'modes', default = 's, t'),
        #'output': options.get_string(option_section, 'output', default = 'tCl,pCl,lCl,mPk'),
            }
    #Create the object that connects to Class
    config['cosmo'] = classy.Class()

    #Return all this config information
    return config

def get_class_inputs(block, config):

    #Get parameters from block and give them the
    #names and form that class expects

    params = {
        'output': 'tCl,pCl,lCl,mPk',#       confit["output"],
        'modes':  's, t', #       config["modes"],
        'l_max_scalars': config["lmax"],
        'P_k_max_h/Mpc': config["kmax"],
        'lensing':       config["lensing"],
        'z_pk': ', '.join(str(z) for z in np.arange(0.0, config['zmax'], 0.01)),
        'n_s':          block[cosmo, 'n_s'],
        'H0':           100*block[cosmo, 'h0'],
        'omega_b':      block[cosmo, 'ombh2'],
        'omega_cdm':    block[cosmo, 'omch2'],
        'tau_reio':     block[cosmo, 'tau'],
        'T_cmb':        block.get_double(cosmo, 't_cmb', default=2.726),
        'N_eff':        block.get_double(cosmo, 'massless_nu', default=3.046),
        'r':            block.get_double(cosmo, 'r_t', default=0.),
        }
    if block.has_value(cosmo, 'A_s'):
        params['A_s'] = block[cosmo, 'A_s']
    if block.has_value(cosmo, 'ln10^{10}A_s'):
        params['ln10^{10}A_s'] = block[cosmo, 'ln10^{10}A_s']
    if block.has_value(cosmo, 'omega_smg') and block[cosmo,'omega_smg'] < 0.:
        smgs = smg_params(block)
        params['expansion_model'] = config['expansion_model']
        params['gravity_model'] =  config['gravity_model']
        params['Omega_Lambda'] = block[cosmo, 'omega_Lambda']
        params['Omega_smg'] = block.get_double(cosmo, 'omega_smg', default = 0.)
        params['Omega_fld'] = block.get_double(cosmo, 'omega_sfld', default = 0.)
        params['expansion_smg'] = block.get_double(cosmo, 'expansion_smg', default = 0.5)
        params['parameters_smg'] = block.get_string(cosmo, 'parameters_smg', default = smgs)

    return params

def get_class_outputs(block, c, config):
    ##
    ## Derived cosmological parameters
    ##

    block[cosmo, 'sigma_8'] = c.sigma8()
    h0 = block[cosmo, 'h0']

    ##
    ##  Matter power spectrum
    ##

    #Ranges of the redshift and matter power
    dz = 0.01
    kmin = 1e-4
    kmax = config['kmax']*h0
    nk = 100

    #Define k,z we want to sample
    z = np.arange(0.0, config["zmax"]+dz, dz)
    k = np.logspace(np.log10(kmin), np.log10(kmax), nk)
    nz = len(z)

    #Extract (interpolate) P(k,z) at the requested
    #sample points.
    P = np.zeros((nk, nz))
    for i,ki in enumerate(k):
        for j,zj in enumerate(z):
            P[i,j] = c.pk(ki,zj)

    #Save matter power as a grid
    block.put_grid("matter_power_lin", "k_h", k/h0, "z", z, "p_k", P*h0**3)

    ##
    ##Distances and related quantities
    ##

    #save redshifts of samples
    block[distances, 'z'] = z
    block[distances, 'nz'] = nz

    #Save distance samples
    block[distances, 'd_l'] = np.array([c.luminosity_distance(zi) for zi in z])
    d_a = np.array([c.angular_distance(zi) for zi in z])
    block[distances, 'd_a'] = d_a
    block[distances, 'd_m'] = d_a * (1+z)
    block[distances, 'h'] = np.array([c.Hubble(zi) for zi in z])

    #Save some auxiliary related parameters
    block[distances, 'age'] = c.age()
    block[distances, 'rs_zdrag'] = c.rs_drag()

    ##
    ## Now the CMB C_ell
    ##
    c_ell_data =  c.raw_cl()
    ell = c_ell_data['ell']
    ell = ell[2:]

    #Save the ell range
    block[cmb_cl, "ell"] = ell

    #t_cmb is in K, convert to mu_K, and add ell(ell+1) factor
    tcmb_muk = block[cosmo, 't_cmb'] * 1e6
    f = ell*(ell+1.0) / 2 / np.pi * tcmb_muk**2

    #Save each of the four spectra
    for s in ['tt','ee','te','bb']:
        block[cmb_cl, s] = c_ell_data[s][2:] * f

def execute(block, config):
    c = config['cosmo']

   # try:
        # Set input parameters
    params = get_class_inputs(block, config)
    c.set(params)
    try:
        # Run calculations
        c.compute()

        # Extract outputs
        get_class_outputs(block, c, config)
    except classy.CosmoError as error:
        if config['debug']:
            sys.stderr.write("Error in class. You set debug=T so here is more debug info:\n")
            traceback.print_exc(file=sys.stderr)
        else:
            sys.stderr.write("Error in class. Set debug=T for info: {}\n".format(error))
        return 1
    finally:
        #Reset for re-use next time
        c.struct_cleanup()
    return 0

def cleanup(config):
    config['cosmo'].empty()

def smg_params(block):
    snl =[]
    for i in range(1,100):
        if block.has_value(cosmo, 'parameters_smg__%i'% i):
            snl.append(block[cosmo, 'parameters_smg__%i'% i])
        else:
            break
    smg = ",".join(map(str, snl))
    return smg
