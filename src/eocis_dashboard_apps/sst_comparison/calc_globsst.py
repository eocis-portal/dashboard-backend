#!/usr/bin/env python

# Note: this is copied from https://github.com/surftemp/plots-dev/tree/master/projects/recent-warming

import argparse
import datetime
import os
import numpy as np
import xarray as xr

regions = {
    'sst': dict(lat=slice(-60., 60)),
    'arctic': dict(lat=slice(60, None)),
}


def process_path(path, outname, update=False):
    cci = None
    gmsst = []
    copy_attrs = ['long_name', 'standard_name', 'source']
    if update:
        orig = xr.open_dataset(outname)
    else:
        orig = []
    for root, dirs, files in os.walk(path):
        dirs.sort()  # Easier to make sure we sort before reading data
        for f in files:
            if not f.endswith('.nc'):
                continue
            if update:
                # Need to check midnight version for DOISST
                dt0 = np.datetime64(datetime.datetime.strptime(f[:8], '%Y%m%d'))
                dt1 = np.datetime64(datetime.datetime.strptime(f[:10], '%Y%m%d%H'))
                if dt0 in orig.time or dt1 in orig.time:
                    continue
            print(f)
            ds_full = xr.open_dataset(os.path.join(root, f))
            if ds_full.id == 'DMI-L4UHskin-ARC_IST-DMI_OI':
                # Copy surface temperature to 'sst'
                ds_full['analysed_sst'] = ds_full.analysed_st
            attrs = {at: ds_full.analysed_sst.attrs[at] for at in copy_attrs if at in ds_full.analysed_sst.attrs}
            # Do we have an OSTIA based 0.05 degree product
            ostia = ds_full.id in ['OSTIA-ESACCI-L4-GLOB-v3.0', 'OSTIA-C3S-L4-GLOB-v3.0',
                                   'OSTIA-UKMO-L4-GLOB_ICDR-v3.0',
                                   'DMI-L4UHskin-ARC_IST-DMI_OI']
            if cci is None and not ostia:
                cci = xr.open_dataset(f'ESACCI_LSM_{ds_full.id}.nc')

            out = xr.Dataset()
            out.attrs.update(ds_full.attrs)

            for region in regions:
                ds = ds_full.sel(regions[region])

                wts = np.cos(np.deg2rad(ds.lat))
                wts.name = "weights"

                if ostia:
                    msk_all = ds.analysed_sst > 0
                    msk_ice = msk_all & (ds.sea_ice_fraction < 0.15)
                    msk_cci = msk_all
                elif ds.id == 'CMC0.2deg-CMC-L4-GLOB-v2.0':
                    # Use 5 for CMC2 as the Caspian Sea is flagged as Lake (but not water)
                    # change to 5+8 as CMC unsets water if ice is detected
                    msk_all = (ds.mask.astype(np.int8) & 13 != 0)
                    # Using not over as sea-ice maybe NaN for ice-free (instead of zero)
                    msk_ice = msk_all & ~(ds.sea_ice_fraction >= 0.15)
                    # Only allow cells where SST-CCI mask thinks there might be water
                    # 1 = All water; 2 = All land; 3 = Water and land present
                    msk_cci = (cci.mask & 1) == 1
                else:
                    if 'CMC' in ds.id:
                        # CMC unsets water when ice is flagged
                        msk_all = (ds.mask.astype(np.int8) & 9 != 0)
                    else:
                        msk_all = (ds.mask.astype(np.int8) & 1 != 0)
                    msk_ice = msk_all & ~(ds.sea_ice_fraction >= 0.15)
                    msk_cci = (cci.mask & 1) == 1

                    msk0 = (ds.mask.astype(np.int8) & 1 != 0) & ~(ds.sea_ice_fraction >= 0.15)
                    # Only allow cells where SST-CCI mask thinks there might be water
                    # 1 = All water; 2 = All land; 3 = Water and land present
                    msk1 = msk0 & ((cci.mask & 1) == 1)
                    msk2 = (ds.mask.astype(np.int8) & 1 != 0) & ((cci.mask & 1) == 1)
                # SST is a float32, so we get better accuracy if we convert to C before averaging
                sst = ds.analysed_sst - 273.15
                sea_ice_fraction = ds.sea_ice_fraction
                # Specify dimensions so we do not drop the time axis
                dims = ['lat', 'lon']
                attrs['units'] = 'Celsius'

                out[f'analysed_{region}'] = sst.where(msk_ice & msk_cci).weighted(wts).mean(dims)
                out[f'analysed_{region}'].attrs.update(attrs, comment="Masking in common with ESA CCI")

                if region == 'arctic':
                    out['sea_ice_fraction_arctic'] = sea_ice_fraction.where(msk_cci).weighted(wts).mean(dims)

                out[f'all_{region}'] = sst.where(msk_all & msk_cci).weighted(wts).mean(dims)
                out[f'all_{region}'].attrs.update(attrs, comment="Masking in common with ESA CCI, ignoring sea ice")

                out[f'self_{region}'] = sst.where(msk_all).weighted(wts).mean(dims)
                out[f'self_{region}'].attrs.update(attrs, comment="Using self mask only")

            gmsst.append(out)
    if not gmsst:
        print('No files found')
        return
    gmsst = xr.concat(gmsst, 'time')
    if update:
        gmsst = xr.concat([orig.load(), gmsst], 'time')
        orig.close()
    gmsst.to_netcdf(outname)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('path')
    parser.add_argument('-o', dest='outname', default='globmeansst.nc')
    parser.add_argument('-u', '--update', action='store_true', help='Append to existing output file')
    args = parser.parse_args()

    process_path(args.path, args.outname, args.update)