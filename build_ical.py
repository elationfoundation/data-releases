#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# This file is part of data-releases, a listing of public data releases by federal agencies.
# Copyright © 2016 seamus tuohy, <s2e (at) seamustuohy.com>
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the included LICENSE file for details.

import argparse
import csv
from datetime import datetime
from icalendar.cal import Calendar, Event
from icalendar import vDatetime
from collections import namedtuple
from os import walk, path
from tempfile import NamedTemporaryFile
import iso8601
from iso8601 import ParseError
from urllib.parse import urlparse

import logging
logging.basicConfig(level=logging.ERROR)
log = logging.getLogger(__name__)


def get_release_list(list_path):
    with open(list_path, 'r') as csvfile:
        reader= csv.reader(csvfile, delimiter=',', quotechar='"')
        csvlist = list(reader)
    return csvlist

def write_csv_file(release_table, csv_path):
    with open(csv_path, 'w+') as csvfile:
        csvw = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        csvw.writerow("name", "date", "desription", "agency_name",
                      "url", "contact_name", "contact_email")
        for entry in release_table:
            csvw.writerow(entry)

def get_release_csvs(folder_path):
    files_to_merge = []
    for dir_name, subdir_name, file_list in walk(folder_path):
        for filename in file_list:
            extension = path.splitext(filename)[1]
            if extension == ".csv":
                full_path = path.join(dir_name, filename)
                files_to_merge.append(full_path)
    if files_to_merge == []:
        raise OSError("There are no CSV files in the directory specified.")
    else:
        return files_to_merge


def merge_folder(folder_path, merged_path):
    files_to_merge  = get_release_csvs(folder_path)
    merged_releases = []
    headers = None
    for release in files_to_merge:
        # Get release without the header information
        rel_list = get_release_list(release)
        if headers == None:
            headers = rel_list[0]
            merged_releases += headers
        if rel_list[0] == headers:
            merged_releases += rel_list[1:]
        else:
            raise ValueError("Error at file {0}".format(release) +
                             "CSV's have different headers " +
                             "Cannot merge inconsistant CSV's")
    write_csv_file(merged_releases, merged_path)


def make_dataset(release):
    """
    column_order = [ "name", # 0
            "date", # 1
            "desription", # 2
            "agency_name", # 3
            "url", # 4
            "contact_name", # 5
            "contact_email"] # 6
    """
    #print(release)
    dataset = Dataset()
    try:
        dataset.title = release[0]
        # Set the temporal range to be the release date twice
        # We can add the end date later if desired
        dataset.temporal = (release[1], release[1])
        dataset.description = release[2]
        dataset.publisher = {"name":release[3]}
        dataset.distribution = {"downloadURL": release[4]}
        dataset.contactPoint = {"fn":release[5], "hasEmail":release[6]}
    except ValueError as _e:
        raise ValueError(_e)
    return dataset


def build_event(release):
    event = Event()
    try:
        # This is where we actually decide what we care about.
        dataset = make_dataset(release)
        event['summary'] = dataset.title
        event['dtstart'] = dataset.temporal.start
        event['url'] = dataset.distribution.downloadURL
        event['organizer'] = dataset.publisher.name
        #"CN={0}".format(dataset.publisher.name)
        event['contact'] = "CN={0}:mailto:{1}".format(dataset.contactPoint.fn,
                                                      dataset.contactPoint.hasEmail)
        event['description'] = dataset.description
    except ValueError as _e:
            log.info("Cannot build event. Invalid fields present.")
            raise ValueError(_e)
    return event


def write_ical(releases, ical_path):
    release_cal = Calendar()
    for release in releases:
        try:
            event = build_event(release)
            release_cal.add_component(event)
        except ValueError as _e:
            log.debug(_e)
            log.warn("Release event {0} could not be added ".format(release[0]) +
                     "to the ical event.")

    with open(ical_path, "wb+") as ical_file:
        ical_file.write(release_cal.to_ical())


def main():
    args = parse_arguments()
    set_logging(args.verbose, args.debug)
    temp_file = None
    if args.merge_folder:
        temp_file = NamedTemporaryFile()
        merge_folder(args.list_path, temp_file.name)
        release_path = temp_file.name
    else:
        release_path = args.list_path

        releases = get_release_list(release_path)[1:]
    write_ical(releases, args.ical_path)
    if temp_file:
        temp_file.close()



class Dataset():
    def __init__(entry):
        pass

    @property
    def title(self):
        """I'm the 'title' property."""
        return self._title

    @title.setter
    def title(self, value):
        if isinstance(value, str):
            self._title = value
        else:
            raise ValueError("Not a string")

    @title.deleter
    def title(self):
        del self._title


    @property
    def description(self):
        """I'm the 'description' property."""
        return self._description

    @description.setter
    def description(self, value):
        if isinstance(value, str):
            self._description = value
        else:
            raise ValueError("Not a string")

    @description.deleter
    def description(self):
        del self._description

    @property
    def keyword(self):
        """I'm the 'keyword' property."""
        return self._keyword

    @description.setter
    def keyword(self, value):
        # https://project-open-data.cio.gov/v1.1/schema/#keyword
        if not isinstance(value, list):
            raise ValueError("Not a array of strings")
        else:
            for i in value:
                if not isinstance(i, str):
                    raise ValueError("Not a string")
        self._keyword = value


    @keyword.deleter
    def keyword(self):
        del self._keyword

    @property
    def publisher(self):
        """I'm the 'publisher' property."""
        return self._publisher

    @publisher.setter
    def publisher(self, values):
        # https://project-open-data.cio.gov/v1.1/schema/#publisher
        # TODO Should stub out to another class
        # But I am not doing that
        self._publisher = Publisher(values)

    @publisher.deleter
    def publisher(self):
        del self._publisher

    @property
    def contactPoint(self):
        """I'm the 'contactPoint' property."""
        return self._contactPoint

    @contactPoint.setter
    def contactPoint(self, values):
        # https://project-open-data.cio.gov/v1.1/schema/#contactPoint
        self._contactPoint = ContactPoint(values)

    @contactPoint.deleter
    def contactPoint(self):
        del self._contactPoint

    @property
    def identifier(self):
        """I'm the 'identifier' property."""
        return self._identifier

    @identifier.setter
    def identifier(self, value):
        # https://project-open-data.cio.gov/v1.1/schema/#identifier
        if isinstance(value, str):
            self._identifier = value
        else:
            raise ValueError("Not a string")


    @identifier.deleter
    def identifier(self):
        del self._identifier

    @property
    def bureauCode(self):
        """I'm the 'bureauCode' property."""
        return self._bureauCode

    @bureauCode.setter
    def bureauCode(self, value):
        # https://project-open-data.cio.gov/v1.1/schema/#bureauCode
        if not isinstance(value, list):
            raise ValueError("Not a array of strings")
        else:
            for i in value:
                if not isinstance(i, str):
                    raise ValueError("Not a string")
        self._bureauCode = value


    @bureauCode.deleter
    def bureauCode(self):
        del self._bureauCode

    @property
    def programCode(self):
        """I'm the 'programCode' property."""
        return self._programCode

    @programCode.setter
    def programCode(self, value):
        # https://project-open-data.cio.gov/v1.1/schema/#programCode
        if not isinstance(value, list):
            raise ValueError("Not a array of strings")
        else:
            for i in value:
                if not isinstance(i, str):
                    raise ValueError("Not a string")
        self._programCode = value

    @programCode.deleter
    def programCode(self):
        del self._programCode

    @property
    def license(self):
        """I'm the 'license' property."""
        return self._license

    @license.setter
    def license(self, value):
        # https://project-open-data.cio.gov/v1.1/schema/#licenes
        if isinstance(value, str):
            self._license = value
        else:
            raise ValueError("Not a string")

    @license.deleter
    def license(self):
        del self._license

    @property
    def rights(self):
        """I'm the 'rights' property."""
        return self._rights

    @rights.setter
    def rights(self, value):
        # https://project-open-data.cio.gov/v1.1/schema/#rights
        if isinstance(value, str):
            self._rights = value
        else:
            raise ValueError("Not a string")

    @rights.deleter
    def rights(self):
        del self._rights

    @property
    def spatial(self):
        """I'm the 'spatial' property."""
        return self._spatial

    @spatial.setter
    def spatial(self, value):
        """ This field should contain one of the following types of content: (1) a bounding coordinate box for the dataset represented in latitude / longitude pairs where the coordinates are specified in decimal degrees and in the order of: minimum longitude, minimum latitude, maximum longitude, maximum latitude; (2) a latitude / longitude pair (in decimal degrees) representing a point where the dataset is relevant; (3) a geographic feature expressed in Geography Markup Language using the Simple Features Profile; or (4) a geographic feature from the GeoNames database."""
        # https://project-open-data.cio.gov/v1.1/schema/#spatial
        # TODO: This needs a class and I am not doing it.
        self._spatial = value

    @spatial.deleter
    def spatial(self):
        del self._spatial

    @property
    def temporal(self):
        """I'm the 'temporal' property."""
        return self._temporal

    @temporal.setter
    def temporal(self, values):
        # https://project-open-data.cio.gov/v1.1/schema/#temporal
        date_pair = namedtuple("temporal", ["start", "end"])
        try:
            #print(str(values[0]))
            date_pair.start = vDatetime(iso8601.parse_date(values[0]))
            #print(values[1])
            date_pair.end = vDatetime(iso8601.parse_date(values[1]))
        except ParseError:
            raise ValueError("One of the date strings {0} or {1} is not parsable".format(values[0],
                                                                                         values[1]))
        self._temporal = date_pair

    @temporal.deleter
    def temporal(self):
        del self._temporal

    @property
    def distribution(self):
        """I'm the 'distribution' property."""
        return self._distribution

    @distribution.setter
    def distribution(self, value):
        # https://project-open-data.cio.gov/v1.1/schema/#distribution
        # TODO this needs a class
        # See distribution class
        self._distribution = Distribution(value)

    @distribution.deleter
    def distribution(self):
        del self._distribution

    @property
    def accrualPeriodicity(self):
        """I'm the 'accrualPeriodicity' property."""
        return self._accrualPeriodicity

    @accrualPeriodicity.setter
    def accrualPeriodicity(self, value):
        # https://project-open-data.cio.gov/v1.1/schema/#accrualPeriodicity
        # TODO ISO 8601 Repeating Duration (or irregular)
        self._accrualPeriodicity = value

    @accrualPeriodicity.deleter
    def accrualPeriodicity(self):
        del self._accrualPeriodicity

    @property
    def conformsTo(self):
        """I'm the 'conformsTo' property."""
        return self._conformsTo

    @conformsTo.setter
    def conformsTo(self, value):
        # https://project-open-data.cio.gov/v1.1/schema/#conformsTo
        is_uri(value)
        self._conformsTo = value

    @conformsTo.deleter
    def conformsTo(self):
        del self._conformsTo

    @property
    def dataQuality(self):
        """I'm the 'dataQuality' property."""
        return self._dataQuality

    @dataQuality.setter
    def dataQuality(self, value):
        # https://project-open-data.cio.gov/v1.1/schema/#dataQuality
        if isinstance(value, bool):
            self._dataQuality = value
        else:
            raise ValueError("Not a boolean value")

    @dataQuality.deleter
    def dataQuality(self):
        del self._dataQuality

    @property
    def describedBy(self):
        """I'm the 'describedBy' property."""
        return self._describedBy

    @describedBy.setter
    def describedBy(self, value):
        # https://project-open-data.cio.gov/v1.1/schema/#describedBy
        is_url(value)
        self._describedBy = value

    @describedBy.deleter
    def describedBy(self):
        del self._describedBy

    @property
    def describedByType(self):
        """I'm the 'describedByType' property."""
        return self._describedByType

    @describedByType.setter
    def describedByType(self, value):
        # https://project-open-data.cio.gov/v1.1/schema/#describedByType
        is_url(value)
        self._describedByType = value

    @describedByType.deleter
    def describedByType(self):
        del self._describedByType

    @property
    def isPartOf(self):
        """I'm the 'isPartOf' property."""
        return self._isPartOf

    @isPartOf.setter
    def isPartOf(self, value):
        # https://project-open-data.cio.gov/v1.1/schema/#isPartOf
        if isinstance(value, str):
            self._isPartOf = value
        else:
            raise ValueError("Not a string")

    @isPartOf.deleter
    def isPartOf(self):
        del self._isPartOf

    @property
    def language(self):
        """I'm the 'language' property."""
        return self._language

    @language.setter
    def language(self, value):
        # https://project-open-data.cio.gov/v1.1/schema/#language
        if not isinstance(value, list):
            raise ValueError("Not a array of strings")
        else:
            for i in value:
                if not isinstance(i, str):
                    raise ValueError("Not a string")
        self._language = value

    @language.deleter
    def language(self):
        del self._language

    @property
    def landingPage(self):
        """I'm the 'landingPage' property."""
        return self._landingPage

    @landingPage.setter
    def landingPage(self, value):
        # https://project-open-data.cio.gov/v1.1/schema/#landingPage
        if isinstance(value, str):
            self._landingPage = value
        else:
            raise ValueError("Not a string")

    @landingPage.deleter
    def landingPage(self):
        del self._landingPage

    @property
    def primaryITinvestmentUII(self):
        """I'm the 'primaryITinvestmentUII' property."""
        return self._primaryITinvestmentUII

    @primaryITinvestmentUII.setter
    def primaryITInvestmentUII(self, value):
        # https://project-open-data.cio.gov/v1.1/schema/#primaryITInvestmentUII
        self._primaryITinvestmentUII = value

    @primaryITinvestmentUII.deleter
    def primaryITinvestmentUII(self):
        del self._primaryITinvestmentUII

    @property
    def references(self):
        """I'm the 'references' property."""
        return self._references

    @references.setter
    def references(self, value):
        # https://project-open-data.cio.gov/v1.1/schema/#references
        if not isinstance(value, list):
            raise ValueError("Not a array of strings")
        else:
            for i in value:
                if not isinstance(i, str):
                    raise ValueError("Not a string")
        self._references = value

    @references.deleter
    def references(self):
        del self._references

    @property
    def systemOfRecords(self):
        """I'm the 'systemOfRecords' property."""
        return self._systemOfRecords

    @systemOfRecords.setter
    def systemOfRecords(self, value):
        # https://project-open-data.cio.gov/v1.1/schema/#systemOfRecords
        if isinstance(value, str):
            self._systemOfRecords = value
        else:
            raise ValueError("Not a string")

    @systemOfRecords.deleter
    def systemOfRecords(self):
        del self._systemOfRecords

    @property
    def theme(self):
        """I'm the 'theme' property."""
        return self._theme

    @theme.setter
    def theme(self, value):
        # https://project-open-data.cio.gov/v1.1/schema/#theme
        if not isinstance(value, list):
            raise ValueError("Not a array of strings")
        else:
            for i in value:
                if not isinstance(i, str):
                    raise ValueError("Not a string")
        self._theme = value

    @theme.deleter
    def theme(self):
        del self._theme

class Distribution():

    def __init__(self, values):
        self.downloadURL = values["downloadURL"]

    @property
    def accessURL(self):
        """I'm the 'accessURL' property."""
        return self._accessURL

    @accessURL.setter
    def accessURL(self, value):
        is_url(value)
        self._accessURL = value

    @accessURL.deleter
    def accessURL(self):
        del self._accessURL

    @property
    def conformsTo(self):
        """I'm the 'conformsTo' property."""
        return self._conformsTo

    @conformsTo.setter
    def conformsTo(self, value):
        is_uri(value)
        self._conformsTo = value

    @conformsTo.deleter
    def conformsTo(self):
        del self._conformsTo

    @property
    def describedByType(self):
        """I'm the 'describedByType' property."""
        return self._describedByType

    @describedByType.setter
    def describedByType(self, value):
        # https://project-open-data.cio.gov/v1.1/schema/#dataset-describedByType
        if isinstance(value, str):
            self._describedByType = value
        else:
            raise ValueError("Not a string")

    @describedByType.deleter
    def describedByType(self):
        del self._describedByType

    @property
    def description(self):
        """I'm the 'description' property."""
        return self._description

    @description.setter
    def description(self, value):
        if isinstance(value, str):
            self._description = value
        else:
            raise ValueError("Not a string")

    @description.deleter
    def description(self):
        del self._description

    @property
    def downloadURL(self):
        """I'm the 'downloadURL' property."""
        return self._downloadURL

    @downloadURL.setter
    def downloadURL(self, value):
        is_url(value)
        self._downloadURL = value

    @downloadURL.deleter
    def downloadURL(self):
        del self._downloadURL

    @property
    def format(self):
        """I'm the 'format' property."""
        return self._format

    @format.setter
    def format(self, value):
        if isinstance(value, str):
            self._format = value
        else:
            raise ValueError("Not a string")

    @format.deleter
    def format(self):
        del self._format

    @property
    def mediaType(self):
        """I'm the 'mediaType' property."""
        return self._mediaType

    @mediaType.setter
    def mediaType(self, value):
        if isinstance(value, str):
            self._mediaType = value
        else:
            raise ValueError("Not a string")

    @mediaType.deleter
    def mediaType(self):
        del self._mediaType

    @property
    def title(self):
        """I'm the 'title' property."""
        return self._title

    @title.setter
    def title(self, value):
        if isinstance(value, str):
            self._title = value
        else:
            raise ValueError("Not a string")

    @title.deleter
    def title(self):
        del self._title


class ContactPoint():
    def __init__(self, values):
        self.fn = values["fn"]
        self.hasEmail = values["hasEmail"]

    @property
    def fn(self):
        """I'm the 'fn' property."""
        return self._fn

    @fn.setter
    def fn(self, value):
        self._fn = value

    @fn.deleter
    def fn(self):
        del self._fn

    @property
    def hasEmail(self):
        """I'm the 'hasEmail' property."""
        return self._hasEmail

    @hasEmail.setter
    def hasEmail(self, value):
        self._hasEmail = value

    @hasEmail.deleter
    def hasEmail(self):
        del self._hasEmail

class Publisher():

    def __init__(self, values):
        self.name = values["name"]

    @property
    def name(self):
        """I'm the 'name' property."""
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @name.deleter
    def name(self):
        del self._name

class Spatial():
    def __init__(self):
        raise NotImplementedError("Not implemented")

def is_uri(value):
    if urlparse(value).path != "":
        return True

def is_url(value):
    if urlparse(value).path != "":
        return True

# Command Line Functions below this point

def set_logging(verbose=False, debug=False):
    if debug == True:
        log.setLevel("DEBUG")
    elif verbose == True:
        log.setLevel("INFO")

def parse_arguments():
    parser = argparse.ArgumentParser("Get a summary of some text")
    parser.add_argument("--verbose", "-v",
                        help="Turn verbosity on",
                        action='store_true')
    parser.add_argument("--debug", "-d",
                        help="Turn debugging on",
                        action='store_true')
    parser.add_argument("--list_path", "-l",
                        help="Path to CSV listing of public data releases by federal agencies",
                        default="./releases.csv")
    parser.add_argument("--ical_path", "-i",
                        help="Path where ical file should be written.",
                        default="./releases.ical")
    parser.add_argument("--merge_folder", "-m",
                        help="Path to folder to merge."
                        "If the parser should merge all CSV's in a folder into a single file")
    args = parser.parse_args()
    return args

def usage():
    print("TODO: usage needed")

if __name__ == '__main__':
    main()
