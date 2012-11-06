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

# format date method
def formatDate(dt):
    return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")

def urlquote(url, charset='UTF-8'):
    if isinstance(url, unicode):
        url = url.encode(charset, 'ignore')
    proto, rest = url.split(":", 1)
    return proto + ":" + urllib.quote(rest)

validExtensions = [".aac", ".m4a", ".mp4", ".mp3"]

# Overrides for file extensions that do not indicate the default item type
itemTypes = {
        ".aac": "audio/mp4",
        ".m4a": "audio/mp4",
        ".mp4": "audio/mp4",
        }

defaultItemType = "audio/mpeg"

# command line options
#    - python createRSFeed.py /path/to/podcast/files /path/to/output/rss [<Podcast title>]
# directory passed in
rootdir = sys.argv[1]
# output RSS filename
outputFilename = sys.argv[2]

# constants
# the podcast name
try:
    rssTitle = sys.argv[3]
except:
    rssTitle = "Default podcast title"
# the podcast description
rssDescription = "The podcast description"
# the url where the podcast items will be hosted
rssSiteURL = "http://192.168.1.251/"
# the url of the folder where the items will be stored
rssItemURL = rssSiteURL + "recordings/"
# the url to the podcast html file
rssLink = rssSiteURL #+ ""
# url to the podcast image
rssImageUrl = rssSiteURL #+ "/logo.jpg"
# the time to live (in minutes)
rssTtl = "60"
# contact details of the web master
rssWebMaster = "me@me.com"


#record datetime started
now = datetime.datetime.now()



# Main program

# Construct the XML
xml = ET.ElementTree(ET.Element("rss", {"version": "2.0"}))

# Now populate the 'rss' element */

chan = ET.SubElement(xml.getroot(), "channel")

ET.SubElement(chan, "title").text = rssTitle
ET.SubElement(chan, "description").text = rssDescription
ET.SubElement(chan, "link").text = rssLink
ET.SubElement(chan, "ttl").text = rssTtl
ET.SubElement(chan, "copyright").text = "mart 2012"
ET.SubElement(chan, "lastBuildDate").text = formatDate(now)
ET.SubElement(chan, "pubDate").text = formatDate(now)
ET.SubElement(chan, "webMaster").text = rssWebMaster

image = ET.SubElement(chan, "image")
imageUrl = ET.SubElement(image, "url")
imageUrl.text = urlquote(rssImageUrl)
ET.SubElement(image, "title").text = rssTitle
ET.SubElement(image, "link").text = rssLink

# walk through all files and subfolders
for path, subFolders, files in os.walk(rootdir):
    for f in files:
        # split the file based on "." we use the first part as the title and the extension to work out the media type
        basename, ext = os.path.splitext(f)
        # get the full path of the file
        fullPath = os.path.join(path, f)
        # get the stats for the file
        fileStat = os.stat(fullPath)
        # find the path relative to the starting folder, e.g. /subFolder/file
        relativePath = os.path.relpath(fullPath, os.path.dirname(outputFilename))
        print relativePath

        if not ext in validExtensions:
            continue

        audioTags = mutagen.File(fullPath, easy=True)
        print audioTags.pprint()

        try:
            fileTitle = audioTags["title"][0]
        except KeyError:
            fileTitle = "Unknown"
        print fileTitle

        try:
            fileDate = audioTags["date"][0]
            print fileDate
            try:
                fileTimeStamp = datetime.datetime.strptime(fileDate, "%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                fileTimeStamp = datetime.datetime.fromtimestamp(os.path.getmtime(fullPath))
                print "Unable to parse date from meta-data; falling back to", fileTimeStamp
        except KeyError:
            fileTimeStamp = datetime.datetime.now()
        print fileTimeStamp
        print formatDate(fileTimeStamp)

        try:
            fileDesc = audioTags["comment"][0]
        except KeyError:
            fileDesc = "No comment"

        # Add the item to the RSS XML
        item = ET.SubElement(chan, "item")
        ET.SubElement(item, "title").text = fileTitle
        ET.SubElement(item, "description").text = fileDesc
        ET.SubElement(item, "link").text = urlquote(rssItemURL + relativePath)
        ET.SubElement(item, "guid").text = urlquote(rssItemURL + relativePath)
        ET.SubElement(item, "pubDate").text = formatDate(fileTimeStamp)
        ET.SubElement(item, "enclosure", {
            "url": urlquote(rssItemURL + relativePath),
            "length": str(fileStat[ST_SIZE]),
            "type": itemTypes.get(ext, defaultItemType)
            })
        
        candidate = os.path.join(path, basename + ".jpg")
        if os.path.isfile(candidate):
            print candidate
            imageUrl.text = urllib.quote(os.path.splitext(relativePath)[0] + '.jpg')
    #end for loop
#end for loop

# Write the XML
xml.write(outputFilename, "UTF-8")

print "complete"

