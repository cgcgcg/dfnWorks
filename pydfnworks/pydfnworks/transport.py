import os
import sys
import shutil
from time import time
import subprocess

def dfn_trans(self):
    """Primary driver for dfnTrans. 

    Parameters
    ---------
        self : object
            DFN Class 
   
    Returns
    --------
        None
    """
    print('='*80)
    print("\ndfnTrans Starting\n")
    print('='*80)
    tic=time()
    self.copy_dfn_trans_files()
    self.check_dfn_trans_run_files()
    self.run_dfn_trans()
    delta_time = time() - tic
    self.dump_time('Process: dfnTrans', delta_time)   
    print('='*80)
    print("\ndfnTrans Complete\n")
    print("Time Required for dfnTrans: %0.2f Seconds\n"%delta_time)
    print('='*80)

def copy_dfn_trans_files(self):
    """Creates symlink to dfnTrans Execuateble and copies input files for dfnTrans into working directory

    Parameters
    ---------
        self : object
            DFN Class
 
    Returns
    --------
        None
    """

    print("Attempting to Copy %s\n"%self.dfnTrans_file) 
    try:
        shutil.copy(self.dfnTrans_file, os.path.abspath(os.getcwd())) 
    except OSError:
        print("--> Problem copying %s file"%self.local_dfnTrans_file)
        print("--> Trying to delete and recopy") 
        os.remove(self.local_dfnTrans_file)
        shutil.copy(self.dfnTrans_file, os.path.abspath(os.getcwd())) 
    except:
        print("--> ERROR: Problem copying %s file"%self.dfnTrans_file)
        sys.exit("Unable to replace. Exiting Program")

def run_dfn_trans(self):
    """ Execute dfnTrans

    Parameters
    ---------
        self : object
            DFN Class  
 
    Returns
    --------
    None
    """
    tic = time()
    failure = subprocess.call(os.environ['DFNTRANS_EXE']+' '+self.local_dfnTrans_file, shell = True)
    self.dump_time("Function: DFNTrans ",time()-tic)
    if failure != 0:
        sys.exit("--> ERROR: dfnTrans did not complete\n")

def create_dfn_trans_links(self, path = '../'):
    """ Create symlinks to files required to run dfnTrans that are in another directory. 

    Parameters
    ---------
        self : object 
            DFN Class
        path : string 
            Absolute path to primary directory. 
   
    Returns
    --------
    None

    Notes
    -------
    Typically, the path is DFN.path, which is set by the command line argument -path

    """
    files = ['params.txt', 'allboundaries.zone', 'full_mesh.stor',
        'poly_info.dat', 'full_mesh.inp', 'aperture.dat']
    if self.flow_solver == 'PFLOTRAN':
        files.append('cellinfo.dat')
        files.append('darcyvel.dat')
        files.append('full_mesh_vol_area.uge')
    if self.flow_solver == 'FEHM':
        files.append('tri_frac.fin')
 
    for f in files:
        try:
            os.symlink(path+f, f)
        except:
            print("--> Error Creating link for %s"%f)

def check_dfn_trans_run_files(self):
    """ Ensures that all files required for dfnTrans run are in the current directory
 
    Parameters
    ---------
        self : object 
            DFN Class
   
    Returns
    --------
        None

    Notes
    -------
        None
    """
    cwd = os.getcwd()
    print("\nChecking that all files required for dfnTrans are in the current directory")
    print("--> Current Working Directory: %s"%cwd)
    print("--> dfnTrans is running from: %s"%self.local_dfnTrans_file)

    files = {"param:": None ,"poly:":None, "inp:": None, "stor:": None, "boundary:": None, "aperture_file:": None}
    if self.flow_solver == "PFLOTRAN":
        files["PFLOTRAN_vel:"]=None
        files["PFLOTRAN_cell:"]=None
        files["PFLOTRAN_uge:"]=None
    if self.flow_solver == "FEHM":
        files["FEHM_fin:"]=None

    keys = files.keys()
    with open(self.local_dfnTrans_file) as fp:
        for line in fp.readlines():
               for key in keys:
                    if key in line:
                        if files[key] == None:
                            files[key] = line.split()[-1]

    for key in keys:
        if not os.path.isfile(files[key]) or os.stat(files[key]).st_size == 0:
            sys.exit("ERROR!!!!!\nRequired file %s is either empty of not in the current directory.\nPlease check required files\nExiting Program"%files[key])
    print("--> All files required for dfnTrans have been found in current directory\n\n")
