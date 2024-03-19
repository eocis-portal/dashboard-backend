# dashboard-backend

code for generating the data displayed in the dashboard apps

each app backend is implemented within this repo as a sub-package of package `eocis_dashboard_apps`

app frontends are implemented in the [Dashboard repo](https://github.com/eocis-portal/dashboard)

the backend code should must contain:

* an `update.sh` script which is invoked periodically (for example nightly) on the EOCIS host
* other scripts and programs which are invoked by the update script

The app is served from a deployment folder, this will be passed as the argument to the update script

The update script will typically populate or refresh the files in the `data` sub-folder of the deployment folder

## The update process:

* the latest version of the app's source code is pulled before each update runs
* the update script is only allowed to write or update files under the deployment folder
* the amount of data stored under the deployment folder will be restricted
* the update script is allowed to read any data files from the EOCIS datasets
* the update process should be efficient, incrementally updating any deployed data files
* one or more conda environments may be defined using `environment.yml` files and used in the update process


