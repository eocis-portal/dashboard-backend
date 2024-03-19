import os
import json
import xarray as xr
import numpy as np
from shapely.geometry import shape
from shapely import Point

root_folder = "/home/dev/data/soil_moisture/v1.2.0/"
ds = xr.open_dataset(os.path.join(root_folder,"daily","2020","01","sm2020_01_01.v1.2.0.nc"))
lats = ds["lat"].data
lons = ds["lon"].data
nlats = lats.shape[0]
nlons = lons.shape[0]

output_shape = (nlats,nlons)

lat2d = np.broadcast_to(lats[None].T, output_shape)
lon2d = np.broadcast_to(lons, output_shape)

masks_folder = "masks"
os.makedirs(masks_folder,exist_ok=True)

with open("africa-outline-with-countries_6.geojson") as f:
    geojson = json.loads(f.read())

shapes = {}
names = {}

for feature in geojson["features"]:
    name = feature["properties"]["name"]
    code = feature["properties"]["adm0_a3"]
    names[code] = name
    shapes[code] = shape(feature["geometry"]).buffer(0)

for code in shapes:
    shape = shapes[code]
    name = names[code]
    mask = np.zeros((nlats,nlons),dtype=np.int8)

    for y in range(0,nlats):
        for x in range(0,nlons):
            p = Point(lon2d[y,x],lat2d[y,x])
            if shape.contains(p):
                mask[y,x] = 1
    ds_out = xr.Dataset(attrs={"name":name,"country_code":code})
    ds_out["lat"] = ds["lat"]
    ds_out["lon"] = ds["lon"]
    ds_out["mask"] = xr.DataArray(data=mask, dims=("lat","lon"))
    mask_path = os.path.join(masks_folder, code+".nc")
    ds_out.to_netcdf(mask_path)
    print("writing: "+mask_path)



