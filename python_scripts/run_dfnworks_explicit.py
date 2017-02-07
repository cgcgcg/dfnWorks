import os, sys
#sys.path.append("/home/jhyman/dfnworks/dfnworks-main/python_scripts/") 
sys.path.append("/home/jhyman/dfnworks/dfnworks-main/python_scripts/modules") 
from modules import dfnworks 
import generator as generator
import flow as flow
import gen_input as gen_input
import gen_output as gen_output
import helper as helper
import mesh_helper as mesh_helper
import transport as transport


from time import time

def define_paths():
	# Set Environment Variables
	os.environ['PETSC_DIR']='/home/satkarra/src/petsc-git/petsc-3.7-release'
	os.environ['PETSC_ARCH']='/Ubuntu-14.04-nodebug'

	os.environ['PFLOTRAN_DIR']='/home/satkarra/src/pflotran-dev-pt-testing'
	os.environ['DFNWORKS_PATH'] = '/home/jhyman/dfnworks/dfnworks-main/'
	
	os.environ['DFNGENC_PATH']='/home/jhyman/dfnworks/DFNGen/DFNC++Version'
	os.environ['DFNTRANS_PATH']= os.environ['DFNWORKS_PATH'] +'ParticleTracking/'
	os.environ['input_files']='/home/jhyman/dfnworks/input_files'

	# Executables	
	os.environ['python_dfn'] = '/n/swdev/packages/Ubuntu-14.04-x86_64/anaconda-python/2.4.1/bin/python'
#	os.environ['lagrit_dfn'] = '/n/swdev/LAGRIT/bin/lagrit_ulin3.2'
	os.environ['lagrit_dfn'] = '/n/swdev/mesh_tools/lagrit/install-Ubuntu-14.04-x86_64/3.2.0/release/gcc-4.8.4/bin/lagrit'

	os.environ['connect_test'] = os.environ['DFNWORKS_PATH']+'/DFN_Mesh_Connectivity_Test/ConnectivityTest'
	os.environ['correct_uge_PATH'] = os.environ['DFNWORKS_PATH']+'/C_uge_correct/correct_uge' 

lanl_statement = '''
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
~~~~~~~~~~~~~~~~~~ Program: DFNWorks  V2.0 ~~~~~~~~~~~~~~~~~~~~~~~~
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This program was prepared at Los Alamos National Laboratory (LANL),
Earth and Environmental Sciences Division, Computational Earth
Science Group (EES-16), Subsurface Flow and Transport Team.
All rights in the program are reserved by the DOE and LANL.
Permission is granted to the public to copy and use this software
without charge, provided that this Notice and any statement of
authorship are reproduced on all copies. Neither the U.S. Government
nor LANS makes any warranty, express or implied, or assumes
any liability or responsibility for the use of this software.

Contact Information : dfnworks@lanl.gov
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

LA-CC-17-027

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Copyright (2017).  Los Alamos National Security, LLC. 
This material was produced under U.S. Government contract DE-AC52-06NA25396 for 
Los Alamos National Laboratory (LANL), which is operated by Los Alamos National 
Security, LLC for the U.S. Department of Energy. The U.S. Government has rights 
to use, reproduce, and distribute this software.  NEITHER THE GOVERNMENT NOR LOS
 ALAMOS NATIONAL SECURITY, LLC MAKES ANY WARRANTY, EXPRESS OR IMPLIED, OR 
ASSUMES ANY LIABILITY FOR THE USE OF THIS SOFTWARE.  If software is modified to 
produce derivative works, such modified software should be clearly marked, so as
 not to confuse it with the version available from LANL.

Additionally, this program is free software; you can redistribute it and/or 
modify it under the terms of the GNU General Public License as published by the 
Free Software Foundation; either version 2 of the License, or (at your option) 
any later version. Accordingly, this program is distributed in the hope that it 
will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of 
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public 
License for more details.
 
Additionally, redistribution and use in source and binary forms, with or 
without modification, are permitted provided that the following conditions are 
met:
1.       Redistributions of source code must retain the above copyright notice, 
this list of conditions and the following disclaimer.

2.      Redistributions in binary form must reproduce the above copyright 
notice, this list of conditions and the following disclaimer in the 
documentation and/or other materials provided with the distribution.

3.      Neither the name of Los Alamos National Security, LLC, Los Alamos 
National Laboratory, LANL, the U.S. Government, nor the names of its 
contributors may be used to endorse or promote products derived from this 
software without specific prior written permission.
 
THIS SOFTWARE IS PROVIDED BY LOS ALAMOS NATIONAL SECURITY, LLC AND 
CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT 
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A 
PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL LOS ALAMOS NATIONAL 
SECURITY, LLC OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, 
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, 
PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR 
BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER 
IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE 
POSSIBILITY OF SUCH DAMAGE.
'''


print ('='*80)
print lanl_statement
print ('='*80)
os.system("date")
define_paths()
main_time = time()
DFN = dfnworks.create_dfn()


#dfn.dfnGen()
generator.make_working_directory(DFN._jobname)
gen_input.check_input(DFN._dfnGen_file, DFN._jobname)
generator.create_network(DFN._local_dfnGen_file, DFN._jobname)
print DFN._output_file
gen_output.output_report(DFN._output_file)
mesh_helper.mesh_network(DFN._jobname, helper.get_num_frac(), DFN._ncpu)

os.chdir(DFN._jobname)

#dfn.dfnFlow()

DFN.lagrit2pflotran()
dfnflow.pflotran()
dfnflow.parse_pflotran_vtk()       
dfnflow.pflotran_cleanup()

#dfn.dfnTrans()
transport.copy_dfnTrans_files(DFN._dfnTrans_file)
transport.run_dfntrans(DFN._local_dfnTrans_file)

main_elapsed = time() - main_time
timing = 'Time Required: %0.2f Minutes'%(main_elapsed/60.0)
print timing
helper.dump_time(dfn._jobname, dfn._jobname,main_elapsed) 
#dfn.print_run_time()	
print("*"*80)
print(dfn._jobname+' complete')
print("Thank you for using dfnWorks")
print("*"*80)
