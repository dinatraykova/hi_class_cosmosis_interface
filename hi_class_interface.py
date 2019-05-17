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
from numpy import zeros

#These are pre-defined strings we use as datablock
#section names
cosmo = names.cosmological_parameters
distances = names.distances
cmb_cl = names.cmb_cl

def setup(options):
    #Read options from the ini file which are fixed across
    #the length of the chain
    config = {
        'lmax': options.get_int(option_section,'lmax', default=2500),
        'zmax': options.get_double(option_section,'zmax', default=1.),
        'kmax': options.get_double(option_section,'kmax', default=1.0),
        'debug': options.get_bool(option_section, 'debug', default=False),
        'lensing': options.get_string(option_section, 'lensing', default = 'yes'),
        'expansion_model': options.get_string(option_section, 'expansion_model', default = 'lcdm'),
        'gravity_model':   options.get_string(option_section, 'gravity_model', default = 'propto_omega'),
        'modes':  options.get_string(option_section, 'modes', default = 's'),
        'output': options.get_string(option_section, 'output', default = 'tCl,pCl,lCl,mPk,mTk,vTk'),
        'non_linear': options.get_string(option_section, 'non_linear', default = ' '),
        'format':  options.get_string(option_section, 'format', default = 'camb'),
        #        'sBBN file': options.get_string(option_section, 'sBBN file', default = 'hi_class_devel/bbn/sBBN.dat'),
        #'skip_stability_tests_smg': options.get_string(option_section, 'skip_stability_tests_smg', default = 'no'),
        #'background_verbose': options.get_int(option_section,'background_verbose', default=1),
        #'thermodynamics_verbose': options.get_int(option_section,'thermodynamics_verbose', default=10)
        #'kineticity_safe_smg': options.get_double(option_section,'kineticity_safe_smg', default=1e-5)
            }
    #Create the object that connects to Class
    config['cosmo'] = classy.Class()

    #Return all this config information
    return config

def get_class_inputs(block, config):

    #Get parameters from block and give them the
    #names and form that class expects

    params = {
        'output':        config["output"],
        'modes':         config["modes"],
        'l_max_scalars': config["lmax"],
        'P_k_max_h/Mpc': config["kmax"], #/block[cosmo, 'h0'],
        'lensing':       config["lensing"],
        'non linear':    config["non_linear"],
        'format':        config["format"],
        #        'background_verbose': config["background_verbose"],
        'z_pk': ', '.join(str(z) for z in np.arange(0.0, config['zmax'], 0.01)),
        'n_s':          block[cosmo, 'n_s'],
#        'omega_b':      block[cosmo, 'ombh2'],
#        'omega_cdm':    block[cosmo, 'omch2'],
        'tau_reio':     block[cosmo, 'tau'],
        'T_cmb':        block.get_double(cosmo, 't_cmb', default=2.726),
        'N_ur':         block.get_double(cosmo, 'N_ur', default=3.046),
        'k_pivot':      block.get_double(cosmo, 'k_pivot', default=0.05),
        'YHe':          block.get_double(cosmo, 'yhe', default=0.24),
        }
#    params['sBBN file'] = config['sBBN file']

    if block.has_value(cosmo, 'ombh2') and block.has_value(cosmo, 'omch2'):
        params['omega_b'] = block[cosmo, 'ombh2']
        params['omega_cdm'] = block[cosmo, 'omch2']
    if block.has_value(cosmo, 'omega_b') and block.has_value(cosmo, 'omega_m'):
        ombh2 = block[cosmo, 'omega_b']*block[cosmo, 'h0']*block[cosmo, 'h0']
        ommh2 = block[cosmo, 'omega_m']*block[cosmo, 'h0']*block[cosmo, 'h0']
        params['omega_b'] = ombh2
        params['omega_cdm'] = ommh2 - ombh2 - block[cosmo, 'omnuh2']
    if block.has_value(cosmo, '100*theta_s'):
        params['100*theta_s'] = block[cosmo, '100*theta_s']
    if block.has_value(cosmo, 'h0'):
        params['H0'] = 100*block[cosmo, 'h0']
    if block.has_value(cosmo, 'A_s'):
        params['A_s'] = block[cosmo, 'A_s']
    if block.has_value(cosmo, 'logA'):
        params['ln10^{10}A_s'] = block[cosmo, 'logA']
    if block.has_value(cosmo, 'omega_smg') and block[cosmo,'omega_smg'] < 0.:
        smgs = smg_params(block)
        smgs_exp = smg_exp(block)
        params['expansion_model'] = config['expansion_model']
        params['gravity_model'] =  config['gravity_model']
        params['Omega_Lambda'] = block[cosmo, 'omega_Lambda']
        params['Omega_smg'] = block.get_double(cosmo, 'omega_smg', default = 0.)
        params['Omega_fld'] = block.get_double(cosmo, 'omega_fld', default = 0.)
        params['expansion_smg'] = block.get_string(cosmo, 'expansion_smg', default = smgs_exp)
        params['parameters_smg'] = block.get_string(cosmo, 'parameters_smg', default = smgs)
#        params['skip_stability_tests_smg'] = config['skip_stability_tests_smg']
        params['kineticity_safe_smg'] = block.get_double(cosmo, 'kineticity_safe_smg', default=0.)
    if block.has_value(cosmo, 'N_ur') and block[cosmo,'N_ur'] != 3.046:
        params['N_ncdm'] = block[cosmo, 'N_ncdm']
        if block[cosmo, 'N_ncdm'] == 1:
            if block.has_value(cosmo, 'm_ncdm'):
                params['m_ncdm'] = block[cosmo, 'm_ncdm']
            if block.has_value(cosmo, 'omega_ncdm'):
                params['omega_ncdm'] = block[cosmo, 'omnuh2']
            params['T_ncdm'] = block[cosmo, 'T_ncdm']

        if block[cosmo, 'N_ncdm'] > 1:
            m_nu = []
            o_nu = []
            T_nu = []
            for i in range(1,4):
                if block.has_value(cosmo, 'm_ncdm__%i'%i):
                    m_nu.append(block[cosmo, 'm_ncdm__%i'%i])
                    T_nu.append(block[cosmo, 'T_ncdm__%i'%i])
                if block.has_value(cosmo, 'omnuh2__%i'%i):
                    o_nu.append(block[cosmo, 'omnuh2__%i'%i])
                    T_nu.append(block[cosmo, 'T_ncdm__%i'%i])
            print 'm_nu', len(m_nu)
            print 'omega_nu', len(o_nu)
            if len(m_nu)>0:
                params['m_ncdm'] = ",".join(map(str, m_nu))
                print 'm in'
            if len(o_nu)>0:
                print 'omega in'
                params['omnuh2'] = ",".join(map(str, o_nu))
            params['T_ncdm'] = ",".join(map(str, T_nu))

    return params

def get_class_outputs(block, c, config):
    ##
    ## Derived cosmological parameters
    ##

    block[cosmo, 'sigma_8'] = c.sigma8()
    h0 = block[cosmo, 'h0'] #c.Hubble(0.)/100.
    if block.has_value(cosmo, 'ombh2') and block.has_value(cosmo, 'omch2'):
        block[cosmo, 'omega_m'] = c.Omega_m()
        block[cosmo, 'omega_b'] = c.Omega_b()
    block[cosmo, 'omega_lambda'] = c.Omega0_smg()
    #    block[cosmo, 'omega_nu'] = c.Omega_nu()
    ##
    ##  Matter power spectrum
    ##
    print c.Hubble(0.)/100.
    print h0
    
    #Ranges of the redshift and matter power
    dz = 0.01
    kmin = 1e-5 * h0 #config['kmin']*h0
    kmax = config['kmax']*h0
    nk = 200 #config['nk']

    #Define k,z we want to sample
    z = np.arange(0.0, config["zmax"]+dz, dz)
    k = np.logspace(np.log10(kmin), np.log10(kmax), nk)
    nz = len(z)

    #Extract (interpolate) P(k,z) at the requested
    #sample points.
    #P = np.zeros((nk,nz))
    P = np.zeros((nk, nz)) 
    for i,ki in enumerate(k):
        for j,zj in enumerate(z):
            #P[i,j] = c.pk_lin(ki,zj)
            P[i,j] = c.pk(ki,zj)
            
    block.put_grid("matter_power_lin", "k_h", k/h0,  "z", z, "p_k", P*h0**3)

    ##
    ##Distances and related quantities
    ##

    #save redshifts of samples
    block[distances, 'z'] = z
    block[distances, 'nz'] = nz

    #Save distance samples
    d_l = np.array([c.luminosity_distance(zi) for zi in z])
    block[distances, 'd_l'] = d_l
    d_a = np.array([c.angular_distance(zi) for zi in z])
    block[distances, 'd_a'] = d_a
    block[distances, 'd_m'] = d_a * (1+z)
    block[distances, 'H'] = np.array([c.Hubble(zi) for zi in z])
    block[distances, 'mu'] = 5.*np.log10(d_l + 1e-100) + 25.
    
    #Save some auxiliary related parameters
    block[distances, 'age'] = c.age()
    block[distances, 'rs_zdrag'] = c.rs_drag()
    block[distances, 'a'] = 1./(1.+z)

    ## Growth stuff
    s8 = np.array([c.sigma8_at_z(zi) for zi in z])
    grr = np.array([c.growthrate_at_z(zi) for zi in z])
    
    # Save growth stuff
    block[names.growth_parameters, 'sigma8_at_z'] = s8
    block[names.growth_parameters, 'growthrate_at_z'] = grr


    ##
    ## Now the CMB C_ell
    ##
    if config['lensing'] == 'no':
        c_ell_data =  c.raw_cl()
    if config['lensing'] == 'yes':
        c_ell_data = c.lensed_cl()
    ell = c_ell_data['ell']
    ell = ell[2:]

    #Save the ell range
    block[cmb_cl, "ell"] = ell

    #t_cmb is in K, convert to mu_K, and add ell(ell+1) factor
    tcmb_muk = block[cosmo, 't_cmb'] * 1e6
    f = ell*(ell+1.0) / 2 / np.pi * tcmb_muk**2
    f1 = ell*(ell+1.0) / 2 / np.pi

    #Save each of the four spectra
    for s in ['tt','ee','te','bb','tp']:
        block[cmb_cl, s] = c_ell_data[s][2:] * f
    block[cmb_cl, 'pp'] = c_ell_data['pp'][2:] * f1

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
    for i in range(1,20):
        if block.has_value(cosmo, 'parameters_smg__%i'% i):
            snl.append(block[cosmo, 'parameters_smg__%i'% i])
        else:
            break
    smg = ",".join(map(str, snl))
    return smg

def smg_exp(block):
    snl_exp =[]
    for i in range(1,20):
        if block.has_value(cosmo, 'expansion_smg__%i'% i):
            snl_exp.append(block[cosmo, 'expansion_smg__%i'% i])
        else:
            break
    smg_exp = ",".join(map(str, snl_exp))
    return smg_exp
