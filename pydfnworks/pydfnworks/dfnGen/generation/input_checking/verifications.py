## ====================================================================== ##
##                              Verification                              ##
## ====================================================================== ##

from pydfnworks.dfnGen.generation.input_checking.parameter_checking_general import check_general, check_user_defined
from pydfnworks.dfnGen.generation.input_checking.parameter_checking_fractures import check_fracture_params, cross_check
from pydfnworks.dfnGen.generation.input_checking.parameter_checking_h import check_h


def verify_params(params):
    """ Verify all of the parameters in the input file.

    Parameters
    -------------
        params : dict
            parameter dictionary

    Returns 
    ------------
        None

    Notes
    -------------
        None

    """

    ## Check General Parameters.
    check_general(params)
    # Check Ellipse Parameters
    if params["nFamEll"]['value'] > 0:
        check_fracture_params(params, 'ellipse')
    # ## Check Rectangle Parameters.
    if params["nFamRect"]['value'] > 0:
        check_fracture_params(params, 'rectangle')
    # Cross-Check
    if params["nFamEll"]['value'] > 0 and params["nFamRect"]['value'] > 0:
        cross_check(params)
    check_user_defined(params)
    # Check h (Requires information from fracture checking)
    check_h(params)
