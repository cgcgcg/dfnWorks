"""
.. module:: lagrit_scripts.py
   :synopsis: create lagrit scripts for meshing dfn using LaGriT 
.. moduleauthor:: Jeffrey Hyman <jhyman@lanl.gov>

"""
import os
import glob
from shutil import copy, rmtree, move
from numpy import genfromtxt, sqrt, cos, arcsin
import subprocess

def edit_intersection_files(num_poly, fracture_list, path):
    """ If pruning a DFN, this function walks through the intersection files
    and removes references to files that are not included in the 
    fractures that will remain in the network.
 
    Parameters
    ---------
        num_poly : int 
            Number of Fractures in the original DFN
        fracture_list :list of int
            List of fractures to keep in the DFN

    Returns
    -------
        None

    Notes
    -----
    1. Currently running in serial, but it could be parallelized
    2. Assumes the pruning directory is not the original directory

    """
    # Make list of connectivity.dat
    connectivity = []  
    fp = open("connectivity.dat", "r")
    for i in range(num_poly):
        tmp = []
        line = fp.readline()
        line = line.split()
        for frac in line:
            tmp.append(int(frac))
        connectivity.append(tmp)
    fp.close()

    fractures_to_remove = list(set(range(1,num_poly+ 1)) - set(fracture_list))
    cwd = os.getcwd()
    os.chdir('intersections')
    # clean up directory 
    #fl_list = glob.glob("*prune.inp")
    #for fl in fl_list: 
    #   os.remove(fl)    

    print("Editing Intersection Files")    
    for i in fracture_list:
        filename = 'intersections_%d.inp'%i
        print('--> Working on: %s'%filename)
        intersecting_fractures = connectivity[i-1]
        pull_list = list(set(intersecting_fractures).intersection(set(fractures_to_remove)))
        if len(pull_list) > 0:
            # Create Symlink to origignal intersection file
            os.symlink(path+'intersections/'+filename,filename)
            # Create LaGriT script to remove intersections with fractures not in prune_file
            lagrit_script = 'read / %s / mo1'%filename
            lagrit_script += '''
pset / pset2remove / attribute / b_a / 1,0,0 / eq / %d
    '''%pull_list[0]    
            for j in pull_list[1:]:
                lagrit_script += '''
pset / prune / attribute / b_a / 1,0,0 / eq / %d
pset / pset2remove / union / pset2remove, prune
#rmpoint / pset, get, prune
pset / prune / delete
     '''%j
            lagrit_script += '''
rmpoint / pset, get, pset2remove 
rmpoint / compress
    
cmo / modatt / mo1 / imt / ioflag / l
cmo / modatt / mo1 / itp / ioflag / l
cmo / modatt / mo1 / isn / ioflag / l
cmo / modatt / mo1 / icr / ioflag / l
    
cmo / status / brief
dump / intersections_%d_prune.inp / mo1
finish

'''%i
            
            lagrit_filename = 'prune_intersection.lgi'
            f = open(lagrit_filename, 'w')
            f.write(lagrit_script)
            f.flush()
            f.close()
            subprocess.call(os.environ['LAGRIT_EXE'] + \
                '< prune_intersection.lgi > out_%d.txt'%i,shell=True)
            os.remove(filename)
            move("intersections_%d_prune.inp"%i, "intersections_%d.inp"%i)
        else:
            try:
                copy(path+'intersections/'+filename,filename)
            except:
                pass
    os.chdir(cwd)


def create_parameter_mlgi_file(fracture_list, h, slope=2.0, refine_dist = 0.5):
    """Create parameteri.mlgi files used in running LaGriT Scripts
    
    Parameters
    ----------
        num_poly : int
            Number of polygons
        h : float 
            Meshing length scale
        slope : float 
            Slope of coarsening function, default = 2
        refine_dist : float 
            Distance used in coarsening function, default = 0.5

    Returns
    -------
        None

    Notes
    -----
    Set slope = 0 for uniform mesh
    """
    
    print("\nCreating parameter*.mlgi files")
    try:
        os.mkdir('parameters')
    except OSError:
        rmtree('parameters')    
        os.mkdir('parameters')

    # Extrude and Translate computation
    # Parameters, delta: buffer zone, amount of h/2 we remove from around line
    # h_extrude height of rectangle extruded from line of intersection
    # r_radius: Upper bound on radius of circumscribed circle around rectangle
    # h_trans : amount needed to translate to create delta buffer
    # It's  just a little trig! 
    delta = 0.75
    h_extrude = 0.5*h # upper limit on spacing of points on interssction line
    h_radius = sqrt((0.5*h_extrude)**2 + (0.5*h_extrude)**2)
    h_trans = -0.5*h_extrude + h_radius*cos(arcsin(delta))

    #Go through the list and write out parameter file for each polygon
    #to be an input file for LaGriT
    data = genfromtxt('poly_info.dat')
    for index, i in enumerate(fracture_list): 
        # using i - 1 do to python indexing from 0
        # fracture index starts at 1
        frac_id = str(int(data[i-1,0]))
        long_name = str(int(data[i-1,0]))      
        theta = data[i-1,2]    
        x1 = data[i-1,3]    
        y1 = data[i-1,4]    
        z1 = data[i-1,5]    
        x2 = data[i-1,6]    
        y2 = data[i-1,7]    
        z2 = data[i-1,8]    
        family = data[i-1,1]

        fparameter_name = 'parameters/parameters_' + long_name + '.mlgi'
        f = open(fparameter_name, 'w')
        f.write('define / ID / ' + str(index+1) + '\n')
        f.write('define / OUTFILE_GMV / mesh_' + long_name + '.gmv\n')
        f.write('define / OUTFILE_AVS / mesh_' + long_name + '.inp\n')
        f.write('define / OUTFILE_LG / mesh_' + long_name + '.lg\n')
        f.write('define / POLY_FILE / poly_' + long_name + '.inp\n')
        f.write('define / QUAD_FILE / tmp_quad_' + frac_id + '.inp\n')
        f.write('define / EXCAVATE_FILE / tmp_excavate_' + frac_id + '.inp\n')
        f.write('define / PRE_FINAL_FILE / tmp_pre_final_'+frac_id + '.inp\n')
        f.write('define / PRE_FINAL_MASSAGE / tmp_pre_final_massage_' + frac_id +'.gmv\n')
        
        f.write('define / H_SCALE / %e \n'%h)
        f.write('define / H_EPS / %e \n'%(h*10**-7))
        f.write('define / H_SCALE2 / %e \n'%(1.5*h))

        f.write('define / H_EXTRUDE / %e \n'%(h_extrude))
        f.write('define / H_TRANS / %e \n'%(h_trans))

        f.write('define / H_PRIME / %e \n'%(0.8*h))
        f.write('define / H_PRIME2 / %e \n'%(0.3*h))
        
        f.write('define / H_SCALE3 / %e \n'%(3.0*h))
        f.write('define / H_SCALE8 / %e \n'%(8.0*h))
        f.write('define / H_SCALE16 / %e \n'%(16.0*h))
        f.write('define / H_SCALE32 / %e \n'%(32.0*h))
        f.write('define / H_SCALE64 / %e \n' %(64.0*h))

        f.write('define / PERTURB8 / %e \n'%(8*0.05*h))
        f.write('define / PERTURB16 / %e \n'%(16*0.05*h))
        f.write('define / PERTURB32 / %e \n'%(32*0.05*h))
        f.write('define / PERTURB64 / %e \n'%(64*0.05*h))

        f.write('define / PARAM_A / %f \n'%slope)    
        f.write('define / PARAM_B / %f \n'%(h*(1-slope*refine_dist)))    

        f.write('define / PARAM_A2 / %f \n'%(0.5*slope))    
        f.write('define / PARAM_B2 / %f \n'%(h*(1 - 0.5*slope*refine_dist)))    
        
        f.write('define / THETA  / %0.12f \n'%theta)
        f.write('define / X1 /  %0.12f \n'%x1)
        f.write('define / Y1 / %0.12f \n'%y1)
        f.write('define / Z1 / %0.12f \n'%z1)
        f.write('define / X2 / %0.12f \n'%x2)
        f.write('define / Y2 / %0.12f \n'%y2)
        f.write('define / Z2 / %0.12f \n'%z2)
        f.write('define / FAMILY / %d \n'%family)
        f.write('finish \n')
        f.flush()
        f.close()
    print("Creating parameter*.mlgi files: Complete\n")

def create_lagrit_scripts(visual_mode, ncpu, refine_factor=1, production_mode=True): 
    """ Creates LaGriT script to be mesh each polygon
    
    Parameters
    ---------- 
        visual_mode : bool 
            Sets if running if visual mode or in full dump
        ncpu : int
            Number of cpus
        refine_factor : int 
            Number of times original polygon gets refined 
        production_mode : bool
            Determines if clean up of work files occurs on the fly. 

    Returns
    -------
        None

    Notes
    -----
    1. Only ncpu of these files are created
    2. Symbolic links are used to rotate through fractures on different CPUs 
    """

    #Section 2 : Creates LaGriT script to be run for each polygon
    #Switches to control the LaGriT output
    #Network visualization mode True ouputs the triangulated mesh
    #for each fracture without any refinement. The goal is to visualize
    #the network structure instead of outputing the appropriate values
    #for computation

    print("Writing LaGriT Control Files")
    #Go through the list and write out parameter file for each polygon
    #to be an input file for LaGriT

    lagrit_input = """infile %s 
#LaGriT Script
# Name the input files that contain the polygons 
# and lines of intersection. 

define / POLY_FILE / %s 
define / LINE_FILE / %s 
define / OUTPUT_INTER_ID_SSINT / id_tri_node_CPU%d.list

# Define parameters such as: 
# length scale to refine triangular mesh  
# purturbation distance to break symmetry of refined mesh# 

# Read in line and polygon files  
read / POLY_FILE / mo_poly_work
""" 
    if not visual_mode:
        lagrit_input += """
read / LINE_FILE / mo_line_work 
"""
    #
    # START: Refine the point distribution
    #
    if(refine_factor > 1):
        lagrit_input += 'extrude / mo_quad_work / mo_line_work / const / H_SCALE8 / volume / 0. 0. 1.  \n'
        if (refine_factor == 2):
            lagrit_input += 'refine/constant/imt1/linear/element/1 0 0 /-1.,0.,0./inclusive amr 2  \n'

        if (refine_factor == 4):
            lagrit_input += 'refine/constant/imt1/linear/element/1 0 0 /-1.,0.,0./inclusive amr 2  \n'
            lagrit_input += 'refine/constant/imt1/linear/element/1 0 0 /-1.,0.,0./inclusive amr 2  \n'
            
        if (refine_factor == 8):
            lagrit_input +='refine/constant/imt1/linear/element/1 0 0 /-1.,0.,0./inclusive amr 2  \n'
            lagrit_input +='refine/constant/imt1/linear/element/1 0 0 /-1.,0.,0./inclusive amr 2  \n'
            lagrit_input +='refine/constant/imt1/linear/element/1 0 0 /-1.,0.,0./inclusive amr 2  \n'
            
        lagrit_input += """ 
grid2grid / tree_to_fe / mo_quad_work / mo_quad_work  
extract/surfmesh/1,0,0/mo_ext_work/mo_quad_work/external 
compute / distance_field / mo_ext_work / mo_line_work / dfield 
pset / pdel_work / attribute / dfield / 1 0 0 / H_SCALE3 / gt 
rmpoint / pset get pdel_work / inclusive 
rmpoint / compress  

cmo / delete / mo_quad_work 
cmo / delete / mo_line_work
cmo / move / mo_line_work / mo_ext_work 
rmpoint / compress  
"""    
        # END: Refine the point distribution
        #
    lagrit_input += """
## Triangulate Fracture without point addition 
cmo / create / mo_pts / / / triplane 
copypts / mo_pts / mo_poly_work 
cmo / select / mo_pts 
triangulate / counterclockwise 

cmo / setatt / mo_pts / imt / 1 0 0 / ID 
cmo / setatt / mo_pts / itetclr / 1 0 0 / ID 
resetpts / itp 
cmo / delete / mo_poly_work 
cmo / select / mo_pts 

"""
    if not visual_mode:
        lagrit_input += """
# Creates a Coarse Mesh and then refines it using the distance field from intersections
massage / H_SCALE64 / H_EPS  / H_EPS
recon 0; smooth;recon 0;smooth;recon 0;smooth;recon 0
resetpts / itp
pset / p_move / attribute / itp / 1 0 0 / 0 / eq
perturb / pset get p_move / PERTURB64 PERTURB64 0.0
recon 0; smooth;recon 0;smooth;recon 0;smooth;recon 0
smooth;recon 0;smooth;recon 0;smooth;recon 0

massage / H_SCALE32 / H_EPS / H_EPS
resetpts / itp
pset / p_move / attribute / itp / 1 0 0 / 0 / eq
perturb / pset get p_move / PERTURB32 PERTURB32 0.0
recon 0; smooth;recon 0;smooth;recon 0;smooth;recon 0
smooth;recon 0;smooth;recon 0;smooth;recon 0

massage / H_SCALE16 / H_EPS  / H_EPS
resetpts / itp
pset / p_move / attribute / itp / 1 0 0 / 0 / eq
perturb / pset get p_move / PERTURB16 PERTURB16 0.0
recon 0; smooth;recon 0;smooth;recon 0;smooth;recon 0
smooth;recon 0;smooth;recon 0;smooth;recon 0

massage / H_SCALE8 / H_EPS / H_EPS
resetpts / itp
pset / p_move / attribute / itp / 1 0 0 / 0 / eq
perturb / pset get p_move / PERTURB8 PERTURB8 0.0
recon 0; smooth;recon 0;smooth;recon 0;smooth;recon 0
smooth;recon 0;smooth;recon 0;smooth;recon 0

cmo/addatt/ mo_pts /x_four/vdouble/scalar/nnodes 
cmo/addatt/ mo_pts /fac_n/vdouble/scalar/nnodes 

# Massage points based on linear function down to h_prime
massage2/user_function2.lgi/H_PRIME/fac_n/1.e-5/1.e-5/1 0 0/strictmergelength 

assign///maxiter_sm/1 
smooth;recon 0;smooth;recon 0;smooth;recon 0

assign///maxiter_sm/10

massage2/user_function.lgi/H_PRIME/fac_n/1.e-5/1.e-5/1 0 0/strictmergelength 
cmo / DELATT / mo_pts / rf_field_name 

# Extrude and excavate the lines of intersection
cmo / select / mo_line_work 

extrude / mo_quad / mo_line_work / const / H_EXTRUDE / volume / 0. 0. 1. 
"""
        if not production_mode:
            lagrit_input += """
dump / avs / QUAD_FILE / mo_quad 
cmo / delete / mo_quad 
read / QUAD_FILE / mo_quad 
"""
        else:
            lagrit_input += 'cmo / select / mo_quad \n'
        
        lagrit_input += """
# Translate extruced lines of intersectino down slightly to excavate 
# nearby points from the mesh 

trans / 1 0 0 / 0. 0. 0. / 0. 0. H_TRANS
hextotet / 2 / mo_tri / mo_quad 
cmo / delete / mo_quad 
addmesh / excavate / mo_excavate / mo_pts / mo_tri

##### DEBUG #####
# If meshing fails, uncomment and rerun the script to get tmp meshes, 
# which are otherwise not output 
#dump / avs2 / tmp_tri.inp / mo_tri / 1 1 1 0
#dump / avs2 / tmp_pts.inp / mo_pts / 1 1 1 0
#dump / avs2 / tmp_excavate.inp / mo_excavate / 1 1 1 0
#finish
#####
 
cmo / delete / mo_tri 
cmo / delete / mo_pts 

# recompute dfield 
cmo / create / mo_final / / / triplane 
copypts / mo_final / mo_excavate  
compute / distance_field / mo_final / mo_line_work / dfield 
cmo / printatt / mo_final / dfield / minmax 
pset / pdel / attribute dfield / 1,0,0 / lt H_PRIME2 
rmpoint / pset,get,pdel / inclusive  
rmpoint / compress  

copypts / mo_final / mo_line_work  

cmo / select / mo_final 
cmo / setatt / mo_final / imt / 1 0 0 / ID 
cmo / setatt / mo_final / itp / 1 0 0 / 0 
cmo / setatt / mo_final / itetclr / 1 0 0 / ID 
# cmo / printatt / mo_final / -xyz- / minmax 
trans/ 1 0 0 / zero / xyz 
cmo / setatt / mo_final / zic / 1 0 0 / 0.0 
cmo / printatt / mo_final / -xyz- / minmax 
connect 

trans / 1 0 0 / original / xyz 
cmo / printatt / mo_final / -xyz- / minmax 

#cmo / delete / mo_line_work 
cmo / delete / mo_excavate
cmo / select / mo_final 
resetpts / itp 

"""
        if not production_mode:
            lagrit_input += 'dump / gmv / PRE_FINAL_MASSAGE / mo_final \n'
        
        lagrit_input += """
## Massage Mesh Away from Intersection 
pset / pref / attribute / dfield / 1,0,0 / lt / H_EPS 
pset / pregion / attribute / dfield / 1,0,0 / gt / H_SCALE2 
pset / pboundary / attribute / itp / 1,0,0 / eq / 10 
pset / psmooth / not / pregion pref pboundary 
#massage / H_SCALE / 1.e-5 / 1.e-5 / pset get pref / & 
#nosmooth / strictmergelenth

assign///maxiter_sm/1 

smooth / position / esug / pset get psmooth; recon 0; 
smooth / position / esug / pset get psmooth; recon 0; 
smooth / position / esug / pset get psmooth; recon 0; 

assign///maxiter_sm/10
###########################################
# nodes for Intersection / Mesh Connectivity Check 
cmo / copy / mo_final_check / mo_final
#
# Define variables that are hard wired for this part of the workflow
define / MO_TRI_MESH_SSINT / mo_tri_tmp_subset
define / MO_LINE_MESH_SSINT / mo_line_tmp_subset
define / ATT_ID_INTERSECTION_SSINT / b_a
define / ATT_ID_SOURCE_SSINT / id_node_global
define / ATT_ID_SINK_SSINT / id_node_tri
#
# Before subsetting the mesh reate a node attribute containing the integer global node number
cmo / set_id / mo_final_check / node / ATT_ID_SOURCE_SSINT
#
# Subset the triangle mesh based on b_a node attribute ne 0
#
cmo / select / mo_final_check
pset / pkeep / attribute / ATT_ID_INTERSECTION_SSINT / 1 0 0 / ne / 0
pset / pall / seq / 1 0 0
pset / pdel / not pall pkeep
rmpoint / pset get pdel / exclusive
rmpoint / compress
#
# Create an integer node attribute in the line mesh to interpolate the triangle node number onto
# 
cmo / addatt / mo_line_work / ATT_ID_SINK_SSINT / vint / scalar / nnodes
interpolate / voronoi / mo_line_work ATT_ID_SINK_SSINT / 1 0 0 / &
                        mo_final_check  ATT_ID_SOURCE_SSINT
#
# Supress AVS output of a bunch of node attributes
#
cmo / modatt / mo_line_work / imt / ioflag / l
cmo / modatt / mo_line_work / itp / ioflag / l
cmo / modatt / mo_line_work / isn / ioflag / l
cmo / modatt / mo_line_work / icr / ioflag / l
cmo / modatt / mo_line_work / a_b / ioflag / l
cmo / modatt / mo_line_work / b_a / ioflag / l
#
# Output list of intersection nodes with the corrosponding node id number from the triangle mesh

dump / avs2 / OUTPUT_INTER_ID_SSINT / mo_line_work / 0 0 2 0
cmo / delete / mo_line_work

cmo / delete / mo_final_check
# nodes for intersection check over

cmo / select / mo_final 

##### DEBUG
# write out mesh before it is rotate back into its final location
# Useful to compare with meshing workflow if something crashes
#dump / avs2 / tmp_mesh_2D.inp / mo_final / 1 1 1 0 
##### DEBUG
# Rotate facture back into original plane 
rotateln / 1 0 0 / nocopy / X1, Y1, Z1 / X2, Y2, Z2 / THETA / 0.,0.,0.,/  
cmo / printatt / mo_final / -xyz- / minmax 
recon 1 

resetpts / itp 

cmo / addatt / mo_final / unit_area_normal / xyz / vnorm 
cmo / addatt / mo_final / scalar / xnorm ynorm znorm / vnorm 
cmo / DELATT / mo_final / vnorm 

"""
        # Clean up before output to GMV/AVS
        if production_mode:
            lagrit_input += """
cmo / DELATT / mo_final / x_four 
cmo / DELATT / mo_final / fac_n 
cmo / DELATT / mo_final / rf_field_name 
cmo / DELATT / mo_final / xnorm 
cmo / DELATT / mo_final / ynorm 
cmo / DELATT / mo_final / znorm 
cmo / DELATT / mo_final / a_b 
cmo / setatt / mo_final / ipolydat / no 
cmo / modatt / mo_final / icr1 / ioflag / l 
cmo / modatt / mo_final / isn1 / ioflag / l 
    
# Create Family element set
cmo / addatt / mo_final / family_id / vint / scalar / nelements 
cmo / setatt / mo_final / family_id / 1 0 0 / FAMILY
    
"""
        lagrit_input += """
dump / OUTFILE_AVS / mo_final
dump / lagrit / OUTFILE_LG / mo_final
""" 
    else:
        lagrit_input += """
cmo / setatt / mo_pts / imt / 1 0 0 / ID 
cmo / setatt / mo_pts / itetclr / 1 0 0 / ID 
resetpts / itp 

cmo / setatt / mo_line_work / imt / 1 0 0 / ID 
cmo / setatt / mo_line_work / itetclr / 1 0 0 / ID

addmesh / merge / mo_final / mo_pts / mo_line_work 
cmo / delete / mo_pts 
cmo / delete / mo_line_work 
    
# Create Family element set
cmo / addatt / mo_final / family_id / vint / scalar / nelements 
cmo / setatt / mo_final / family_id / 1 0 0 / FAMILY

cmo / select / mo_final 
# Rotate 
rotateln / 1 0 0 / nocopy / X1, Y1, Z1 / X2, Y2, Z2 / THETA / 0.,0.,0.,/ 

cmo / printatt / mo_final / -xyz- / minmax 
cmo / modatt / mo_final / icr1 / ioflag / l 
cmo / modatt / mo_final / isn1 / ioflag / l
dump / lagrit / OUTFILE_LG / mo_final 
"""

    lagrit_input += """
quality 
cmo / delete / mo_final 
cmo / status / brief 
finish
"""

    # Create a different Run file for each CPU
    for i in range(1,ncpu+1):
        file_name = 'mesh_poly_CPU%d.lgi'%i
        f = open(file_name, 'w')
        #Name of parameter Input File
        fparameter_name = 'parameters_CPU%d.mlgi'%i 
        fintersection_name = 'intersections_CPU%d.inp'%i
        fpoly_name = 'poly_CPU%d.inp'%i
        parameters = (fparameter_name, fpoly_name, fintersection_name, i)
        f.write(lagrit_input%parameters)
        f.flush()
        f.close()
    print('--> Writing LaGriT Control Files: Complete')

def create_user_functions():
    """ Create user_function.lgi files for meshing
    
    Parameters
    ----------
        None
    
    Returns
    -------
        None
    
    Notes
    -----
    These functions are called within LaGriT. It controls the mesh resolution using slope and refine_dist

    """


    # user_function.lgi useing PARAM_A and PARAM_B for slope and intercept
    lagrit_input = """
cmo/DELATT/mo_pts/dfield
compute / distance_field / mo_pts / mo_line_work / dfield
math/multiply/mo_pts/x_four/1,0,0/mo_pts/dfield/PARAM_A/
math/add/mo_pts/x_four/1,0,0/mo_pts/x_four/PARAM_B/
cmo/copyatt/mo_pts/mo_pts/fac_n/x_four
finish
"""
    f = open('user_function.lgi', 'w')
    f.write(lagrit_input)
    f.close()

    # user_function2.lgi uses PARAM_A2 and PARAM_B2 for slope and intercept
    lagrit_input = """
cmo/DELATT/mo_pts/dfield
compute / distance_field / mo_pts / mo_line_work / dfield
math/multiply/mo_pts/x_four/1,0,0/mo_pts/dfield/PARAM_A2/
math/add/mo_pts/x_four/1,0,0/mo_pts/x_four/PARAM_B2/
cmo/copyatt/mo_pts/mo_pts/fac_n/x_four
finish
"""
    f = open('user_function2.lgi', 'w')
    f.write(lagrit_input)
    f.close()



def create_merge_poly_files(ncpu, num_poly, fracture_list, h, visual_mode, domain, flow_solver):
    """ Creates a LaGriT script that reads in each fracture mesh, appends it to the main mesh, and then deletes that mesh object. Then duplicate points are removed from the main mesh using EPS_FILTER.  The points are compressed, and then written to file.

    Parameters
    ----------
        ncpu : int 
            Number of Processors used for meshing
        fracture_list : list of int
            List of fracture numbers in the DFN
        h : float 
            Meshing length scale
        visual_mode : bool
            If True, reduced_mesh.inp will be output. If False, full_mesh.inp is output
        domain : dict
            Dictionary of x,y,z domain size
        flow_solver : string
            Name of target flow solver (Changes output files)

    Returns
    -------
        endis : list of int
            Number of last fracture merged into a partition of the DFN

    Notes
    -----
    1. Fracture mesh objects are read into different part_*.lg files. This allows for merging of the mesh to be performed in batches.  
    """

    print("--> Writing : merge_poly.lgi")
    part_size = num_poly/ncpu + 1 ###v number of fractures in each part
    endis = []
    ii = 0
    for i in fracture_list[:-1]:    
        ii += 1    
        if ii == part_size:
            endis.append(i)
            ii = 0    
    endis.append(fracture_list[-1])

    lagrit_input = """
# Change to read LaGriT
read / lagrit /  %s / mo_%d / binary
cmo / move / mo_%d / mo_final 
define / MO_NAME_FRAC / mo_%d
"""
    if not visual_mode:
        lagrit_input += """
cmo / addatt / MO_NAME_FRAC / volume / evol_one
math / sum / MO_NAME_FRAC / evol_sum / 1 0 0 / MO_NAME_FRAC / evol_one 
""" 
    lagrit_input += """
addmesh / merge / cmo_tmp / cmo_tmp / mo_%d
cmo / delete / mo_%d
"""
    lagrit_input_2 = '#Writing out merged fractures\n' 
    if not visual_mode:
        lagrit_input_2 += """
mo / addatt/ cmo_tmp / volume / evol_all
math / sum / cmo_tmp / evol_sum / 1 0 0 / cmo_tmp / evol_all """
    lagrit_input_2 += """ 
cmo select cmo_tmp
dump lagrit part%d.lg cmo_tmp
finish \n 
"""

    j = 0 # Counter for cpus 
    fout = 'merge_poly_part_1.lgi'
    f = open(fout, 'w')
    for i in fracture_list: 
        tmp = 'mesh_'+str(i) +'.lg'
        f.write(lagrit_input%(tmp,i,i,i,i,i))
        # if i is the last fracture in the cpu set
        # move to the next cpu set    
        if i == endis[j]:
            f.write(lagrit_input_2%(j+1))
            f.flush()
            f.close()
            j += 1
            fout = 'merge_poly_part_'+str(j+1)+'.lgi'
            f = open(fout,'w') 

    f.flush() 
    f.close() 
    os.remove(fout) ###

    ## Write LaGriT file for merge parts of the mesh and remove duplicate points 

    lagrit_input  = """
read / lagrit / part%d.lg / junk / binary
addmesh / merge / mo_all / mo_all / cmo_tmp 
cmo / delete / cmo_tmp 
    """
    f = open('merge_rmpts.lgi','w')
    for j in range(1,len(endis)+1):
        f.write(lagrit_input%(j))

    # Append meshes complete
    if not visual_mode: 
        lagrit_input = """
# Appending the meshes complete 
# LaGriT Code to remove duplicates and output the mesh
cmo / select / mo_all 
#recon 1
define / EPS / %e 
define / EPS_FILTER / %e 
pset / pinter / attribute / dfield / 1,0,0 / lt / EPS 
#cmo / addatt / mo_all / inter / vint / scalar / nnodes 
#cmo / setatt / mo_all / inter / 1 0 0 / 0 
#cmo / setatt / mo_all / inter / pset, get, pinter / 1 

filterkd / pset get pinter / EPS_FILTER / nocheck
pset / pinter / delete

rmpoint / compress 
# SORT can affect a_b attribute
sort / mo_all / index / ascending / ikey / imt xic yic zic 
reorder / mo_all / ikey 
cmo / DELATT / mo_all / ikey
"""%(h*10**-5, h*10**-3)
        lagrit_input += """ 
resetpts / itp 
boundary_components 
#dump / full_mesh.gmv / mo_all
dump / full_mesh.inp / mo_all
dump / lagrit / full_mesh.lg / mo_all
"""
        if flow_solver == "PFLOTRAN":
            print("\nDumping output for %s"%flow_solver)
            lagrit_input += """
dump / pflotran / full_mesh / mo_all / nofilter_zero
dump / stor / full_mesh / mo_all / ascii
    """
        elif flow_solver == "FEHM":
            print("\nDumping output for %s"%flow_solver)
            lagrit_input += """
dump / stor / full_mesh / mo_all / ascii
dump / coord / full_mesh / mo_all 
# matid start at 1, but we need them to start at 7 for FEHM due to zone files
# So we do a little addition
math / add / mo_all / imt1 / 1,0,0 / mo_all / imt1 / 6
dump / zone_imt / full_mesh / mo_all
# and then we subtract 6 back 
math / subtract / mo_all / imt1 / 1,0,0 / mo_all / imt1 / 6
"""
        else:
            print("WARNING!!!!!!!\nUnkown flow solver selection: %s"%flow_solver)
        lagrit_input += """ 
# Dump out Material ID Dat file
cmo / modatt / mo_all / isn / ioflag / l
cmo / modatt / mo_all / x_four / ioflag / l
cmo / modatt / mo_all / fac_n / ioflag / l
cmo / modatt / mo_all / dfield / ioflag / l
cmo / modatt / mo_all / rf_field / ioflag / l
cmo / modatt / mo_all / a_b / ioflag / l
cmo / modatt / mo_all / b_a / ioflag / l
cmo / modatt / mo_all / xnorm / ioflag / l
cmo / modatt / mo_all / ynorm / ioflag / l
cmo / modatt / mo_all / znorm / ioflag / l
cmo / modatt / mo_all / evol_one / ioflag / l
cmo / modatt / mo_all / evol_all / ioflag / l
cmo / modatt / mo_all / numbnd / ioflag / l
cmo / modatt / mo_all / id_numb / ioflag / l
cmo / modatt / mo_all / evol_all / ioflag / l
cmo / modatt / mo_all / itp / ioflag / l
cmo / modatt / mo_all / icr / ioflag / l
cmo / modatt / mo_all / meshid / ioflag / l
cmo / modatt / mo_all / id_n_1 / ioflag / l
cmo / modatt / mo_all / id_n_2 / ioflag / l
cmo / modatt / mo_all / pt_gtg / ioflag / l
cmo / modatt / mo_all / pt_gtg / ioflag / l
# Dump out Material ID Dat file
dump / avs2 / materialid.dat / mo_all / 0 0 2 0

cmo / modatt / mo_all / imt1 / ioflag / l
cmo / modatt / mo_all / family_id / ioflag / l
cmo / modatt / mo_all / evol_onen / ioflag / l
# Dump mesh with no attributes for viz
dump / full_mesh_viz.inp / mo_all

# Dump out zone files
define / XMAX / %e 
define / XMIN / %e 
define / YMAX / %e 
define / YMIN / %e 
define / ZMAX / %e 
define / ZMIN / %e 

define / ZONE / 1
define / FOUT / boundary_top
pset / top / attribute / zic / 1,0,0/ gt / ZMAX
pset / top / zone / FOUT/ ascii / ZONE

define / ZONE / 2
define / FOUT / boundary_bottom
pset / bottom / attribute / zic / 1,0,0/ lt / ZMIN
pset / bottom / zone / FOUT/ ascii / ZONE

define / ZONE / 3
define / FOUT / boundary_left_w
pset / left_w / attribute/ xic/ 1,0,0 /lt / XMIN
pset / left_w / zone / FOUT/ ascii / ZONE

define / ZONE / 4
define / FOUT / boundary_front_n
pset / front_n / attribute/ yic / 1,0,0 / gt / YMAX
pset / front_n / zone / FOUT/ ascii / ZONE

define / ZONE / 5
define / FOUT / boundary_right_e
pset / right_e / attribute/ xic / 1,0,0/ gt / XMAX
pset / right_e / zone / FOUT/ ascii / ZONE

define / ZONE / 6
define / FOUT / boundary_back_s
pset / back_s / attribute/ yic/ 1,0,0 / lt / YMIN
pset / back_s / zone / FOUT/ ascii / ZONE

"""
        eps = h*10**-3
        parameters = (0.5*domain['x'] - eps, -0.5*domain['x'] + eps, \
            0.5*domain['y'] - eps, -0.5*domain['y'] + eps, \
            0.5*domain['z'] - eps, -0.5*domain['z'] + eps)

        lagrit_input=lagrit_input%parameters

    else:
        lagrit_input = """
cmo / modatt / mo_all / icr1 / ioflag / l
cmo / modatt / mo_all / isn1 / ioflag / l
cmo / modatt / mo_all / itp1 / ioflag / l
#dump / reduced_mesh.gmv / mo_all 
dump / reduced_mesh.inp / mo_all
"""
    lagrit_input += """
quality 
finish
"""
    f.write(lagrit_input)
    f.flush()
    f.close()

    return len(endis)

def define_zones():
    """Processes zone files for particle tracking. All zone files are combined into allboundaries.zone 
    
    Parameters
    ----------
        None

    Returns
    -------
        None

    Notes
    -----
        None 
    """    
   
    fall=open("allboundaries.zone","w")
    #copy all but last 2 lines of boundary_top.zone in allboundaries.zone
    fzone=open("boundary_top.zone","r")
    lines=fzone.readlines()
    lines=lines[:-2]
    fzone.close() 
    fall.writelines(lines)
    #copy all but frist and last 2 lines of boundary_bottom.zone in allboundaries.zone
    files=['bottom','left_w','front_n','right_e']
    for f in files:
            fzone=open("boundary_%s.zone"%f,"r")
            lines=fzone.readlines()
            lines=lines[1:-2]
            fzone.close() 
            fall.writelines(lines)
    fzone=open("boundary_back_s.zone","r")
    lines=fzone.readlines()
    lines=lines[1:]
    fzone.close() 
    fall.writelines(lines)
    fall.close()
    # copies boundary zone files for PFLOTRAN 
    # This can be deleted once we clean up the flow 
    move('boundary_bottom.zone','pboundary_bottom.zone')
    move('boundary_left_w.zone','pboundary_left_w.zone')
    move('boundary_front_n.zone','pboundary_front_n.zone')
    move('boundary_right_e.zone','pboundary_right_e.zone')
    move('boundary_back_s.zone','pboundary_back_s.zone')
    move('boundary_top.zone','pboundary_top.zone')
 
    ## Remove Left over zone files
    #os.remove('boundary_bottom.zone')
    #os.remove('boundary_top.zone')
    #os.remove('boundary_left_w.zone')
    #os.remove('boundary_right_e.zone')
    #os.remove('boundary_front_n.zone')
    #os.remove('boundary_back_s.zone')

