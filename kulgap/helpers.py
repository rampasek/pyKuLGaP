import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.integrate import quad


def p_value(l1, l2):
    """
    returns p-value for each x in l1, based on l2
    :param l1: The list  of x for which the p-value is to be computed
    :param l2: The list of values on which the p-value calculation is based
    :return: The calculated list of p-values
    """
    pval_list = []
    for y in l1:
        pval_list.append((len([x for x in l2 if x >= y]) + 1) / (len(l2) + 1))
    return pval_list


def get_all_treatment_conditions(treatment_response_experiment):
    """
    Takes a list of patients and returns a dictionary of all categories in the list of patients,

    :param treatment_response_experiment: [TreatmentResponseExperiment] A container holding the set of
        `CancerModel` objects associated with a treatment response experiment.
    :return: [dict] A dictionary of the form {name: treatment_condition}
    """
    treatment_condition_dict = {}
    for _, cancer_model in treatment_response_experiment:
        control = cancer_model.treatment_conditions.get("Control")
        for condition_name, treatment_condition in cancer_model.treatment_conditions:
            if condition_name != "Control":
                treatment_condition_dict[str(cancer_model.name) + "-" + str(condition_name)] = \
                    {"case": treatment_condition, "control": control}
    return treatment_condition_dict


def calculate_AUC(x, y):
    """
    Calculates the area under the curve of a set of observations 

    :param x [ndarray] the time points:
    :param y [ndarray] the observations:
    :return [float] The area under the curve:    
    """
    AUC = 0
    l = min(len(x), len(y))
    for j in range(l - 1):
        AUC += (y[j + 1] - y[j]) / (x[j + 1] - x[j])
    return AUC


def kl_divergence(case, control):
    """
    Calcluates KL divergence between case and control
    :param case: The treatment TreatmentCondition object
    :param control: The control TreatmentCondition object
    :return: [float] The KL value
    """

    def kl_integrand(t):
        mean_control, var_control = control.gp.predict(np.asarray([[t]]))
        mean_case, var_case = case.gp.predict(np.asarray([[t]]))
        return ((var_control + (mean_control - mean_case) ** 2) / (2 * var_case)) + (
                (var_case + (mean_case - mean_control) ** 2) / (2 * var_control)) - 1

    max_x_index = min(case.measurement_end, control.measurement_end)
    if control.y.shape[1] > case.y.shape[1]:
        kl_divergence = abs(1 / (case.x[max_x_index] - case.drug_start_day) *
                            quad(kl_integrand, case.drug_start_day, case.x[max_x_index], limit=100)[0])[0] / 11
    else:
        kl_divergence = abs(1 / (control.x[max_x_index] - case.drug_start_day) *
                            quad(kl_integrand, case.drug_start_day, control.x[max_x_index], limit=100)[0])[0] / 11
    return kl_divergence


def cross_kl_divergences(treatment_condition_list):
    """
    takes a list of categories and computes KL(x,y) for all x and y in the list
    :param treatment_condition_list: A list of TreatmentCondition objects
    :return: The list of all KL(x,y) as x, y range over cat_list
    """
    kl_list = []
    cl = len(treatment_condition_list)

    for i in range(cl):
        print(f"done {i} out of {cl}")
        for j in range(i):
            new_kl = kl_divergence(treatment_condition_list[i], treatment_condition_list[j])
            if (new_kl is not None) and (str(new_kl) != "nan") and str(new_kl) != "inf":
                kl_list.append(new_kl)
    return kl_list


def cv_smoothing(list_to_be_smoothed):
    """
    Computes kernel smoothing for list_to_be_smoothed
    :param list_to_be_smoothed: the list to be smoothed. Needs to be of type numeric.
    
    :return: a KDEMultivariate object, smoothed using leave-one-out cross-validation
    """
    return sm.nonparametric.KDEMultivariate(data=list_to_be_smoothed, var_type="c", bw="cv_ml")


def calculate_null_kl(treatment_condition_list=None, filename=None):
    """
    Calculates the smoothed null KL distribution. One of the two parameters must be non-null
    :param treatment_condition_list: [list] The list of treatment condition from which the null kl is to be calculated.
    :param filename: If None, calculate from category_list. Else read in from file_path
    :return: [list] the list of values and the smoothed object
    """
    if filename is None and treatment_condition_list is not None:
        null_kl_data = cross_kl_divergences(treatment_condition_list)
    elif filename is not None and treatment_condition_list is None:
        null_kl_data = list(pd.read_csv(filename, header=None)[0])
    else:
        raise ValueError("Only one of `filename` or `treatment_condition_list` can be passed as a parameter!")
    smoothed_null_kl = cv_smoothing(null_kl_data)
    return {"list": null_kl_data, "smoothed": smoothed_null_kl}


def dict_to_string(dictionary):
    """
    Write the input dictionary to a string of the form {key:entry,...}
    :param dictionary: A dictionary
    :return: The converted string
    """
    return "_".join([str(key) + ":" + str(value) for key, value in dictionary.items()])


def remove_extremal_nas(y, replacement_value):
    """
    Replace leading and trailing n/a values in the rows of y by replacement_value
    Return the modified y, the start (first measurement) and the end (last measurement) dates

    :param y [ndarray] the array to be modified:
    :param replacement_value [int] The value with which the nas will be replaced:
    :return [tuple] a tuple containing the items:
        - y the modified ndarray
        - first the last occasion of a leading na
        - last the first occasion of a trailing na
    """
    firsts = []
    lasts = []
    for j, y_slice in enumerate(y):
        ind = np.where(~np.isnan(y_slice))[0]
        firsts.append(ind[0])
        lasts.append(ind[-1])

        y[j, :firsts[-1]] = replacement_value
        y[j, lasts[-1] + 1:] = replacement_value
    first = max(firsts)
    last = min(lasts)
    return y, first, last


def forward_fill_nas(arr):
    """
    forward-fills na values in numpy array arr: replaces it by previous valid choice

    :param arr [ndarray] the array to be modified:
    :return [ndarray] the modified array:
    """
    mask = np.isnan(arr)
    idx = np.where(~mask, np.arange(mask.shape[1]), 0)
    np.maximum.accumulate(idx, axis=1, out=idx)
    out = arr[np.arange(idx.shape[0])[:, None], idx]
    return out


def relativize(y, start):
    """
    Normalises a numpy array to a given start index.
    :param y [ndarray] the array to be normalised:
    :param start [int] the start index:
    :return [ndarray] the modified array:
    """
    return y / y[start] - 1


def centre(y, start):
    """
    Subtracts the value at index start from a numpy array
    :param y [ndarray] the array to be modified:
    :param start [int] the index to centre on:
    :return [ndarray] the modified array
    """
    return y - y[start]


def compute_response_angle(x, y, start):
    """
    Calculates the response angle for observations y, given time points x and start point start
    :param x [ndarray] the time points: 
    :param y [ndarray] the observations:
    :param start [umpy array] the start point for the angle computation:
    :return [float] the angle:
    """
    l = min(len(x), len(y))
    model = sm.OLS(y[start:l], x[start:l])
    results = model.fit()
    return np.arctan(results.params[0])
