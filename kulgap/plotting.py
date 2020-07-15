import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib import pylab as pl, patches as mp
from matplotlib.backends.backend_pdf import PdfPages
from scipy.stats import mannwhitneyu

from .create_heatmaps import create_agreements, create_FDR, create_KT
from .helpers import dict_to_string, calculate_null_kl


sns.set(style="ticks")




def create_measurement_dict(all_patients,kl_null_filename):
    """
    Creates a dictionary of measurements from a list of Patient objects.
    The keys of the measurement dictionary are the experiments, the corresponding value
    is a dictionary whose keys are the names of the measurements and ve values the corresponding
    values of the measurement for that experiment.
    :param all_patients: The list of Patient objects
    :param kl_null_filename: Name of the file from which the KL null distribution is read
    :return:  [dict] The dictionary of measurements
    """
    stats_dict = {}
    kl_control_vs_control = calculate_null_kl(filename= kl_null_filename)
    for i,patient in enumerate(all_patients):
        control = patient.categories['Control']
        #     control.normalize_data()
        #     control.fit_gaussian_processes()

        for category in patient.categories.keys():
            if 'Control' not in category:
                cur_case = patient.categories[category]
                key = str(cur_case.phlc_id) + "*" + str(category)
                stats_dict[key] = {'tumour_type': patient.tumour_type, 'mRECIST': None, 'num_mCR': None,
                                   'num_mPR': None,
                                   'num_mSD': None, 'num_mPD': None,
                                   'perc_mCR': None, 'perc_mPR': None,
                                   'perc_mSD': None, 'perc_mPD': None,
                                   'drug': None,
                                   'response_angle': None, 'response_angle_control': None,
                                   'perc_true_credible_intervals': None,
                                   'delta_log_likelihood': None,
                                   'kl': None, 'kl_p_value': None, 'kl_p_cvsc': None, 'gp_deriv': None,
                                   'gp_deriv_control': None, 'auc': None,
                                   'auc_control_norm': None, 'auc_norm': None, 'auc_control': None, 'auc_gp': None,
                                   'auc_gp_control': None,
                                   'number_replicates': len(cur_case.replicates),
                                   'number_replicates_control': len(control.replicates),
                                   "tgi": cur_case.tgi}
                stats_dict[key]['drug'] = category

                try:
                    cur_case.calculate_mrecist()
                    cur_case.enumerate_mrecist()
                except Exception as e:
                    print(e)
                    continue
                
                if cur_case.kl_divergence is not None:
                    cur_case.kl_p_value = (len([x for x in kl_control_vs_control["list"] if
                                                    x >= cur_case.kl_divergence]) + 1) / (
                                                      len(kl_control_vs_control["list"]) + 1)

                    cur_case.kl_p_cvsc = 1 - kl_control_vs_control["smoothed"].cdf(
                            [cur_case.kl_divergence])

                num_replicates = len(cur_case.replicates)
                stats_dict[key]['mRECIST'] = dict_to_string(cur_case.mrecist)
                stats_dict[key]['num_mCR'] = cur_case.mrecist_counts['mCR']
                stats_dict[key]['num_mPR'] = cur_case.mrecist_counts['mPR']
                stats_dict[key]['num_mSD'] = cur_case.mrecist_counts['mSD']
                stats_dict[key]['num_mPD'] = cur_case.mrecist_counts['mPD']
                stats_dict[key]['perc_mCR'] = cur_case.mrecist_counts['mCR'] / num_replicates
                stats_dict[key]['perc_mPR'] = cur_case.mrecist_counts['mPR'] / num_replicates
                stats_dict[key]['perc_mSD'] = cur_case.mrecist_counts['mSD'] / num_replicates
                stats_dict[key]['perc_mPD'] = cur_case.mrecist_counts['mPD'] / num_replicates

                stats_dict[key]['perc_true_credible_intervals'] = cur_case.percent_credible_intervals
                stats_dict[key]['delta_log_likelihood'] = cur_case.delta_log_likelihood_h0_h1
                stats_dict[key]['kl'] = cur_case.kl_divergence
                stats_dict[key]['kl_p_value'] = cur_case.kl_p_value
                stats_dict[key]['kl_p_cvsc'] = cur_case.kl_p_cvsc
                stats_dict[key]['gp_deriv'] = np.nanmean(cur_case.rates_list)
                stats_dict[key]['gp_deriv_control'] = np.nanmean(cur_case.rates_list_control)

                stats_dict[key]['auc'] = dict_to_string(cur_case.auc)
                stats_dict[key]['auc_norm'] = dict_to_string(cur_case.auc_norm)
                stats_dict[key]['auc_control'] = dict_to_string(cur_case.auc_control)
                stats_dict[key]['auc_control_norm'] = dict_to_string(cur_case.auc_control_norm)
                try:
                    stats_dict[key]['auc_gp'] = cur_case.auc_gp[0]
                    stats_dict[key]['auc_gp_control'] = cur_case.auc_gp_control[0]
                except TypeError:
                    stats_dict[key]['auc_gp'] = ""
                    stats_dict[key]['auc_gp_control'] = ""

                stats_dict[key]['response_angle'] = dict_to_string(cur_case.response_angle)
                stats_dict[key]['response_angle_rel'] = dict_to_string(cur_case.response_angle_rel)
                stats_dict[key]['response_angle_control'] = dict_to_string(cur_case.response_angle_control)
                stats_dict[key]['response_angle_rel_control'] = dict_to_string(cur_case.response_angle_rel_control)

                stats_dict[key]['average_angle'] = cur_case.average_angle
                stats_dict[key]['average_angle_rel'] = cur_case.average_angle_rel
                stats_dict[key]['average_angle_control'] = cur_case.average_angle_control
                stats_dict[key]['average_angle_rel_control'] = cur_case.average_angle_rel_control
    return stats_dict
    
    
    
def create_measurement_df(all_patients):
    """
    Creates a DataFrame of measurements from a list of Patient objects.
    One row per experiment, one column per measurement.
    Wraps the response of create_measurement as a DataFrame
    :param all_patients: The list of Patient objects
    :return:  [DataFrame] The DataFrame of measurements
    """
    stats_dict = create_measurement_dict(all_patients)
    return pd.DataFrame.from_dict(stats_dict).transpose() 

def plusnone(a, b):
    """
    Add a and b, returning None if either of them is None
    :param a: The first summand
    :param b: The second summand
    :return: The sum
    """
    if (a is None) or (b is None):
        return None
    return a + b




def dictvals(dictionary):
    """
    Returns the list of elements in a dictionary, unpacking them if they are inside a list
    :param dictionary: the dictionary to be unpacked
    :returns :[list]
    """
    try:
        return [x[0] for x in dictionary.values()]
    except IndexError:
        return list(dictionary.values())
    except TypeError:
        return list(dictionary.values())


def bts(boolean, y="Y", n="N"):
    """
    Converts a boolean value to a string
    :param boolean: The boolean to be converted
    :param y: [string] the value to be returned if boolean is True
    :param n: [string] the value to be returned if boolean is False
    :return [string]:    
    """
    if boolean:
        return y
    return n


def tsmaller(v1, v2, y="Y", n="N", na="N/a"):
    """
    Compares v1 with v2. Returns the value of y if v1 is smaller than v2 and the value of n
    otherwise. Returns na if either of v1 or v2 is None
    :param v1: the first value of the comparison
    :param v2: the first value of the comparison 
    :param y: the value to be returned if v1<v2
    :param n: the value to be returned if v1>=v2
    :param na: the value to be returned if either v1 or v2 is None.
    """
    if (v1 is not None) and (v2 is not None):
        return bts(v1 < v2, y=y, n=n)
    return na


def mw_letter(d1, d2, pval=0.05, y="Y", n="N", na=None):
    """
    Mann-Whitney U test on d1, d2.
    :param d1: The first list or dict-object to be compared
    :param d2: The second list or dict-object to be compared  
    :param pval: The p-value to be used
    :param y: Returned if the test is significant
    :param n: Returned if the test is not significant
    :param na: Returned if the test fails
    """
    l1 = dictvals(d1)
    l2 = dictvals(d2)
    try:
        return bts(mannwhitneyu(l1, l2).pvalue < pval, y=y, n=n)
    except ValueError as e:
        if na is None:
            return str(e)
        return na


def mw_letter_from_strings(s1, s2, pval=0.05, y="Y", n="N", na=None):
    """
    Turn strings s1, s2 into dictionaries, then apply Mann-Whitney test as in mw_letter
    :param s1: The first string to be compared
    :param s2: The second string to be compared  
    :param pval: The p-value to be used
    :param y: Returned if the test is significant
    :param n: Returned if the test is not significant
    :param na: Returned if the test fails
    """
    if ("nan" == str(s1)) or ("nan" == str(s2)):
        if na is None:
            return "no value"
        return na
    return mw_letter(dict_from_string(s1), dict_from_string(s2), pval, y, n, na)


def dict_from_string(s):
    """
    Inverse of dict_to_string. Takes the string representation of a dictionary and returns
    the original dictionary.
    :param s: The string representation of the dictionary
    :return: [dict] the dictionary
    """
    l = s.replace("[", "").replace("]", "").split("_")
    d = {x.split(":")[0]: float(x.split(":")[1]) for x in l}
    return d


def pointwise_kl(case, control, t):
    """
    Calculates the point-wise KL divergence between case and control at time t
    :param case: The treatment Category
    :param controL: The control Category
    :param t: The time point
    :return: [float] The KL value.
    """
    mean_control, var_control = control.gp.predict(np.asarray([[t]]))
    mean_case, var_case = case.gp.predict(np.asarray([[t]]))
    return ((var_control + (mean_control - mean_case) ** 2) / (2 * var_case)) + (
            (var_case + (mean_case - mean_control) ** 2) / (2 * var_control))


def p_value(y, l2):
    """
    returns p-value for each y based on l2
    :param y: The value for which the p-value is to be computed
    :param l2: The list of values on which the p-value calculation is based
    :return: The calculated p-value
    """
    return (len([x for x in l2 if x >= y]) + 1) / (len(l2) + 1)


def find_start_end(case, control):
    """
    Find the measurement start and end of a control, treatment pair.
    :param case: The treatment Category
    :param controL: The control Category
    :return a [tuple]:
        - the start index point
        - the end index point
    """
    if control is None:
        start = case.find_start_date_index()
        end = case.measurement_end
    else:
        start = max(case.find_start_date_index(), control.measurement_start)
        end = min(case.measurement_end, control.measurement_end)

    return start, end


def logna(x):
    """
    Calcluate the log of x except return 0 if x is None
    :param x: the input value
    :return: the log or 0.
    """
    if x is None:
        return 0
    return np.log(x)


def plot_gp(case, control, savename):
    """
    Plots a GP fitted to a treatment and control pair.
    :param case: The treatment Category
    :param controL: The control Category
    :param savename: name under which the plot will be saved.
    """
    start, end = find_start_end(case, control)
    plot_limits = [case.x[start][0], case.x[end - 1][0] + 1]
    fig, ax = plt.subplots()

    plt.title("GP fits")
    plt.xlim(*plot_limits)
    plt.ylim([0, 3.75])

    plt.xlabel("Time since start of experiment (days)")
    plt.ylabel("Log-normalized tumor size")

    control.gp.plot_data(ax=ax, color="blue")
    control.gp.plot_mean(ax=ax, color="blue", plot_limits=plot_limits, label="Control mean")
    control.gp.plot_confidence(ax=ax, color="blue", plot_limits=plot_limits, label="Control confidence")

    case.gp.plot_data(ax=ax, color="red")
    case.gp.plot_mean(ax=ax, color="red", plot_limits=plot_limits, label="Treatment mean")
    case.gp.plot_confidence(ax=ax, color="red", plot_limits=plot_limits, label="Treatment confidence")
    plt.savefig(savename)


def plot_category(case, control, means=None, savename="figure.pdf", normalised=True):

    """
    Fully plot a category
    :param case: the category to be plotted. Not allowed to be None
    :param control : the corresponding control to be plotted. Can be None
    :paran mean:  whether the mean values across replicates are also plotted. Can be None
        (mean will not be plotted), "both" (mean is overlayed) or "only" 
        (only mean is plotted)
    :param savename: The file name under which the figure will be saved.
    :param normalised: If true, plots the normalised versions (case.y_norm). Otherwise case.y
    :return [Figure]: The figure showing the plot
    """
    case_y = case.y_norm if normalised else case.y

    if means not in [None, "only", "both"]:
        raise ValueError("means must be None, 'only', or 'both'")

    start, end = find_start_end(case, control)
    if control is None:
        #        start,end = case.find_start_date_index()
        #        end = case.measurement_end
        high = case_y[:, start:end].max()
    else:
        control_y = control.y_norm if normalised else control.y
        high = max(case_y[:, start:end].max(), control_y[:, start:end].max())
    low = min(case_y[:, start:end].min() * 10, 0)
    fig = plt.figure()
    plt.ylim(low, high * 1.05)
    plt.xlabel("Time since start of experiment (days)")
    if normalised:
        plt.ylabel("Log-normalized tumor size")
    else:
        plt.ylabel("Tumor size (mm3)")
    if means is None:
        plt.title("Replicates")
    elif means == "both":
        plt.title("Replicates and mean")
    else:
        plt.title("Means")
    if means != "only":
        if case is not None:
            for (j, y_slice) in enumerate(case_y):
                if j == 1:
                    s = "treatment"
                else:
                    s = "_treatment"
                plt.plot(case.x[start:end], y_slice[start:end], '.r-', label=s)
        if control is not None:
            for j, y_slice in enumerate(control_y):
                if j == 1:
                    s = "control"
                else:
                    s = "_control"
                plt.plot(control.x[start:end], y_slice[start:end], '.b-', label=s)
    if means is not None:
        if means == "both":
            scase = ".k-"
            scontrol = ".k-"
        else:
            scase = ".r-"
            scontrol = ".b-"
        plt.plot(case.x[start:end], case_y.mean(axis=0)[start:end], scase, label="treatment")
        plt.plot(control.x[start:end], control_y.mean(axis=0)[start:end], scontrol, label="control")
    fig.legend(loc='upper left', bbox_to_anchor=(0.125, .875))  # loc="upperleft"
    #    fig.legend(loc=(0,0),ncol=2)#"upper left")
    fig.savefig(savename)
    return fig


def plot_everything(outname, all_patients, stats_df, ag_df, kl_null_filename, fit_gp=True, p_val=0.05, p_val_kl=0.05, tgi_thresh=0.6):
    """
    Plot a long PDF, one page per patient in all_patients
    :param outname: The name under which the PDF will be saved
    :param all_patients: list of Patient objects to be plotted
    :param stats_df: corresponding DataFrame of continuous statistics
    :param ag_df: corresponding DataFrame of binary classifiers
    :param kl_null_filename: Filename from which the KL null is read
    :param fit_gp: whether a GP was fitted
    :param p_val: the p-value
    :param p_val_kl: The p-value for the KuLGaP calculation
    :param tgi_thresh: The threshold for calling a TGI response.
    """
    all_kl = calculate_null_kl(filename= kl_null_filename)
    with PdfPages(outname) as pdf:
        for n, patient in enumerate(all_patients):
            control = patient.categories["Control"]
            for cat, cur_cat in patient.categories.items():
                if cat != "Control":
                    # TO ADD: SHOULD START ALSO CONTAIN control.measurement_start?!?
                    start = max(cur_cat.find_start_date_index(), cur_cat.measurement_start)
                    end = min(cur_cat.measurement_end, control.measurement_end)
                    name = str(patient.name) + "*" + str(cat)
                    #                    plt.figure(figsize = (24,18))

                    fig, axes = plt.subplots(4, 2, figsize=(32, 18))
                    fig.suptitle(name, fontsize="x-large")
                    axes[0, 0].set_title("Replicates")

                    print("Now plotting patient", name)
                    for y_slice in cur_cat.y_norm:
                        axes[0, 0].plot(cur_cat.x[start:end], y_slice[start:end], '.r-')

                    if control.y_norm is None:
                        print("No control for patient %d, category %s" % (n, str(cat)))
                        print(patient)
                        print('----')
                    else:
                        for y_slice in control.y_norm:
                            axes[0, 0].plot(control.x[start:end], y_slice[start:end], '.b-')

                    axes[1, 0].set_title("Means")
                    axes[1, 0].plot(cur_cat.x[start:end], cur_cat.y_norm.mean(axis=0)[start:end], '.r-')
                    if control.y_norm is not None:
                        axes[1, 0].plot(control.x[start:end], control.y_norm.mean(axis=0)[start:end], '.b-')
                    
                    axes[1, 1].set_title("Pointwise KL divergence")

                    if fit_gp:
                        axes[1, 1].plot(cur_cat.x[start:end + 1].ravel(),
                                        [pointwise_kl(cur_cat, control, t).ravel()[0] for t in
                                         cur_cat.x[start:end + 1].ravel()], 'ro')
                    else:
                        axes[1, 1].axis("off")
                        axes[1, 1].text(0.05, 0.3, "no GP fitting, hence no KL values")
                    axes[2, 0].set_title("GP plot: case")
                    axes[2, 1].set_title("GP plot: control")
                    if fit_gp:
                        cur_cat.gp.plot(ax=axes[2, 0])
                        pl.show(block=True)
                        control.gp.plot(ax=axes[2, 1])
                        pl.show(block=True)
                    else:
                        for axis in [axes[2, 0], axes[2, 1]]:
                            axis.text(0.05, 0.3, "not currently plotting GP fits")

                    axes[3, 0].axis("off")
                    txt = []
                    mrlist = [str(stats_df.loc[name, mr]) for mr in ["num_mCR", "num_mPR", "num_mSD", "num_mPD"]]
                    txt.append("mRECIST: (" + ",".join(mrlist))
                    for col in ["kl", "response_angle_rel", "response_angle_rel_control", "auc_norm",
                                "auc_control_norm", "tgi"]:
                        txt.append(col + ": " + str(stats_df.loc[name, col]))

                    # TO ADD: MAYBE BETTER AGGREGATE DATA?
                    txt.append("red = treatment,       blue=control")
                    axes[3, 0].text(0.05, 0.3, '\n'.join(txt))

                    axes[0, 1].axis("off")
                    rtl = ["KuLGaP: " + bts(cur_cat.kl_p_cvsc < p_val),
                           "mRECIST (Novartis): " + tsmaller(stats_df.loc[name, "perc_mPD"], 0.5),
                           "mRECIST (ours): " + tsmaller(
                               plusnone(stats_df.loc[name, "perc_mPD"], stats_df.loc[name, "perc_mSD"]), 0.5),
                           "Angle: " + mw_letter(cur_cat.response_angle_rel, cur_cat.response_angle_rel_control,
                                                 pval=p_val),
                           "AUC: " + mw_letter(cur_cat.auc_norm, cur_cat.auc_control_norm, pval=p_val),
                           "TGI: " + tsmaller(tgi_thresh, cur_cat.tgi)]

                    #                    not yet implemented" )
                    # TO ADD: TGI
                    resp_text = "\n".join(rtl)
                    axes[0, 1].text(0.05, 0.3, resp_text, fontsize=20)

                    pdf.savefig(fig)
                    plt.close()




def get_classification_df(stats_df, p_val=0.05, p_val_kl=0.05, tgi_thresh=0.6):
    """
    Computes the DF of classifications (which measures call a Responder) from the continuous statistics
    :param stats_df: corresponding DataFrame of continuous statisitics
    :param p_val: the p-value for the angle and AUC tests
    :param p_val_kl: The p-value for the KuLGaP calculation
    :param tgi_thresh: The threshold for calling a TGI response.    
    :return:
    """
    responses = stats_df.copy()[["kl"]]

    responses["kulgap"] = stats_df.kl_p_cvsc.apply(lambda x: tsmaller(x, p_val, y=1, n=-1, na=0))
    responses["mRECIST-Novartis"] = stats_df.perc_mPD.apply(lambda x: tsmaller(x, 0.5, y=1, n=-1, na=0))
    
    responses["Angle"] = stats_df.apply(
        lambda row: mw_letter_from_strings(row["response_angle_rel"], row["response_angle_rel_control"], pval=p_val,
                                            y=1, n=-1, na=0), axis=1)
    responses["AUC"] = stats_df.apply(
        lambda row: mw_letter_from_strings(row["auc_norm"], row["auc_control_norm"], pval=p_val, y=1, n=-1, na=0),
        axis=1)
    responses["TGI"] = stats_df.tgi.apply(lambda x: tsmaller(tgi_thresh, x, y=1, n=-1, na=0))
    responses.drop("kl", axis=1, inplace=True)
    return responses


def get_classification_dict_with_patients(all_patients, stats_df, p_val, all_kl, p_val_kl, tgi_thresh):
    """
    Return the responses (responder/non-responder calls) as a dictionary, using the list of patients
    rather than the DataFrame input
    :param all_patients: list of Patient objects
    :param stats_df: corresponding DataFrame of continuous statistics
    :param p_val: the p-value
    :param all_kl: The list of KL null values
    :param p_val_kl: The p-value for the KuLGaP calculation
    :param tgi_thresh: The threshold for calling a TGI response.    

    :return: a dictionary of lists of calls (values) for each classifier (keys)
    """
    predict = {"kulgap": [], "AUC": [], "Angle": [], "mRECIST_Novartis": [], "mRECIST_ours": [],
               "TGI": []}
    for n, patient in enumerate(all_patients):
        for cat, cur_cat in patient.categories.items():
            if cat != "Control":
                name = str(patient.name) + "*" + str(cat)
                predict["kulgap"].append(tsmaller(p_value(cur_cat.kl_divergence, all_kl), p_val_kl, y=1, n=-1, na=0))
                predict["mRECIST_Novartis"].append(tsmaller(stats_df.loc[name, "perc_mPD"], 0.5, y=1, n=-1, na=0))
                predict["mRECIST_ours"].append(
                    tsmaller(plusnone(stats_df.loc[name, "perc_mPD"], stats_df.loc[name, "perc_mSD"]), 0.5, y=1, n=-1,
                             na=0))
                predict["Angle"].append(
                    mw_letter(cur_cat.response_angle_rel, cur_cat.response_angle_rel_control, pval=p_val, y=1, n=-1,
                              na=0))
                predict["AUC"].append(
                    mw_letter(cur_cat.auc_norm, cur_cat.auc_control_norm, pval=p_val, y=1, n=-1, na=0))
                predict["TGI"].append(tsmaller(tgi_thresh, cur_cat.tgi, y=1, n=0, na=2))
    return predict





def create_and_plot_agreements(classifiers_df, agreements_outfigname, agreements_outname):
    """
    Creates and plots the agreement matrix between measures
    :param classifiers_df: The DataFrame of responder calls
    :param agreements_outfigname: Name under which the figure will be saved
    :param agreements_outname: Name under which the data will be saved.
    """
    agreements = create_agreements(classifiers_df)
    agreements.to_csv(agreements_outname)
    paper_list = ["kulgap", "TGI", "mRECIST", "AUC", "Angle"]
    ag2 = agreements[paper_list].reindex(paper_list)
    print(ag2)
    plt.figure()
    sns.heatmap(ag2, vmin=0, vmax=1, center=.5, square=True, annot=ag2, cbar=False, linewidths=.3, linecolor="k",
                cmap="Greens")
    #    sns.heatmap(agreements, vmin=0, vmax=1, center=0,square=True,annot=agreements,cbar=False)
    plt.savefig(agreements_outfigname)


#TODO: this function to be removed
# def create_and_plot_conservative(classifiers_df, conservative_outfigname, conservative_outname):
#     """

#     :param classifiers_df:
#     :param conservative_outfigname:
#     :param conservative_outname:
#     """
#     conservative = create_conservative(classifiers_df)
#     conservative.to_csv(conservative_outname)
#     paper_list = ["kulgap", "TGI", "mRECIST", "AUC", "Angle"]
#     con2 = conservative[paper_list].reindex(paper_list)
#     plt.figure()
#     sns.heatmap(con2, cmap="coolwarm", square=True, annot=con2,
#                 cbar=False, linewidths=.3, linecolor="k", vmin=-.8, vmax=.8, center=-0.1)
#     # sns.heatmap(conservative, square=True,annot=conservative.round(2),cmap="coolwarm",cbar=False)
#     plt.savefig(conservative_outfigname)


def create_and_plot_FDR(classifiers_df, FDR_outfigname, FDR_outname):
    """
    Creates the false discovery matrix and then plots it
    :param classifiers_df: The DataFrame of responder calls
    :param FDR_outfigname: Name under which the figure will be saved
    :param FDR_outname: Name under which the data will be saved.
    """
    FDR = create_FDR(classifiers_df)
    FDR.to_csv(FDR_outname)
    paper_list = ["kulgap", "TGI", "mRECIST", "AUC", "Angle"]
    FDR = FDR[paper_list].reindex(paper_list)
    plt.figure()
    sns.heatmap(FDR, cmap="coolwarm", square=True, annot=FDR,
                cbar=False, linewidths=.3, linecolor="k", vmin=-.8, vmax=.8, center=-0.1)
    plt.savefig(FDR_outfigname)


def create_and_save_KT(classifiers_df, KT_outname):
    """
    Creates and saves the matrix of Kendall Tau tests between the responder calls
    :param classifiers_df: The DataFrame of responder calls
    :param KT_outname: The name under which the data will be saved
    """
    kts = create_KT(classifiers_df)
    print(kts)
    kts.to_csv(KT_outname)


def plot_histogram(list_to_be_plotted, varname, marked=None, savename=None, smoothed=None, x_min=None, x_max=None, dashed=None,
                   solid=None):
    """
    Plots the histogram of list_to_be_plotted, with an asterix and an arrow at marked
    Labels the x axis according to varname
    :param list_to_be_plotted: The list to be plotted
    :param varname: The label for the x-axis
    :param marked: Where the arrow is to appear
    :param savename: Filename under which the figure will be saved
    :param smoothed: Either none or a smoothed object
    :param x_min: The left end point of the range of x-values
    :param x_max: The right end point of the range of x-values
    :param dashed: Where to draw a vertical dashed line
    :param solid: Where to draw a vertical solid line
    :return:
    """
    fig = plt.figure()
    var = pd.Series(l)
    var.dropna().hist(bins=30, grid=False, density=True)
    if smoothed is not None:
        x = np.linspace(x_min, x_max, 1000)
        plt.plot(x, smoothed(x), "-r")
    plt.xlabel(varname)
    plt.ylabel("frequency")
    if marked is not None:
        plt.plot(marked, .02, marker="*", c="r")
        style = "Simple,tail_width=0.5,head_width=4,head_length=8"
        kw = dict(arrowstyle=style, color="k")
        plt.text(11, .2, "critical value")
        arrow = mp.FancyArrowPatch(posA=[11, .2], posB=[marked + .25, 0.035], connectionstyle="arc3,rad=-.25", **kw)
        plt.gca().add_patch(arrow)
    if dashed is not None:
        for val in dashed:
            ax = plt.gca()
            ax.axvline(x=val, color='black', linestyle="--")
    if solid is not None:
        for val in solid:
            ax = plt.gca()
            ax.axvline(x=val, color='black', linestyle="-")

    plt.savefig(savename)
    return fig


def create_scatterplot(stats_df, classifiers_df, savename):
    """
    Creates a scatterplot of all experiments, plotting the number of measures agreeing on 
    a responder label against the logarithm of the KL divergenc.
    Not used in the paper
    :param stats_df: [DataFrame] The raw values of the statistics
    :param classifiers_df: [DataFrame] The binary values (1/0) of the measures
    :param savename: The name under which the figure is saved.
    """

    df = stats_df[["kl"]]
    df.loc[:, "kl_p"] = stats_df.kl_p_cvsc
    df.loc[:, "Ys"] = classifiers_df.drop("kulgap", axis=1).apply(lambda row: row[row == 1].count(), axis=1)

    plt.figure()
    plt.ylim(0, 5)
    plt.plot(df.kl.apply(logna), df.Ys, 'r', marker=".", markersize=2, linestyle="")
    c = np.log(7.97)
    plt.plot([c, c], [0, 5], 'k-', lw=1)
    c = np.log(5.61)
    plt.plot([c, c], [0, 5], 'k--', lw=1)
    c = np.log(13.9)
    plt.plot([c, c], [0, 5], 'k--', lw=1)
    plt.xlabel("Log(KL)")
    plt.ylabel('Number of measures that agree on a "responder" label')
    plt.ylim(-0.2, 4.2)
    plt.yticks(ticks=[0, 1, 2, 3, 4])
    plt.savefig(savename)


def plot_histograms_2c(stats_df, classifiers_df, savename):
    """
    Plots Figure 2C in the paper.
    :param stats_df: [DataFrame] The raw values of the statistics
    :param classifiers_df: [DataFrame] The binary values (1/0) of the measures
    :param savename: The name under which the figure is saved.
    """
    data = stats_df[["kl"]]
    data.loc[:, "klval"] = stats_df.kl.apply(logna)
    data.loc[:, "count"] = classifiers_df.drop("kulgap", axis=1).apply(lambda row: row[row == 1].count(), axis=1)

    ordering = list(data['count'].value_counts().index)
    ordering.sort(reverse=True)
    g = sns.FacetGrid(data, row="count", hue="count", row_order=ordering,
                      height=1.5, aspect=4, margin_titles=False)

    # Draw the densities
    g.map(plt.axhline, y=0, lw=1, clip_on=False, color='black')
    g.map(sns.distplot, "klval", hist=True, rug=True, rug_kws={'height': 0.1})

    # Define and use a simple function to label the plot in axes coordinates
    def label(x, color, label):
        ax = plt.gca()
        ax.text(0, .2, label, fontweight="bold", color=color,
                ha="left", va="center", transform=ax.transAxes)
        ax.axvline(x=np.log(7.97), color='black', linestyle="-")  # critical value for p-val=0.05
        ax.axvline(x=np.log(5.61), color='black', linestyle="--")  # critical value for p-val=0.1
        ax.axvline(x=np.log(13.9), color='black', linestyle="--")  # critical value for p-val=0.001 

    g.map(label, "klval")

    # Set the subplots to have no spacing
    g.fig.subplots_adjust(hspace=0.01)

    # Remove axes details
    g.set_titles("")
    g.set(yticks=[])

    # Set labels
    g.set_axis_labels(x_var='log(KL)')
    plt.ylabel('Number of measures that agree on a "responder" label', horizontalalignment='left')
    g.despine(bottom=True, left=True)
    plt.savefig("{}.pdf".format(savename))