#!/usr/bin/env python
u"""
tsregress.py
Written by Tyler Sutterley (07/2020)

Fits a synthetic signal to the data over the time period by least-squares
    or weighted least-squares
Default fits constant, trend, annual sin and cos, semi-annual sin and cos
Fit significance derivations are based on Burnham and Anderson (2002)
    Model Selection and Multimodel Inference

CALLING SEQUENCE:
    tsbeta = tsregress(t_in, d_in, ORDER=1, CYCLES=[0.5,1.0], CONF=0.95)

INPUTS:
    t_in: input time array
    d_in: input data array

OUTPUTS:
    beta: regressed coefficients array
    error: regression fit error for each coefficient for an input deviation
        STDEV: standard deviation of output error
        CONF: confidence interval of output error
    std_err: standard error for each coefficient
    R2: coefficient of determination (r**2).
        Proportion of variability accounted by the model
    R2Adj: adjusted r**2. adjusts the r**2 for the number of terms in the model
    MSE: mean square error
    WSSE: Weighted sum of squares error
    NRMSE: normalized root mean square error
    AIC: Akaike information criterion (Second-Order, AICc)
    BIC: Bayesian information criterion (Schwarz criterion)
    model: modeled timeseries
    simple: modeled timeseries without oscillating components
    residual: model residual
    DOF: degrees of freedom
    N: number of terms used in fit
    cov_mat: covariance matrix

OPTIONS:
    DATA_ERR: data precision
        single value if equal
        array if unequal for weighted least squares
    WEIGHT: Set if measurement errors for use in weighted least squares
    RELATIVE: relative period
    ORDER: maximum polynomial order in fit (0=constant, 1=linear, 2=quadratic)
    CYCLES: list of cyclical terms (0.5=semi-annual, 1=annual)
    STDEV: standard deviation of output error
    CONF: confidence interval of output error
    AICc: use second order AIC

PYTHON DEPENDENCIES:
    numpy: Scientific Computing Tools For Python (https://numpy.org)
    scipy: Scientific Tools for Python (https://docs.scipy.org/doc/)

UPDATE HISTORY:
    Updated 07/2020: added function docstrings
    Updated 10/2019: changing Y/N flags to True/False
    Updated 12/2018: put transpose of design matrix within FIT_TYPE if statement
    Updated 08/2018: import packages before function definition
    Updated 10/2017: output a seasonal model (will be 0 if no oscillating terms)
    Updated 09/2017: using rcond=-1 in numpy least-squares algorithms
    Updated 03/2017: added a catch for zero error in weighted least-squares
    Updated 08/2015: changed sys.exit to raise ValueError
    Updated 09/2014: made AICc option for second order AIC
        previously was default with no option for standard AIC
    Updated 07/2014: output the covariance matrix Hinv
        import scipy.stats and scipy.special
    Updated 06/2014: changed message to sys.exit
        new output for number of terms
    Updated 04/2014: added parameter RELATIVE for the relative time
    Updated 02/2014: minor update to if statements.  output simple regression
    Updated 10/2013:
        Added calculation for AICc (corrected for small sample size)
        Added output DOF (degrees of freedom, nu)
    Updated 09/2013: updated weighted least-squares and added AIC, BIC and
        LOGLIK options for parameter evaluation
        Fixed case with known standard deviations
        Changed Weight flag to Y/N
        Minor change: P_cons, P_lin and P_quad changed to P_x0, P_x1 and P_x2
    Updated 07/2013: added output for the modelled time-series
    Updated 05/2013: converted to Python
    Updated 02/2013: added in case for equal data error
        and made associated edits.. added option WEIGHT
    Updated 10/2012: added in additional FIT_TYPES that do not have a trend
        added option for the Schwarz Criterion for model selection
    Updated 08/2012: NUMBER OF CHANGES
        added option for changing the confidence interval or adding a standard
            deviation of the error
        added option for GRACE errors in spatial domain
        changed 'std' to data_err for measurement errors as I added the std_dev
            out of the error
    Updated 06/2012: added options for MSE and NRMSE.  Fixed rsq_adj
    Updated 06/2012: changed design matrix creation to 'FIT_TYPE'
        wrote in r_square capability to calcuating goodness of fit compared to others
        fixed error analysis for weighted least-squares case
    Updated 05/2012: added option to change half-width of smoothing
    Updated 03/2012:
        combined polynomial and harmonic regression functions (renamed tsregress.pro)
         smoothing procedure now 13-month ad-hoc filter as described in Velicogna (2009)
            fits annual/semi-annual and trend to a 13-month time series
            takes constant and trend terms, and uses as the smoothed time series
        measurement for the central month (month 7 of the 13 month window)
             original 13-month moving average program option in program tssmooth.pro
    Updated 01/2012: added std weighting for a error weighted least-squares
    Written 10/2011
"""
import numpy as np
import scipy.stats
import scipy.special

def tsregress(t_in, d_in, ORDER=1, CYCLES=[0.5,1.0], DATA_ERR=0,
    WEIGHT=False, RELATIVE=-1, STDEV=0, CONF=0, AICc=True):
    """
    Solves sea level equation with option to include polar motion feedback

    Arguments
    ---------
    t_in: input time array
    d_in: input data array

    Keyword arguments
    -----------------
    DATA_ERR: data precision
        single value if equal
        array if unequal for weighted least squares
    WEIGHT: Set if measurement errors for use in weighted least squares
    RELATIVE: relative period
    ORDER: maximum polynomial order in fit
    CYCLES: list of cyclical terms
    STDEV: standard deviation of output error
    CONF: confidence interval of output error
    AICc: use second order AIC

    Returns
    -------
    beta: regressed coefficients array
    error: regression fit error for each coefficient for an input deviation
        STDEV: standard deviation of output error
        CONF: confidence interval of output error
    std_err: standard error for each coefficient
    R2: coefficient of determination (r**2)
    R2Adj: r**2 adjusted for the number of terms in the model
    MSE: mean square error
    WSSE: Weighted sum of squares error
    NRMSE: normalized root mean square error
    AIC: Akaike information criterion
    BIC: Bayesian information criterion
    model: modeled timeseries
    simple: modeled timeseries without oscillating components
    residual: model residual
    DOF: degrees of freedom
    N: number of terms used in fit
    cov_mat: covariance matrix
    """

    #-- remove singleton dimensions
    t_in = np.squeeze(t_in)
    d_in = np.squeeze(d_in)
    nmax = len(t_in)
    t_rel = t_in[0:nmax].mean() if (RELATIVE == -1) else RELATIVE

    #-- create design matrix based on polynomial order and harmonics
    DMAT = []
    #-- add polynomial orders (0=constant, 1=linear, 2=quadratic)
    for o in range(ORDER+1):
        DMAT.append((t_in-t_rel)**o)
    #-- add cyclical terms (0.5=semi-annual, 1=annual)
    for c in CYCLES:
        DMAT.append(np.sin(2.0*np.pi*t_in/np.float(c)))
        DMAT.append(np.cos(2.0*np.pi*t_in/np.float(c)))
    #-- take the transpose of the design matrix
    DMAT = np.transpose(DMAT)

    #-- Calculating Least-Squares Coefficients
    if WEIGHT:
        #-- Weighted Least-Squares fitting
        if (np.ndim(DATA_ERR) == 0):
            raise ValueError('Input DATA_ERR for Weighted Least-Squares')
        #-- check if any error values are 0 (prevent infinite weights)
        if np.count_nonzero(DATA_ERR == 0.0):
            #-- change to minimum floating point value
            DATA_ERR[DATA_ERR == 0.0] = np.finfo(np.float).eps
        #--- Weight Precision
        wi = np.squeeze(DATA_ERR**(-2))
        #-- If uncorrelated weights are the diagonal
        W = np.diag(wi)
        #-- Least-Squares fitting
        #-- Temporary Matrix: Inv(X'.W.X)
        TM1 = np.linalg.inv(np.dot(np.transpose(DMAT),np.dot(W,DMAT)))
        #-- Temporary Matrix: (X'.W.Y)
        TM2 = np.dot(np.transpose(DMAT),np.dot(W,d_in))
        #-- Least Squares Solutions: Inv(X'.W.X).(X'.W.Y)
        beta_mat = np.dot(TM1,TM2)
    else:#-- Standard Least-Squares fitting (the [0] denotes coefficients output)
        beta_mat = np.linalg.lstsq(DMAT,d_in,rcond=-1)[0]
        #-- Weights are equal
        wi = 1.0

    #-- number of terms in least-squares solution
    n_terms = len(beta_mat)
    #-- modelled time-series
    mod = np.dot(DMAT,beta_mat)
    #-- residual
    res = d_in[0:nmax] - np.dot(DMAT,beta_mat)
    #-- Fitted Values without (and with) climate oscillations
    simple = np.dot(DMAT[:,0:(ORDER+1)],beta_mat[0:(ORDER+1)])
    season = mod - simple

    #-- nu = Degrees of Freedom
    nu = nmax - n_terms

    #-- calculating R^2 values
    #-- SStotal = sum((Y-mean(Y))**2)
    SStotal = np.dot(np.transpose(d_in[0:nmax] - np.mean(d_in[0:nmax])),
        (d_in[0:nmax] - np.mean(d_in[0:nmax])))
    #-- SSerror = sum((Y-X*B)**2)
    SSerror = np.dot(np.transpose(d_in[0:nmax] - np.dot(DMAT,beta_mat)),
        (d_in[0:nmax] - np.dot(DMAT,beta_mat)))
    #-- R**2 term = 1- SSerror/SStotal
    rsquare = 1.0 - (SSerror/SStotal)
    #-- Adjusted R**2 term: weighted by degrees of freedom
    rsq_adj = 1.0 - (SSerror/SStotal)*np.float((nmax-1.0)/nu)
    #-- Fit Criterion
    #-- number of parameters including the intercept and the variance
    K = np.float(n_terms + 1)
    #-- Log-Likelihood with weights (if unweighted, weight portions == 0)
    #-- log(L) = -0.5*n*log(sigma^2) - 0.5*n*log(2*pi) - 0.5*n
    #log_lik = -0.5*nmax*(np.log(2.0 * np.pi) + 1.0 + np.log(np.sum((res**2)/nmax)))
    log_lik = 0.5*(np.sum(np.log(wi)) - nmax*(np.log(2.0 * np.pi) + 1.0 -
        np.log(nmax) + np.log(np.sum(wi * (res**2)))))

    #-- Aikaike's Information Criterion
    AIC = -2.0*log_lik + 2.0*K
    if AICc:
        #-- Second-Order AIC correcting for small sample sizes (restricted)
        #-- Burnham and Anderson (2002) advocate use of AICc where
        #-- ratio num/K is small
        #-- A small ratio is defined in the definition at approximately < 40
        AIC += (2.0*K*(K+1.0))/(nmax - K - 1.0)

    #-- Bayesian Information Criterion (Schwarz Criterion)
    BIC = -2.0*log_lik + np.log(nmax)*K

    #--- Error Analysis
    if WEIGHT:
        #-- WEIGHTED LEAST-SQUARES CASE (unequal error)
        #-- Covariance Matrix
        Hinv = np.linalg.inv(np.dot(np.transpose(DMAT),np.dot(W,DMAT)))
        #-- Normal Equations
        NORMEQ = np.dot(Hinv,np.transpose(np.dot(W,DMAT)))
        beta_err = np.zeros((n_terms))
        #-- Propagating RMS errors
        for i in range(0,n_terms):
            beta_err[i] = np.sqrt(np.sum((NORMEQ[i,:]*DATA_ERR)**2))
        #-- Weighted sum of squares Error
        WSSE = np.dot(np.transpose(wi*(d_in[0:nmax] - np.dot(DMAT,beta_mat))),
            wi*(d_in[0:nmax] - np.dot(DMAT,beta_mat)))/np.float(nu)

        return {'beta':beta_mat, 'error':beta_err, 'R2':rsquare,
            'R2Adj':rsq_adj, 'WSSE':WSSE, 'AIC':AIC, 'BIC':BIC,
            'LOGLIK':log_lik, 'model':mod, 'residual':res, 'simple':simple,
            'season':season, 'N':n_terms, 'DOF':nu, 'cov_mat':Hinv}

    elif ((not WEIGHT) and (DATA_ERR != 0)):
        #-- LEAST-SQUARES CASE WITH KNOWN AND EQUAL ERROR
        P_err = DATA_ERR*np.ones((nmax))
        Hinv = np.linalg.inv(np.dot(np.transpose(DMAT),DMAT))
        #-- Normal Equations
        NORMEQ = np.dot(Hinv,np.transpose(DMAT))
        beta_err = np.zeros((n_terms))
        for i in range(0,n_terms):
            beta_err[i] = np.sqrt(np.sum((NORMEQ[i,:]*P_err)**2))
        #-- Mean square error
        MSE = np.dot(np.transpose(d_in[0:nmax] - np.dot(DMAT,beta_mat)),
            (d_in[0:nmax] - np.dot(DMAT,beta_mat)))/np.float(nu)

        return {'beta':beta_mat, 'error':beta_err, 'R2':rsquare,
            'R2Adj':rsq_adj, 'MSE':MSE, 'AIC':AIC, 'BIC':BIC,
            'LOGLIK':log_lik, 'model':mod, 'residual':res, 'simple':simple,
            'season':season,'N':n_terms, 'DOF':nu, 'cov_mat':Hinv}
    else:
        #-- STANDARD LEAST-SQUARES CASE
        #-- Regression with Errors with Unknown Standard Deviations
        #-- MSE = (1/nu)*sum((Y-X*B)**2)
        #-- Mean square error
        MSE = np.dot(np.transpose(d_in[0:nmax] - np.dot(DMAT,beta_mat)),
            (d_in[0:nmax] - np.dot(DMAT,beta_mat)))/np.float(nu)
        #-- Root mean square error
        RMSE = np.sqrt(MSE)
        #-- Normalized root mean square error
        NRMSE = RMSE/(np.max(d_in[0:nmax])-np.min(d_in[0:nmax]))
        #-- Covariance Matrix
        #-- Multiplying the design matrix by itself
        Hinv = np.linalg.inv(np.dot(np.transpose(DMAT),DMAT))
        #-- Taking the diagonal components of the cov matrix
        hdiag = np.diag(Hinv)
        #-- set either the standard deviation or the confidence interval
        if (STDEV != 0):
            #-- Setting the standard deviation of the output error
            alpha = 1.0 - scipy.special.erf(STDEV/np.sqrt(2.0))
        elif (CONF != 0):
            #-- Setting the confidence interval of the output error
            alpha = 1.0 - CONF
        else:
            #-- Default is 95% confidence interval
            alpha = 1.0 - (0.95)
        #-- Student T-Distribution with D.O.F. nu
        #-- t.ppf parallels tinv in matlab
        tstar = scipy.stats.t.ppf(1.0-(alpha/2.0),nu)
        #-- beta_err is the error for each coefficient
        #-- beta_err = t(nu,1-alpha/2)*standard error
        st_err = np.sqrt(MSE*hdiag)
        beta_err = tstar*st_err

        return {'beta':beta_mat, 'error':beta_err, 'std_err':st_err, 'R2':rsquare,
            'R2Adj':rsq_adj, 'MSE':MSE, 'NRMSE':NRMSE, 'AIC':AIC, 'BIC':BIC,
            'LOGLIK':log_lik, 'model':mod, 'residual':res, 'simple':simple,
            'season':season, 'N':n_terms, 'DOF':nu, 'cov_mat':Hinv}
