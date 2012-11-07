#!/usr/bin/python
# update environment to handle Unicode
PYTHONIOENCODING="utf-8"

# Ideas:
# Function to check if file should be ignored. Only accept recognised files
# Check for existence of nfo file
# May be read details from nfo file?
# Move reading of tags into a function so can have different versions
# depending if reading nfo or audio file
# Name output rss by input file directory.rss if output file not provided
# or just provided as a directory.
# Overwrite existing rss file.


# import libraries
import os
import sys
import datetime
import time
import mutagen
import urllib
import xml.etree.ElementTree as ET

# import constants from stat library
from stat import * # ST_SIZE ST_MTIME

# import ID3 tag reader
from mutagen.id3 import ID3, ID3TimeStamp, TDRC
from time import strptime, strftime

def print_diag(level, value, linefeed = True):
    if level < config.verbosity:
        print str(value),
        if linefeed:
            print

# format date method
def formatDate(dt):
    return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")

# A quick and dirty function to produce a 'safe' version the
# the URL for embedding in the RSS feed
def urlquote(url, charset='UTF-8'):
    if isinstance(url, unicode):
        url = url.encode(charset, 'ignore')
    proto, rest = url.split(":", 1)
    return proto + ":" + urllib.quote(rest)

# A function to produce the RSS XML skeleton
# Returns a tuple of the whole XML and the channel element for population
def create_rss_channel(config):
    #record datetime started
    now = datetime.datetime.now()

    # Construct the XML
    xml = ET.ElementTree(ET.Element("rss", {"version": "2.0"}))

    # Now populate the 'rss' element */
    chan = ET.SubElement(xml.getroot(), "channel")

    ET.SubElement(chan, "title").text = config.rssTitle
    ET.SubElement(chan, "description").text = config.rssDescription
    ET.SubElement(chan, "link").text = config.rssLink
    ET.SubElement(chan, "ttl").text = str(config.rssTtl)
    ET.SubElement(chan, "lastBuildDate").text = formatDate(now)
    ET.SubElement(chan, "pubDate").text = formatDate(now)

    return xml, chan

# Ignore files unless they have one of these extensions and include the item type for each
fileTypes = {
        ".aac": "audio/mp4",
        ".m4a": "audio/mp4",
        ".mp4": "audio/mp4",
        ".mp3": "audio/mpeg",
}

CRITICAL, IMPORTANT, INFOMATION, DEBUG, EXTRA_DEBUG = range(5)

defaults = {
    "source": (None, "String (required) - The directory containing content for this feed"),
    "sourceUrl": (None, "String (required) - The URL for the 'source' directory on the internet"),
    "rssFile": (None, "String (required) - The RSS (i.e. XML) file to produce"),
    "rssTitle": ("Random podcast title", "String - The RSS feed title"),
    "rssLink": ("http://www.example.com/", "String - The website corresponding to the RSS feed"),
    "rssDescription": ("Random podcast description", "String - The RSS feed description"),
    "rssTtl": (60, "Integer - How long (in minutes) a feed can be cached before being refrshed"),
    "verbosity": (2, "Integer (0-5) - Amount of information to output. 0 results in no output"),
}

class Config(object):
    def __init__(self, defaults):
        self._defaults = defaults
        self._config = {}

    def __call__(self, filename):
        for k, v in self._defaults.items():
            self._config[k] = v[0]
        execfile(filename, {}, self._config)
        for k in self._config.keys():
            assert k in self._defaults.keys(), "'%s' is not a valid configuration option" % k
            if self._config[k] is None:
                del self._config[k]

    def __getattr__(self, attr):
        return self._config[attr]

    def __str__(self):
        return str(self._config)

config = Config(defaults)

if len(sys.argv) != 2:
    print >> sys.stderr, """Usage: %s <config file>

The config file is a python script setting some or all of the following variables:
""" % sys.argv[0]
    for k, v in sorted(defaults.items()):
        print >> sys.stderr, "  " + k + ":"
        print >> sys.stderr, "    " + v[1]
        if v[0] is not None:
            print >> sys.stderr, "      Default:", repr(v[0])
    sys.exit()
else:
    config(sys.argv[1])

xml, chan = create_rss_channel(config)

# walk through all files and subfolders
for path, subFolders, files in os.walk(config.source):
    for f in files:
        # split the file based on "." we use the first part as the title and the extension to work out the media type
        basename, ext = os.path.splitext(f)
        # get the full path of the file
        fullPath = os.path.join(path, f)
        # get the stats for the file
        fileStat = os.stat(fullPath)
        # find the path relative to the starting folder, e.g. /subFolder/file
        relativePath = os.path.relpath(fullPath, config.source)
        print_diag(INFOMATION, relativePath)

        if not ext in fileTypes.keys():
            continue

        audioTags = mutagen.File(fullPath, easy=True)
        print_diag(INFOMATION, audioTags.pprint())

        try:
            fileTitle = audioTags["title"][0]
        except KeyError:
            fileTitle = "Unknown"
        print_diag(INFOMATION, fileTitle)

        try:
            fileDate = audioTags["date"][0]
            print_diag(INFOMATION, fileDate)
            try:
                fileTimeStamp = datetime.datetime.strptime(fileDate, "%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                fileTimeStamp = datetime.datetime.fromtimestamp(os.path.getmtime(fullPath))
                print_diag(CRITICAL, "Unable to parse date from meta-data; falling back to %s" % fileTimeStamp)
        except KeyError:
            fileTimeStamp = datetime.datetime.now()
        print_diag(DEBUG, fileTimeStamp)
        print_diag(EXTRA_DEBUG, formatDate(fileTimeStamp))

        try:
            fileDesc = audioTags["comment"][0]
        except KeyError:
            fileDesc = "No comment"

        # Add the item to the RSS XML
        item = ET.SubElement(chan, "item")
        ET.SubElement(item, "title").text = fileTitle
        ET.SubElement(item, "description").text = fileDesc
        ET.SubElement(item, "link").text = urlquote(config.sourceUrl + relativePath)
        ET.SubElement(item, "guid").text = urlquote(config.sourceUrl + relativePath)
        ET.SubElement(item, "pubDate").text = formatDate(fileTimeStamp)
        ET.SubElement(item, "enclosure", {
            "url": urlquote(config.sourceUrl + relativePath),
            "length": str(fileStat[ST_SIZE]),
            "type": fileTypes[ext],
            })
        
    #end for loop
#end for loop

# Write the XML
xml.write(config.rssFile, "UTF-8")

print_diag(EXTRA_DEBUG, "complete")

