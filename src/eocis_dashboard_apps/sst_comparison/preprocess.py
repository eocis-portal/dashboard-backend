

import csv
import xarray as xr
import argparse
import os.path
import pandas as pd

def extract(input_path, variable_name, output_path):

    ds = xr.open_dataset(input_path)
    time = ds["time"]

    da = ds[variable_name]
    with open(output_path,"w") as of:
        wtr = csv.writer(of)
        wtr.writerow(["date","year","doy",variable_name])
        for (t,v) in zip(time.data,da.data):
            dt = pd.to_datetime(t)
            doy = dt.timetuple().tm_yday
            wtr.writerow([dt.strftime("%Y-%m-%d"),dt.year,doy,v])

folder = os.path.split(__file__)[0]

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-path",default="globmeansst.nc")
    parser.add_argument("--variable-name", default="analysed_sst")
    parser.add_argument("--output-path", default="globmeansst.csv")

    args = parser.parse_args()
    extract(args.input_path,args.variable_name,args.output_path)
