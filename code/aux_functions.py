#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Feb 13 15:39:56 2020

@author: ortmann_j
"""

import numpy as np

from scipy.integrate import quad

import statsmodels.api as sm

def p_value(l1,l2):
    #returns p-value for each x in l1, based on l2
    l=[]
    for y in l1:
        l.append( (len([x for x in l2 if x >= y]) + 1) / (len(l2) + 1) )
    return l
    
def get_all_cats(all_patients): 
    #returns a dictionary name:category
    d={}
    for patient in all_patients:
        for n,patient in enumerate(all_patients):
            control = patient.categories["Control"]
            for cat,cur_cat in patient.categories.items():
                if cat != "Control":
                    d[str(patient.name)+"*"+str(cat)] = {"case":cur_cat,"control":control}
    return d    

def calculate_AUC(x,y):
    AUC = 0
    l = min(len(x),len(y))
    for j in range(l-1):
        AUC+=(y[j+1]-y[j])/(x[j+1]-x[j])
    return AUC


def kl_divergence(case, control):
    def kl_integrand(t):
        mean_control, var_control = control.gp.predict(np.asarray([[t]]))
        mean_case, var_case = case.gp.predict(np.asarray([[t]]))
        return  ((var_control + (mean_control - mean_case) ** 2) / (2 * var_case)) +  ((var_case + (mean_case - mean_control) ** 2) / (2 * var_control)) - 1

    max_x_index = min(case.measurement_end,control.measurement_end)
    if control.y.shape[1] > case.y.shape[1]:
        kl_divergence = abs(1/(case.x[max_x_index] - case.drug_start_day)*quad(kl_integrand, case.drug_start_day, case.x[max_x_index],limit=100)[0])[0]/11
    else:
        kl_divergence = abs(1/(control.x[max_x_index] - case.drug_start_day)*quad(kl_integrand,case.drug_start_day , control.x[max_x_index],limit=100)[0])[0]/11
    return(kl_divergence)


def cross_kl_divergences(cat_list):
    #takes a list of categories and computes KL(x,y) for all x and y in the list       
    kl_list = []

    cl = len(cat_list)
    
    #can also be done using enumerate instead    
    
    for i in range(cl):
        print("done %d out of %d"%(i,cl))
        for j in range (i):
#            new_kl = kl_between_controls(cat_list[i],cat_list[j]) 
            new_kl  = kl_divergence(cat_list[i],cat_list[j])
            if (new_kl is not None) and (str(new_kl)!="nan") and str(new_kl)!="inf":
                kl_list.append(new_kl)
    return kl_list



def cv_smoothing(l):
    """
    :param l: the list to be smoothed. Needs to be of type numeric.
    
    returns a KDEMultivariate object, smoothed using leave-one-out cross-validation
    """
    
    return sm.nonparametric.KDEMultivariate(data=l,var_type="c",bw="cv_ml")


def calculate_null_kl (cat_list):
    """
    :param cat_list:  The list of categories from which the null kl is to be calculated
    
    returns the list of values and the smoothed object
    """
    
    l = cross_kl_divergences(cat_list)
    dens = cv_smoothing(l)
    return {"list":l,"smoothed":dens}


def find_critical_value(smoothed,p_val,bounds=[0,20]):
    """
    :param smoothed: the KDEMultivariate object from which to calculate the critical value
    :param p_val: the corresponding p_value
    :bounds: the bounds within to search
    """
    
    #TODO: implement this, using binary search!
    
    