# pi-report-localinstall

This repo contains a command-line tool for reporting Shotgun Site usage info for
a single or multiple Sites. It identifies users by their email addresses, and
assumes one Shotgun account per email address.

## Requirements

Check the `requirements.txt` file for a list of required Python modules. These
can be installed by running `pip install -r requirements.txt`. We recommend you
do this from a virtualenv environment, in order to keep your local system
environment clean:

https://virtualenv.pypa.io/en/stable/

## Settings

A `settings.yml` file must exist in *this* directory (the same directory that
this `README.md` file lives in), with at least one Shotgun Site defined:

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

Type `report.py -h` or `report --help` for usage details.

## Workflow

After setting values in `settings.yml` and installing the python modules
specified in the `requirements.txt` file, you're ready to generate a report.
This can be done with a single command:

`./report.py --generate`

After the script has finished running, a `report.json` file will be created in
*this* directory. The report can be emailed to Shotgun Support.

By default the script will parse EventLogEntries for the last 30 days. You can
optionally specify a date range with the `start_date` and `end_date` arguments,
for example:

`./report.py --generate -start_date 2017-04-20 -end_date 2017-05-12`

If you want more detailed per-site and user usage info, add the `--verbose`
flag:

`./report.py --generate --verbose`