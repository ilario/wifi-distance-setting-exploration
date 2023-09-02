#!/usr/bin/env python3
import sys
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sb
from scipy import stats
import numpy as np


param_array = []


def extract_data(filehandl, par="distance"):
    """Reads the log of an experiment and generates a DataFrame
    with the data and the explored parameter

    :param filehandl: handle to the file of the log to be processed
    :param par: name of the parameter that has been explored
    :return: Pandas DataFrame with the data indexed by the value of the parameter

    >>> df = extract_data("iperf3-client.log", par="distance")
    """

    def read_block(filehandl, par="distance"):
        while (par not in (row := filehandl.readline())) & bool(row):
            pass
        # check if the row has some content or if the file is over
        if row:
            # the distance line usually ends with a comma,
            # sometimes the distance in between quotes
            # so we have to remove them. And also remove the newline.
            # looks like:
            # Sun Jun 25 23:10:02 UTC 2023 "distance": 2100, 
            param_str = "".join(c for c in row.split()[7] if c.isalnum())
            param_array.append(int(param_str))
        else:
            # if the row is empty, the file is ended, just returning something
            # for communicating to the loop that the file is over
            yield False
        while ("Cwnd" not in (row := filehandl.readline())) & bool(row):
            pass

        # here we return all the data rows until a termination string is found
        # (or until the end of the file)
        # the table could also be interrupted by a line like this:
        # iperf3: error - unable to receive control message: Connection reset by peer
        # the table could also be interrupted suddenly,
        # without anything else before the next table, like this:
        # [ 33][RX-S] 518.00-519.00 sec  0.00 Bytes  0.00 bits/sec
        # [ 35][TX-S] 518.00-519.00 sec  0.00 Bytes  0.00 bits/sec    0   1.41 KBytes
        # Wed Jul 5 01:00:02 UTC 2023 "distance": "2100",
        while ((row := filehandl.readline()).startswith("[")) & bool(row):
            # using a generator allows to unpack all of the rows at the same time
            # using datatable = [*read_block(filehandl)]
            yield row

    def remove_brakets_split(s):
        # .split() will not separate the first and second column (ID and Role),
        # but ID will be discarded further in the code

        # some lines have 11 items but some have only 8
        # in the longer lines we want also one of these additional columns
        # 0     1           2        3    4     5       6     7         8     9    10
        # [  6][TX-C]   0.00-1.00   sec  2.25 MBytes  18.9 Mbits/sec    0    126 KBytes
        # [  8][RX-C]   0.00-1.00   sec  1.43 MBytes  12.0 Mbits/sec
        # we could just return lists with different lengths, but then we would need to fix
        # them to the same length before converting the lists to a 2D NumPy array
        # for example using zip(*itertools.zip_longest(*datatable, fillvalue=np.nan)) but
        # this would be quite slower
        # so it is more convenient to append a padding element np.nan
        sp = s.split() + [np.nan]
        # we are dropping some unused columns
        return sp[1:2]+sp[6:9]

    datatensor = []
    while True:
        datatable = [*read_block(filehandl, par)]

        # interrupt if an empty line is received, as this indicates that the file is over
        if datatable[0]:
            datatensor.append(datatable)
        else:
            break

    # I am not sure this is the most efficient way to do this...
    datatensor = [map(remove_brakets_split, datatable)
                  for datatable in datatensor]
    # print(datatensor[0])
    # <map object at 0x7fc49c04c970>

    # converting the lists to NumPy array as an intermediate step before
    # converting this to a Pandas DataFrame
    # the alternatives would be:
    # convert the lists to dictionaries
    # convert the lists to io.StringIO
    datanplist = [np.array(list(datatable), dtype="<U32")
                  for datatable in datatensor]
    # at this point the data looks like:
    # print(datanplist[0])
    # [['6][TX-C]' '12.2' 'Mbits/sec' '0']
    # ['8][RX-C]' '8.28' 'Mbits/sec' 'nan']
    # ['6][TX-C]' '14.9' 'Mbits/sec' '0']
    # ...
    # print(datanplist[0].dtype)
    # <U32

    df = [pd.DataFrame(data, columns=("Role", "Bitrate", "Units", "Retry"))
          for data in datanplist]
    # at this point the data looks like:
    # print(df[0])
    #          Role Bitrate      Units Retry
    # 0    6][TX-C]    12.2  Mbits/sec     0
    # 1    8][RX-C]    8.28  Mbits/sec   nan
    # 2    6][TX-C]    14.9  Mbits/sec     0
    # 3    8][RX-C]    3.78  Mbits/sec   nan
    # 4    6][TX-C]    26.7  Mbits/sec     0
    # ..        ...     ...        ...   ...
    # [958 rows x 4 columns]
    # print(df[0].dtypes)
    # Role       object
    # Bitrate    object
    # Units      object
    # Retry      object

    df = pd.concat(df, ignore_index=False, keys=param_array,
                   names=[par, "Entry"])
    # at this point the data looks like:
    # print(df)
    #                     Role Bitrate      Units Retry
    # distance Entry                                   
    # 2100     0      6][TX-C]    12.2  Mbits/sec     0
    #          1      8][RX-C]    8.28  Mbits/sec   nan
    #          2      6][TX-C]    14.9  Mbits/sec     0
    #          3      8][RX-C]    3.78  Mbits/sec   nan
    #          4      6][TX-C]    26.7  Mbits/sec     0
    # ...                  ...     ...        ...   ...
    # [20138 rows x 4 columns]

    df.reset_index(level="Entry", inplace=True)
    # at this point the data looks like:
    # print(df)
    #           Entry      Role Bitrate      Units Retry
    # distance                                          
    # 2100          0  6][TX-C]    12.2  Mbits/sec     0
    # 2100          1  8][RX-C]    8.28  Mbits/sec   nan
    # 2100          2  6][TX-C]    14.9  Mbits/sec     0
    # 2100          3  8][RX-C]    3.78  Mbits/sec   nan
    # 2100          4  6][TX-C]    26.7  Mbits/sec     0
    # [20138 rows x 5 columns]
    # print(df.dtypes)
    # Entry       int64
    # Role       object
    # Bitrate    object
    # Units      object
    # Retry      object

    # there is a TX and a RX line per each second, so 120 lines per minute
    df["Single Meas. Time"] = df["Entry"].values / 120
    # actually, the measures are performed with some pause in between,
    # but for ease of plotting this pause time will be disregarded
    df["Total Meas. Time"] = np.linspace(0, len(df)/120, len(df))
    df.drop(columns="Entry", inplace=True)
    # # at this point the data looks like:
    # print(df)
    #               Role Bitrate      Units Retry  Single Meas. Time  Total Meas. Time
    # distance                                                                        
    # 2100      6][TX-C]    12.2  Mbits/sec     0           0.000000          0.000000
    # 2100      8][RX-C]    8.28  Mbits/sec   nan           0.008333          0.008334
    # 2100      6][TX-C]    14.9  Mbits/sec     0           0.016667          0.016667
    # 2100      8][RX-C]    3.78  Mbits/sec   nan           0.025000          0.025001
    # 2100      6][TX-C]    26.7  Mbits/sec     0           0.033333          0.033335
    # ...            ...     ...        ...   ...                ...               ...
    # [20138 rows x 6 columns]
    # print(df.dtypes)
    # Role                  object
    # Bitrate               object
    # Units                 object
    # Retry                 object
    # Single Meas. Time    float64
    # Total Meas. Time     float64

    # cleaning the Role column, getting rid of the ID information
    striptable = str.maketrans("", "", "][0123456789")
    df["Role"] = df["Role"].str.translate(striptable)
    # Retry is int, but int does not support NaN, so we have to use float
    df = df.astype({"Role": "category", "Bitrate": float,
                   "Units": "category", "Retry": float})
    df.set_index("Role", append=True, inplace=True)
    # at this point the data looks like:
    # print(df)
    #                Bitrate      Units  Retry  Single Meas. Time  Total Meas. Time
    # distance Role                                                                
    # 2100     TX-C    24.40  Mbits/sec    0.0           0.000000          0.000000
    #          RX-C    14.80  Mbits/sec    NaN           0.008333          0.008334
    #          TX-C     3.77  Mbits/sec    0.0           0.016667          0.016667
    #          RX-C    29.00  Mbits/sec    NaN           0.025000          0.025001
    #          TX-C     3.05  Mbits/sec    0.0           0.033333          0.033335
    # ...                ...        ...    ...                ...               ...
    # 10000    RX-C    32.70  Mbits/sec    NaN           7.958333        167.733332
    #          TX-C     2.99  Mbits/sec    0.0           7.966667        167.741665
    #          RX-C    41.50  Mbits/sec    NaN           7.975000        167.749999
    #          TX-C     4.45  Mbits/sec    0.0           7.983333        167.758333
    #          RX-C    41.60  Mbits/sec    NaN           7.991667        167.766667
    # [20132 rows x 5 columns]
    # print(df.dtypes)
    # Bitrate               float64
    # Units                category
    # Retry                 float64
    # Single Meas. Time     float64
    # Total Meas. Time      float64

    # units management taken from https://stackoverflow.com/a/48005992/5033401
    units_dict = {"Mbits/sec": 1, "Kbits/sec": 1e-3, "bits/sec": 1e-6}
    units_multiplier = df["Units"].map(units_dict).astype(int)
    df["Bitrate_in_Mbps"] = df["Bitrate"].values * units_multiplier
    df.drop(columns=["Bitrate", "Units"], inplace=True)
    # at this point the data looks like:
    # print(df)
    #                Retry  Single Meas. Time  Total Meas. Time  Bitrate_in_Mbps
    # distance Role                                                            
    # 2100     TX-C    0.0           0.000000          0.000000      24400000.0
    #          RX-C    NaN           0.008333          0.008334      14800000.0
    #          TX-C    0.0           0.016667          0.016667       3770000.0
    #          RX-C    NaN           0.025000          0.025001      29000000.0
    #          TX-C    0.0           0.033333          0.033335       3050000.0
    # ...              ...                ...               ...             ...
    # 10000    RX-C    NaN           7.958333        167.733332      32700000.0
    #          TX-C    0.0           7.966667        167.741665       2990000.0
    #          RX-C    NaN           7.975000        167.749999      41500000.0
    #          TX-C    0.0           7.983333        167.758333       4450000.0
    #          RX-C    NaN           7.991667        167.766667      41600000.0
    # [20132 rows x 4 columns]
    # print(df.dtypes)
    # Retry                float64
    # Single Meas. Time    float64
    # Total Meas. Time     float64
    # Bitrate_in_Mbps       float64
    return df


def describe_data(datadesc, file=None, par="distance"):
    """Gives basic information on the provided DataFrame and
    some statistical analysis. It can also append this to a file.

    :param datadesc: DataFrame to be analyzed
    :param file: optional, file name for appending the results
    :param distance: the parameter that has been explored

    >>> describe_data(df, file="iperf3-client.log-describe.txt", par="distance")
    """

    out = []
    # for avoiding the message
    # "PerformanceWarning: indexing past lexsort depth may impact performance."
    datasorted = datadesc.sort_index()
    datanoindex = datasorted.reset_index()
    # plot a table with the comparison of values by role and by distance,
    # remove the count of lines as it is not interesting
    # converting to string with .to_string() for plotting the whole content
    out.append(
        # remove Time columns, so that they will not appear in the descriptions
        datanoindex.drop(columns=["Single Meas. Time", "Total Meas. Time"]).groupby(
            ["Role", par]).describe().drop(
            "count", axis=1, level=1).to_string())

    out.append("-"*30)
    out.append("Percentage of seconds with zero transfer (%)")
    out.append(datanoindex.pivot_table(values="Bitrate_in_Mbps", index=par,
               columns="Role", aggfunc=lambda x: 100*sum(x == 0)/len(x)).to_string())
    
    out.append("-"*30)
    # here I check the correlation between the TX and RX speeds, as it looks like
    # when RX is high TX is low and vice versa
    for p in datasorted.index.unique(level=par):
        # roles are usually TX-C and RX-C, but when analysing a server log 
        # they are TX-S and RX-S
        roles = datasorted.index.unique(level="Role")
        out.append(f"Pearson correlation between RX and TX with the {par} setting at {p}:")
        # getting the values as series
        s1 = datasorted.loc[p, roles[0]]["Bitrate_in_Mbps"].reset_index(drop=True)
        s2 = datasorted.loc[p, roles[1]]["Bitrate_in_Mbps"].reset_index(drop=True)
        out.append(str(s1.corr(s2)))

    for role in datasorted.index.unique(level="Role"):
        out.append("\n=============== "+role+" ===============")
        datarole = datasorted.loc[(slice(None), role), :].copy()
        datarole.dropna(axis=1, inplace=True)

        dataroleserie = [datarole.loc[par]["Bitrate_in_Mbps"]
                         for par in datarole.index.unique(level=par)]
        out.append(
            f"Role: {role}, One-way ANOVA - " +
            "assumes normal distribution of data and equal variances")
        out.append(str(stats.f_oneway(*dataroleserie)))
        out.append("-"*30)
        out.append(
            f"Role: {role}, Kruskal-Wallis H-test - " +
            "does not assume normal distribution nor equal variances")
        out.append(str(stats.kruskal(*dataroleserie)))
        out.append("-"*30)
        out.append(
            f"Role: {role}, Alexander Govern test - " +
            "assumes normal distribution but does not assume equal variances")
        out.append(str(stats.alexandergovern(*dataroleserie)))

        datarolenoindex = datarole.reset_index(level=par)
        out.append("-"*30)
        out.append(f"Role: {role}, Pearson correlation")
        out.append(str(datarolenoindex.corr()))
        out.append("-"*30)
        out.append(f"Role: {role}, Spearman correlation")
        out.append(str(datarolenoindex.corr(method='spearman')))
        out.append("-"*30)
        out.append(f"Role: {role}, Kendall correlation")
        out.append(str(datarolenoindex.corr(method='kendall')))

    out.append("-"*30 + "\n")
    outstr = "\n".join(out)
    print(outstr)
    if isinstance(file, str):
        with open(file, "a") as filehandl:
            filehandl.write(outstr)


def plot_violinplot(datanoindex, file, par="distance"):
    """Plots a violin plot and a box plot of the speed data divided by role
    (transmitting or receiving) and by the value of the parameter (e.g. distance) 

    :param datadesc: DataFrame to be analyzed
    :param file: optional, file name for appending the results
    :param distance: the parameter that has been explored

    >>> describe_data(df, file="iperf3-client.log-describe.txt", par="distance")
    """

    plt.clf()
    datanoindex = data.reset_index()
    plotax = sb.catplot(y="Bitrate_in_Mbps", x="Role",
                        data=datanoindex, hue=par,
                        bw=.05, scale="width", kind="violin")
    plotax.set(ylabel="Bitrate (Mbits/s)")
    plt.savefig(file, dpi=200)


def plot_vs_single_meas_time_scatter(dataplotting, file, par="distance"):
    datanoindex = dataplotting.reset_index()
    datanoindex = datanoindex.astype({par: "category"})
    plt.clf()
    plotax = sb.relplot(y="Bitrate_in_Mbps", x="Single Meas. Time",
                        hue=par, data=datanoindex, kind="scatter",
                        row="Role", aspect=6, alpha=0.3, linewidth=0)
    n_experiments = round(datanoindex["Total Meas. Time"].iloc[-1] /
                          max(datanoindex["Single Meas. Time"]) /
                          len(datanoindex[par].unique()))
    plotax.set(xlabel=f"Single Measurement Time (min), {n_experiments} measurements " +
                      "overlapped, one point per second",
               ylabel="Bitrate (Mbits/s)")
    plt.savefig(file, dpi=100)


def plot_vs_total_meas_time_scatter(dataplotting, file, par="distance"):
    datanoindex = dataplotting.reset_index()
    datanoindex = datanoindex.astype({par: "category"})
    plt.clf()
    plotax = sb.relplot(y="Bitrate_in_Mbps", x="Total Meas. Time",
                        hue=par, data=datanoindex, kind="scatter",
                        row="Role", aspect=6, alpha=0.4, linewidth=0)
    plotax.set(xlabel="Total Measurement Time (min)",
               ylabel="Bitrate (Mbits/s)")
    plt.savefig(file, dpi=100)


def plot_vs_time_line(dataplotting, file, par="distance", smooth=30):
    """ Group as many data points as indicated by the smooth parameter
    (smoothing) and then plot a line with confidence interval
    """
    # creating a new column for storing the times, rounded with the smooth parameter
    dataplotting["grouped_index"] = 0
    for p in dataplotting.index.unique(level=par):
        # use the line number of the data with the same par value
        # and convert it to a single time in minutes
        # aggregating the points with the smooth parameter, so that they will be
        # smoothed by the plotting function
        dataplotting.loc[p, "grouped_index"] = [
            (gi//smooth*smooth)/120 for gi in range(0, dataplotting.loc[p].shape[0])]

    datanoindex = dataplotting.reset_index()
    datanoindex = datanoindex.astype({par: "category"})
    plt.clf()
    plotax = sb.relplot(y="Bitrate_in_Mbps", x="grouped_index",
                        data=datanoindex, kind="line",
                        row="Role", col=par, aspect=3)
    # the time index starts from zero, so the duration is one second more
    single_meas_duration = dataplotting["Single Meas. Time"].values[-1] + 1/60
    plotax.set(xlabel="Concatenated Single Measurement Time " +
               f"(each measurement was {single_meas_duration:.3g} min long) (min)",
               ylabel="Bitrate (Mbits/s)")
    # adding vertical lines to make clear the separation between different measurements
    for params, ax in plotax.axes_dict.items():
        # subset the data based on the parameters plotted in each of the small plots
        sub = dataplotting.loc[params[1], params[0]]
        # take the lines of the start of each experiment
        substart = sub[sub["Single Meas. Time"]
                       == min(sub["Single Meas. Time"])]
        # the column grouped_index is the one used as x
        for t in substart["grouped_index"]:
            ax.axvline(x=t, dashes=(3, 3), color="gray")
    plt.savefig(file, dpi=100)


def usage():
    print("For documentation check the readme on:\n",
          "https://github.com/ilario/wifi-distance-setting-exploration\n\n" +
          "Provide as arguments:\n",
          "* the parameter name to explore\n",
          "* the file name of the log file\n\n" +
          "For example:\n\n",
          "python iperf3-log-analysis.py distance 20230626-distance_2100/iperf3-client.log\n\n" +
          "Or simply run without arguments for opening a graphical interface that will " +
          "ask for them:\n\n",
          "python iperf3-log-analysis.py\n\n" +
          "Alternative ways to run, useful for running on multiple logs:\n\n",
          "cat *distance_2100*/iperf3-client.log | python iperf3-log-analysis.py distance\n\n",
          "python iperf3-log-analysis.py distance\n" +
          "and then paste in the terminal all the log content and press Ctrl+D twice for " +
          "starting the processing\n\n",
          "python iperf3-log-analysis.py distance <(cat *distance_2100*/iperf3-client.log)")


if __name__ == "__main__":
    FILENAME_OUT = os.path.join(os.getcwd(), "output")
    handle_needs_closing = False
    if "--help" in sys.argv or "-h" in sys.argv:
        usage()
        sys.exit()
    # check if the last argument seems like a valid parameter
    # simply checking that it does not seem a python file
    elif sys.argv[-1].endswith(".py"):
        print("No arguments detected, asking them in a graphical way...")
        from tkinter.simpledialog import askstring
        from tkinter.filedialog import askopenfilename
        PARAM = askstring("Parameter beeing explored",
                          "Which is the name of the parameter that has been " +
                          "explored? (e.g. distance)")
        FILENAME = askopenfilename(title='Choose the log file to process')
        FILENAME_OUT = FILENAME
        handle = open(FILENAME, "r", encoding="us-ascii")
        handle_needs_closing = True
    elif sys.argv[-2].endswith(".py"):
        print("Only one argument detected, " +
              "taking it as the name of the parameter being explored." +
              "Reading the file content from STDIN. Paste here your data " +
              "and interrupt pressing twice Ctrl+D")
        handle = sys.stdin
        PARAM = sys.argv[-1]
    elif os.path.exists(sys.argv[-1]):
        FILENAME = sys.argv[-1]
        # the provided filename could be a pipe, for example:
        # python iperf3-log-analysis.py distance <(cat */iperf3-client.log)
        # in that case, the FILENAME_OUT will be the default "output" value
        if os.path.isfile(FILENAME):
            FILENAME_OUT = FILENAME
        PARAM = sys.argv[-2]
        handle = open(FILENAME, "r", encoding="us-ascii")
        handle_needs_closing = True
    # if there are two arguments and the last argument does not exist
    # something wrong is happening
    else:
        usage()
        sys.exit(1)

    print("###### Reading data... ######")
    data = extract_data(handle, PARAM)
    if handle_needs_closing:
        handle.close()

    saveto = FILENAME_OUT+"-describe.txt"
    print("-"*30 +
          f"\n###### Describing data and saving to {saveto}... ######")
    describe_data(data, saveto, PARAM)

    saveto = FILENAME_OUT+"-violin.png"
    print("-"*30 + f"\n###### Creating violin plot {saveto} ######")
    plot_violinplot(data, saveto)

    saveto = FILENAME_OUT+"-vs_single_meas_time_scatter.png"
    print("-"*30 + "\n###### Creating scatter plot - all measurements overlapped " +
          f"over their duration {saveto} ######")
    plot_vs_single_meas_time_scatter(data, saveto)
    # plot_vs_single_meas_time_scatter(data.loc[2100,"TX-C"], saveto+"-2T.png")
    # plot_vs_single_meas_time_scatter(data.loc[5000,"TX-C"], saveto+"-5T.png")
    # plot_vs_single_meas_time_scatter(data.loc[10000,"TX-C"], saveto+"-10T.png")
    # plot_vs_single_meas_time_scatter(data.loc[2100,"RX-C"], saveto+"-2R.png")
    # plot_vs_single_meas_time_scatter(data.loc[5000,"RX-C"], saveto+"-5R.png")
    # plot_vs_single_meas_time_scatter(data.loc[10000,"RX-C"], saveto+"-10R.png")

    saveto = FILENAME_OUT+"-vs_total_meas_time_scatter.png"
    print("-"*30 + "\n###### Creating scatter plot - measurements plotted in " +
          f"the order they were measured {saveto} ######")
    plot_vs_total_meas_time_scatter(data, saveto, PARAM)

    saveto = FILENAME_OUT+"-vs_time_line.png"
    SMOOTHING = 30
    print("-"*30 +
          "\n###### Creating scatter plot - measurements separated by parameter, " +
          f"each point is the average of {SMOOTHING} actual points {saveto} ######")
    plot_vs_time_line(data, saveto, PARAM, SMOOTHING)
