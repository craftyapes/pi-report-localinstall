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
import re
import sys
import yaml
import json
import logging
import datetime
import argparse
import shotgun_api3

_DESCRIPTION = "This script generates a usage report.json file for a specified \
time frame, given one or more Shotgun Sites (defined in a settings.yml file). \
If no --start_date or --end_date arguments are specified, 30 days is used. See \
README.md for more details."


class Report(object):
    """
    This class contains methods related to generating Shotgun Site usage
    reports.
    """

    def __init__(self, generate, start_date, end_date, in_house, display):
        """
        Defines variables to share across methods, sets up logging, Shotgun
        connections, and runs _generate and _export class methods.

        :param bool generate: Whether to generate a report.json file or not.
        :param string start_date: The date to start searching for HumanUser
                                  logins. Format example: 2017-05-01.
        :param string end_date: The date to end searching for HumanUser login
                                Defaults to today. Format example: 2017-05-01.
        :param bool in_house: Whether or not to include additional HumanUser
                              data in the report.
        :param bool display: This option can be used to quickly print a report
                             to the terminal after the report.json file has been
                             generated.
        """

        # Initialize shared variables. By default, use the last month for the
        # date range.
        self._sites = {}
        self._date_filter = ["created_at", "in_last", 1, "MONTH"]
        self._date_range = "1 month"
        self._in_house = in_house

        # Set up everything we need to log output.
        self._set_up_logging()

        # Bail if we have an invalid set of args.
        if in_house and (not generate and not start_date and not display):
            logging.info(
                "No generate, start_date, or display args specified, exiting."
            )
            return

        # Be generous and run the generate code if we've only got date args.
        if generate or start_date or end_date:

            # Grab our user settings and barf if something is wrong.
            logging.info("Reading settings.yml...")
            if os.path.exists("settings.yml"):
                try:
                    with open("settings.yml", "r") as fh:
                        self._sites = yaml.load(fh)
                except Exception, e:
                    logging.info("Could not parse settings.yml: %s" % e)
                    return
            else:
                logging.error("Did not find settings.yml. See README.md for details.")
                return
            if not self._sites:
                logging.error("Settings dict is empty (bad \"settings.yml\" file?), exiting.")
                return

            # Deal with weird formatting or combinations of date settings.
            if end_date and not start_date:
                logging.error(
                    "End date specified but no start date (would pull too many EventLogEntries), exiting."
                )
                return
            if start_date and not end_date:
                end_date = datetime.datetime.now().strftime("%Y-%m-%d")
                logging.warning("No end date specified, using today (%s)." % end_date)
            date_regex = "^\d{4}-\d{2}-\d{2}$"
            if start_date:
                if not re.search(date_regex, start_date):
                    logging.error("start_date format does not match YYYY-MM-DD, exiting.")
                    return
            if end_date:
                if not re.search(date_regex, end_date):
                    logging.error("end_date format does not match YYYY-MM-DD, exiting.")
                    return
            if not start_date and not end_date:
                today = datetime.datetime.now()
                end_date = today.strftime("%Y-%m-%d")
                start_date = (today - datetime.timedelta(days=30)).strftime("%Y-%m-%d")

            # If we've got a start/end dates, reset the date filter and date range
            # variables.
            if start_date and end_date:
                self._date_filter = [
                    "created_at",
                    "between",
                    [
                        "%s%s" % (start_date, "T00:00:00Z"),
                        "%s%s" % (end_date, "T00:00:00Z"),
                    ],
                ]
                self._date_range = "%s and %s" % (start_date, end_date)

            # Grab a Python API handle for each Shotgun Site and add it to the
            # self._sites dict.
            for site_url, credentials in self._sites.iteritems():

                if not credentials.get("script_name") or not credentials.get("script_key"):
                    logging.error(
                        "Bad or missing settings for %s in settings.yml, exiting." % site_url
                    )
                    return

                logging.info("Connecting to %s..." % site_url)
                credentials["sg"] = shotgun_api3.Shotgun(
                    site_url,
                    script_name=credentials["script_name"],
                    api_key=credentials["script_key"],
                )

                # We don't need these anymore, so lets clear them out of memory for security.
                credentials.pop("script_name", None)
                credentials.pop("script_key", None)

            # Generate, export, and print the report.
            self._generate()
            self._export()
            self._display()

        # Print the report if it has already been generated.
        if display and not generate:

            try:
                # Read in the matched Versions data.
                with open("report.json") as fh:
                    self._sites = json.load(fh)
                self._display()

            except Exception, e:
                logging.error("Can't parse report.json: %s" % e)
                return

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

        # Set the logging level.
        logging_level = logging.INFO

        # Set up our logging.
        logging.basicConfig(
            filename=log,
            level=logging_level,
            format="%(levelname)s: %(asctime)s: %(message)s",
        )
        logging.getLogger().addHandler(logging.StreamHandler())

    def _generate(self):
        """
        Loops through self._sites and mutates it with HumanUser information.
        """

        # Init our multi-site variables.
        sites = set()
        multi_site_active_users = set()
        multi_site_logged_in_users = set()

        # Loop through each Site and generate a report.
        for site_url, site_info in self._sites.iteritems():

            # Add our Site url to the multi-site report.
            sites.add(site_url)

            # Get user info for the Site, ignoring Shotgun Support, and add
            # it to self._sites.
            logging.info("Getting active users on %s..." % site_url)
            active_users = site_info["sg"].find(
                "HumanUser",
                [
                    ["sg_status_list", "is", "act"],
                    ["email", "not_in", ["support@shotgunsoftware.com", "changeme@email.com"]],
                    ["login", "is_not", "shotgun_template_user"],
                ],
                [
                    "email",
                    "login",
                    "name",
                    "department",
                    "groups",
                    "projects",
                    "firstname",
                    "lastname",
                    "permission_rule_set"
                ],
            )
            site_info["active_users"] = active_users
            site_info["num_active_users"] = len(active_users)

            # Add active user email addresses to the multi-site set.
            for user in active_users:
                multi_site_active_users.add(user["email"])

            # Get all the user login records for the date range, ignoring
            # Shotgun Support
            logging.info(
                "Getting users who logged into %s (date range is %s)..." % (
                    site_url,
                    self._date_range
                )
            )
            users_by_date = site_info["sg"].find(
                "EventLogEntry",
                [
                    ["event_type", "is", "Shotgun_User_Login"],
                    ["user.HumanUser.email", "not_in", ["support@shotgunsoftware.com", "changeme@email.com"]],
                    ["user.HumanUser.login", "is_not", "shotgun_template_user"],
                    self._date_filter,
                ],
                [
                    "user.HumanUser.email",
                ],
            )

            # The Shotgun handle isn't json-friendly, so lets nix that, now that
            # we're done with it.
            site_info.pop("sg", None)

            # Create a set to capture unique users.
            logged_in_users = set()
            for user in users_by_date:
                logged_in_users.add(user["user.HumanUser.email"])
                multi_site_logged_in_users.add(user["user.HumanUser.email"])

            # Convert the set to a list for json-compatibility and count it.
            site_info["logged_in_users"] = list(logged_in_users)
            site_info["num_logged_in_users"] = len(site_info["logged_in_users"])

        # Add the multi-site report to self._sites.
        self._sites["multi_site"] = {
            "sites": list(sites),
            "date_range": self._date_range,
            "active_users": list(multi_site_active_users),
            "logged_in_users": list(multi_site_logged_in_users),
            "num_active_users": len(multi_site_active_users),
            "num_logged_in_users": len(multi_site_logged_in_users),
        }

    def _export(self):
        """
        Writes out a report.json file, assuming a valid/mutated self._sites
        dict.
        """

        # Write out our json file report.
        logging.info("Writing report.json file...")
        with open("report.json", "w") as fh:
            json.dump(self._sites, fh, indent=4, sort_keys=True)

    def _display(self):
        """
        Prints different versions of the Sites report to the terminal and the
        log, with additional info if the in_house argument was used.
        """

        multi_site = self._sites["multi_site"]

        logging.info("\nSHOTGUN USAGE REPORT:\n")

        logging.info("Number of unique user accounts that logged in between %s: %s\n" % (
            multi_site["date_range"],
            multi_site["num_logged_in_users"]),
        )

        logging.info(
            "Total number of user accounts with Status currently \"Active\": %s\n" %
            multi_site["num_active_users"],
        )

        logging.info("Shotgun Sites:\n%s\n" % "\n".join(multi_site["sites"]))

        if self._in_house:
            logging.info(
                "Unique user accounts that logged in between %s:\n%s\n" % (
                    multi_site["date_range"],
                    "\n".join(multi_site["logged_in_users"])
                )
            )
            logging.info("User accounts with Status currently \"Active\":\n%s\n" % "\n".join(multi_site["active_users"]))


if __name__ == "__main__":
    """
    Handles command-line interface and passes args to the Report class.
    """

    # Initialize a command-line argument parser.
    parser = argparse.ArgumentParser(
        description=_DESCRIPTION
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
        "-d",
        "--display",
        help="Display the report, assuming a report.json file is present.",
        action="store_true",
        required=False,
    )
    parser.add_argument(
        "-i",
        "--in_house",
        help="Display a more detailed report for in-house purposes.",
        action="store_true",
        required=False,
    )

    # Print script usage if no arguments are passed.
    if len(sys.argv) < 2:
        print "Usage: report.py --help"

    # Pass our command-line arguments to the Report class.
    else:
        args = vars(parser.parse_args())
        Report(
            args["generate"],
            args["start_date"],
            args["end_date"],
            args["in_house"],
            args["display"]
        )
