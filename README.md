# pi-report-localinstall

This repo contains a command-line tool for reporting Shotgun Site usage info for
a single Site or multiple Sites. It identifies users by their email addresses,
and assumes one Shotgun account per email address.

## Download

To download, simply clone this repo. Or, for those not familar with Git or
GitHub, click the green `Clone or download` button on this page:

https://github.com/shotgunsoftware/pi-report-localinstall

... choose `Download ZIP`, and unzip the package into a directory of your
choice.

## Installation

These instructions assume familiarity with command-line applications—`Terminal`
on MacOS, `GitBash` or similar on Windows, and `Bash` on Linux. They also
assume that `python`, `pip`, and ideally `virtualenv` are already installed (if
you don't know if these items are installed on your system, ask your friendly
IT admin, or Google around with queries like "Install pip Windows").

Once you've verified that `python` and `pip` are installed, open a shell,
navigate into the folder that was created when you unzipped the
`pi-report-localinstall` package, and check the `requirements.txt` file for a
list of required Python modules. These can be installed by running this command:

`pip install -r requirements.txt`.

We recommend you do this from a `virtualenv` environment, in order to keep your
local system environment clean. Full `virtualenv` usage instructions can be
found here:

https://virtualenv.pypa.io/en/stable

## Authenticate

To gain access to a Shotgun Site, `pi-report-localinstall` needs to reference a
Script Key. Visit the following url to learn how to create Script (Application)
Keys for your Shotgun Site:

https://support.shotgunsoftware.com/hc/en-us/articles/219031368-Create-and-manage-API-Scripts

## Settings

A `settings.yml` file must exist in the `pi-report-localinstall` directory with
at least one Shotgun Site and its associated Script Key defined, like this:

```
https://example.shotgunstudio.com:
    script_name: example_script_name
    script_key: 123thisisafakescriptkeyexample123
```

Multiple Sites can be defined:

```
https://example1.shotgunstudio.com:
    script_name: example_script_name1
    script_key: 123thisisafakescriptkeyexample456
https://example2.shotgunstudio.com:
    script_name: example_script_name2
    script_key: 789thisisafakescriptkeyexample101
```

## Usage

Type `./report.py -h` or `./report.py --help` from the `pi-report-localinstall`
directory for usage details.

## Workflow

After setting values in `settings.yml` and installing the python modules
specified in the `requirements.txt` file, you're ready to generate a report.
This can be done with a single command:

`./report.py --generate`

Output should appear in your shell, similar to this:

```
SHOTGUN USAGE REPORT:

Number of unique user accounts that logged in between 2017-04-16 and 2017-05-16: 3

Total number of user accounts with Status currently "Active": 4

Shotgun Sites:
https://example1.shotgunstudio.com
https://example2.shotgunstudio.com
```

This report can be copy/pasted and sent to Shotgun Support. Additionally, a
`report.json` file will be created in the `pi-report-locallinstall` directory.
WARNING: This `report.json` file contains personally identifiable data about the
users of your local Shotgun server. We recommend only storing or transferring
this report in a highly secure way. Please do not send this report to anyone
from Shotgun or Autodesk.

Here are the HumanUser Shotgun fields stored in the
`report.json` file:

```
department
email
firstname
groups
lastname
login
name
permission_rule_set
projects
```

By default the script will parse EventLogEntries for the last 30 days. You can
optionally specify a date range with the `start_date` and `end_date` arguments,
for example:

`./report.py --generate --start_date 2017-04-20 --end_date 2017-05-12`

You can display pre-generated reports with the `--display` flag:

`./report.py --display`

For more detailed user usage info, add the `--in_house` flag:

`./report.py --display --in_house`
