import datetime
import os
import csv
import xarray as xr
import json
import logging

DATE_FORMAT = "%Y-%m-%d"
variable_name = "fsmc_c4grass"

def update(input_folder, deployment_folder, scan_start_date, scan_stop_date, data_load_fn):

    timeseries_csv_folder = os.path.join(deployment_folder, "data", "timeseries")
    csv_folder = os.path.join(deployment_folder, "data", "csv")
    masks_folder = os.path.join(input_folder,"masks")
    masks = {}
    timeseries = {}
    country_names = {}

    for mask_file in os.listdir(masks_folder):
        country_code = os.path.splitext(mask_file)[0]
        ds = xr.open_dataset(os.path.join(masks_folder,mask_file))
        masks[country_code] = ds["mask"].data
        country_names[country_code] = ds.attrs["name"]

    # read in timeseries
    os.makedirs(csv_folder, exist_ok=True)
    os.makedirs(timeseries_csv_folder, exist_ok=True)

    data_start_date = None
    data_end_date = None

    for csv_file in os.listdir(timeseries_csv_folder):
        country_code = os.path.splitext(csv_file)[0]
        ts = []
        with open(os.path.join(timeseries_csv_folder,csv_file)) as f:
            rdr = csv.reader(f)
            first = True
            for row in rdr:
                if first:
                    # skip header row
                    first = False
                    continue
                dt = datetime.date.fromisoformat(row[0])
                if data_start_date is None:
                    data_start_date = dt
                v = float(row[1])
                ts.append((dt,v))
        timeseries[country_code] = ts

    for country_code in masks:
        if country_code not in timeseries:
            timeseries[country_code] = []

    dt = scan_start_date

    while scan_stop_date is None or dt <= scan_stop_date:

        ds = data_load_fn(dt)

        if ds is not None:
            logging.info("Processing: " + dt.strftime(DATE_FORMAT))
            da = ds[variable_name].isel(time=0)
            means = {}
            # append data to timeseries
            for (country_code, mask) in masks.items():
                ts = timeseries[country_code]

                mean = da.where(mask).mean(skipna=True).data
                means[country_code] = mean
                if len(ts):
                    latest_dt = ts[-1][0]
                    if dt != latest_dt + datetime.timedelta(days=1):
                        raise Exception(f"Dates are not contiguous: {latest_dt:%Y-%m-%d} {dt:%Y-%m-%d}")
                ts.append((dt,mean))

            # write out a csv with this days data
            folder = os.path.join(csv_folder,f"{dt.year:04d}",f"{dt.month:02d}")
            filename = f"stress{dt:%Y%m%d}.csv"
            os.makedirs(folder,exist_ok=True)
            with open(os.path.join(folder,filename),"w") as f:
                wtr = csv.writer(f)
                wtr.writerow(["country","stress"])
                for code in means:
                    wtr.writerow([code,str(means[code])])
        else:
            break
        if data_start_date is None:
            data_start_date = dt
        data_end_date = dt
        dt += datetime.timedelta(days=1)


    for country_code in timeseries:
        with open(os.path.join(timeseries_csv_folder,country_code+".csv"),"w") as f:
            wtr = csv.writer(f)
            wtr.writerow(["date","stress"])
            ts = timeseries[country_code]
            for (dt,v) in ts:
                wtr.writerow([dt.strftime("%Y-%m-%d"),str(v)])

    return (data_start_date, data_end_date, country_names), dt

if __name__ == '__main__':
    import argparse

    root_folder=os.path.split(__file__)[0]
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-folder", default=root_folder)
    parser.add_argument("--deployment-folder",default=os.path.join(root_folder,"..","..","..","static","apps","africa_plant_water_stress"))
    parser.add_argument("--start-date",help="start date for processing, YYYY-MM-DD",default="1983-01-01")
    parser.add_argument("--stop-date", help="stop date for processing, YYYY-MM-DD", default=None)

    args = parser.parse_args()

    scan_start_date = datetime.date.fromisoformat(args.start_date) if args.start_date else None

    status_filename = "status.json"
    status_path = os.path.join(args.input_folder, status_filename)

    if scan_start_date is None:
        if os.path.exists(status_path):
            with open(status_path) as f:
                status = json.loads(f.read())
                scan_start_date = datetime.date.fromisoformat(status["next_start_date"])

    if scan_start_date is None:
        scan_start_date = datetime.date(1983,1,1)

    scan_stop_date = datetime.date.fromisoformat(args.stop_date) if args.stop_date else None

    def data_loader(dt):
        year = dt.year
        month = dt.month
        day = dt.day
        file_path = f"/home/dev/data/soil_moisture/v1.2.0/daily/{year}/{month:02d}/sm{year}_{month:02d}_{day:02d}.v1.2.0.nc"

        if os.path.exists(file_path):
            return xr.open_dataset(file_path)
        return None

    logging.basicConfig(level=logging.INFO)

    metadata, next_start_date = update(args.input_folder, args.deployment_folder, scan_start_date, scan_stop_date, data_loader)

    status = { "next_start_date": next_start_date.isoformat() }
    with open(status_path,"w") as f:
        f.write(json.dumps(status))

    metadata_filename = "metadata.json"
    metadata_path = os.path.join(args.deployment_folder, "data", metadata_filename)
    (data_start_date, data_end_date, country_names) = metadata
    with open(metadata_path,"w") as f:
        f.write(json.dumps({
            "start_date": data_start_date.isoformat() if data_start_date is not None else "",
            "end_date": data_end_date.isoformat() if data_end_date is not None else "",
            "country_names": country_names
        }))


