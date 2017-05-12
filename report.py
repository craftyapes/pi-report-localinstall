#!/usr/bin/env python

# Copyright 2017 Autodesk, Inc.  All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license agreement
# provided at the time of installation or download, or which otherwise accompanies
# this software in either electronic or hard copy form.
#

"""
To learn more about this script, see the README.md file in this directory, or
run `./report.py -h` or `./report.py --help` for usage information.
"""

import os
import sys
import yaml
import json
import logging
import datetime
import argparse
import shotgun_api3


class Report(object):
    """
    This class contains methods related to generating Shotgun Site usage
    reports.
    """

    def __init__(self):
        """
        Defines variables to share across methods, sets up cli, logging, and
        runs generate method.
        """

        # Initialize shared variables.
        self._settings = None
        self._debug = False
        self._sites = {}

        # Initialize a command-line argument parser.
        parser = argparse.ArgumentParser(
            description="This script generates a usage report.json file for a \
            specified time frame, given one or more Shotgun Sites--defined in \
            settings.yml file. If no --start_date or --end_date arguments are \
            specified, 30 days is used. See README.md for more details."
        )

        # Add arguments to the parser.
        parser.add_argument(
            "-g",
            "--generate",
            help="Generate a report.json file.",
            action="store_true",
            required=False,
        )
        parser.add_argument(
            "-s",
            "--start_date",
            help="The start date in YYYY-MM-DD format.",
            required=False,
        )
        parser.add_argument(
            "-e",
            "--end_date",
            help="The end date in YYYY-MM-DD format.",
            required=False,
        )
        parser.add_argument(
            "-v",
            "--verbose",
            help="Create a more detailed report.",
            action="store_true",
            required=False,
        )

        # Print script usage if no arguments are passed.
        if len(sys.argv) < 2:
            print "Usage: report.py --help"
            return

        # Make a dictionary from our command-line arguments.
        self._args = vars(parser.parse_args())

        # Set our shared debug variable if verbose was specified in the args.
        if self._args["verbose"]:
            self._debug = True

        # Set up everything we need to log output.
        self._set_up_logging()

        # Grab our user settings.
        logging.info("Reading settings.yml...")
        if os.path.exists("settings.yml"):
            try:
                with open("settings.yml", "r") as fh:
                    self._settings = yaml.load(fh)
            except Exception, e:
                logging.info("Could not parse settings.yml: %s" % e)
                return
        else:
            logging.error("Did not find settings.yml. See README.md for details.")
            return

        if not self._settings:
            logging.error("Settings dict is empty (bad \"settings.yml\" file?), exiting.")
            return

        if self._args["start_date"] and not self._args["end_date"]:
            logging.error("Start date specified but no end date, exiting.")
            return

        if self._args["end_date"] and not self._args["start_date"]:
            logging.error("End date specified but no start date, exiting.")
            return

        # Duplicate our settings dict to prep for mutation.
        self._sites = self._settings

        # Grab a Python API handle for each Shotgun Site and add it to the
        # self._sites dict.
        for k, v in self._sites.iteritems():

            if not v.get("script_name") or not v.get("script_key"):
                logging.error("Bad or missing settings for %s in settings.yml." % k)
                return

            logging.info("Connecting to %s..." % k)
            v["sg"] = shotgun_api3.Shotgun(
                k,
                script_name=v["script_name"],
                api_key=v["script_key"],
            )

            # We don't need these anymore, so lets clear them out of memory for
            # security.
            v.pop("script_name", None)
            v.pop("script_key", None)

        # Generate the report.
        self._generate()

    def _generate(self):
        """
        Loops through self._sites, mutates it with user information, and writes
        out a report.json file.
        """

        # Init our multi-site variables.
        sites = set()
        multi_site_active_users = set()
        multi_site_logged_in_users = set()

        # Loop through each Site and generate a report.
        for k, v in self._sites.iteritems():

            # Add our Site url for the multi-site report.
            sites.add(k)

            # Get user info for the Site, ignoring Shotgun Support, and add
            # it to self._sites.
            logging.info("Getting active users on %s..." % k)
            active_users = v["sg"].find(
                "HumanUser",
                [
                    ["sg_status_list", "is", "act"],
                    ["email", "is_not", "support@shotgunsoftware.com"],
                ],
                [
                    "login",
                    "name",
                    "department",
                    "groups",
                    "projects",
                    "firstname",
                    "lastname",
                    "email",
                    "permission_rule_set"
                ],
            )
            v["active_users"] = active_users
            v["num_active_users"] = len(active_users)

            # Add active user email addresses to the multi-site set, ignoring
            # Shotgun Support.
            for user in active_users:
                multi_site_active_users.add(user["email"])

            # If no date range was given, use the past month.
            date_filter = ["created_at", "in_last", 1, "MONTH"]
            date_range = "1 month"
            if self._args["start_date"]:
                date_filter = [
                    "created_at",
                    "between",
                    [
                        "%s%s" % (self._args["start_date"], "T00:00:00Z"),
                        "%s%s" % (self._args["end_date"], "T00:00:00Z"),
                    ],
                ]
                date_range = "%s -> %s" % (self._args["start_date"], self._args["end_date"])

            # Get all the user login records for date range, ignoring Shotgun Support
            logging.info("Getting users who logged into %s (date range is %s)..." % (k, date_range))
            users_by_date = v["sg"].find(
                "EventLogEntry",
                [
                    ["event_type", "is", "Shotgun_User_Login"],
                    ["user.HumanUser.email", "is_not", "support@shotgunsoftware.com"],
                    date_filter,
                ],
                [
                    "description",
                    "created_at",
                    "permission_rule_set",
                    "user.HumanUser.login",
                    "user.HumanUser.name",
                    "user.HumanUser.firstname",
                    "user.HumanUser.lastname",
                    "user.HumanUser.email",
                ],
            )

            # The Shotgun handle isn't json-friendly, so lets nix that now that
            # we're done with it.
            v.pop("sg", None)

            # Create a set to capture unique users.
            logged_in_users = set()
            for user in users_by_date:
                logged_in_users.add(user["user.HumanUser.email"])
                multi_site_logged_in_users.add(user["user.HumanUser.email"])

            # Convert the set to a list for json-compatibility and count it.
            v["logged_in_users"] = list(logged_in_users)
            v["num_logged_in_users"] = len(v["logged_in_users"])

        # Add the multi-site report.
        self._sites["multi_site"] = {
            "sites": list(sites),
            "date_range": date_range,
            "active_users": list(multi_site_active_users),
            "logged_in_users": list(multi_site_logged_in_users),
            "num_active_users": len(multi_site_active_users),
            "num_logged_in_users": len(multi_site_logged_in_users),
        }

        # Write out our json file report.
        to_write = self._sites["multi_site"]
        if self._args["verbose"]:
            to_write = self._sites
        logging.info("Generating report.json file...")
        with open("report.json", "w") as fh:
            json.dump(to_write, fh, indent=4, sort_keys=True)
        logging.info("Done! Email report.json file to Shotgun Support.")

    def _set_up_logging(self):
        """
        Creates logs directory and sets up logger-related stuffs.
        """

        # Create a logs directory if it doesn't exist.
        if not os.path.exists("logs"):
            os.makedirs("logs")

        # Create a datestamp var for stamping the logs.
        datestamp = datetime.datetime.now().strftime("%Y_%m_%d_%H-%M-%S")

        # Create a log file path.
        log = os.path.join("logs", "%s.log" % datestamp)

        # Set the logging level via argparse.
        logging_level = logging.INFO
        if self._debug:
            logging_level = logging.DEBUG

        # Set up our logging.
        logging.basicConfig(
            filename=log,
            level=logging_level,
            format="%(levelname)s: %(asctime)s: %(message)s",
        )
        logging.getLogger().addHandler(logging.StreamHandler())

        # Tell the log if we're in "verbose" mode.
        if self._debug:
            logging.info("Verbose is ON.")

if __name__ == "__main__":
    Report()
