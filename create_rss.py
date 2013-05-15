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
import mutagen
import urllib
import xml.etree.ElementTree as ET
from textwrap import TextWrapper

def print_diag(level, value, linefeed = True):
    if level < config.verbosity:
        if level == CRITICAL:
            print "***",
        try:
            # If unicode, convert to UTF-8 string
            value = value.encode("utf-8", "replace")
        except:
            pass
        try:
            print str(value),
        except UnicodeEncodeError:
            # OK, failed to output a UTF-8 string so try plain ASCII
            value = value.encode("ascii", "replace")
            print str(value),
        if linefeed:
            print

# format date method
def formatDate(dt):
    return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")

# A quick and dirty function to produce a 'safe' version the
# the URL for embedding in the RSS feed
def urlquote(url, *bits, **kwds):
    try:
        charset = kwds["charset"]
        del kwds["charset"]
    except KeyError:
        charset = "UTF-8"
    assert len(kwds) == 0, "Unrecognised keyword parameters"
    for bit in bits:
        if url[-1] != '/' and bit[0] != '/':
            url += '/'
        url += bit
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

def MP4_process_tags(mp4tags, mTime):
    tags = {
        "title" : "Unknown title",
        "album" : "Unknown album",
        "date" : datetime.datetime.fromtimestamp(mTime),
        "comment" : "No comment",
    }
    copyright = "\xa9"
    
    try:
        tags["title"] = mp4tags[copyright + "nam"][0]
    except KeyError:
        print_diag(IMPORTANT, "Unable to determine title from metadata")

    try:
        tags["album"] = mp4tags[copyright + "alb"][0]
    except KeyError:
        print_diag(IMPORTANT, "Unable to determine album from metadata")

    try:
        fileDate = mp4tags[copyright + "day"][0]
        try:
            # If unicode, convert to regular string
            fileDate = fileDate.encode('utf-8')
        except:
            pass
        fileTimeStamp = datetime.datetime.strptime(fileDate, "%Y-%m-%dT%H:%M:%SZ")
        tags["date"] = fileTimeStamp
    except (KeyError, ValueError):
        print_diag(IMPORTANT, "Unable to parse date from meta-data; falling back to %s" % tags["date"])

    try:
        tags["comment"] = mp4tags[copyright + "cmt"][0]
    except KeyError:
        print_diag(INFOMATION, "Unable to determine description from metadata")

    return tags

def MP3_process_tags(mp3tags, mTime):
    tags = {
        "title" : "Unknown title",
        "album" : "Unknown album",
        "date" : datetime.datetime.fromtimestamp(mTime),
        "comment" : "No comment",
    }

    try:
        tags["title"] = mp3tags["TIT2"].text[0]
    except KeyError:
        print_diag(IMPORTANT, "Unable to determine title from metadata")

    try:
        tags["album"] = mp3tags["TALB"].text[0]
    except KeyError:
        print_diag(IMPORTANT, "Unable to determine album from metadata")

    try:
        fileDate = mp3tags["TDRC"].text[0]
        try:
            # If unicode, convert to regular string
            fileDate = fileDate.encode('utf-8')
        except:
            pass
        fileTimeStamp = datetime.datetime.strptime(fileDate, "%Y-%m-%dT%H:%M:%SZ")
        tags["date"] = fileTimeStamp
    except (KeyError, ValueError):
        print_diag(IMPORTANT, "Unable to parse date from meta-data; falling back to %s" % tags["date"])

    for k in mp3tags.keys():
        if k.startswith("COMM"):
            tags["comment"] = mp3tags[k].text[0]
            break
    else:
        print_diag(INFOMATION, "Unable to determine description from metadata")

    return tags

# The mutagen "easy mode" doesn't work with some tag formats so this, with the functions above,
# replicates it but gives us the ability to work with the tags that we may get...
tagTypes = {
    "MP4": MP4_process_tags,
    "MP3": MP3_process_tags,
    }

CRITICAL, IMPORTANT, INFOMATION, DEBUG, EXTRA_DEBUG = range(5)

defaults = {
    "source": (None, "String (required) - The directory containing content for this feed"),
    "sourceUrl": (None, "String (required) - The URL for the 'source' directory on the internet"),
    "rssFile": (None, "String (required) - The RSS (i.e. XML) file to produce"),
    "rssTitle": ("Random podcast title", "String - The RSS feed title"),
    "rssLink": ("http://www.example.com/", "String - The website corresponding to the RSS feed"),
    "rssDescription": ("Random podcast description", "String - The RSS feed description"),
    "rssTtl": (60, "Integer - How long (in minutes) a feed can be cached before being refreshed"),
    "maxAge": (None, "Integer - The max age, indays, for items to be included in the RSS feed"),
    "deleteOld": (False, "Boolean - Whether files older than 'maxAge' should be deleted"),
    "deleteAllOld": (False, "Boolean - If 'maxAge' is set and 'deleteOld' is True, deletes all old files not just audio files"),
    "episodeTitle": ("%(title)s", "String - The string format to use for the title of each episode. Available attributes are 'title', 'album' and 'comment'"),
    "verbosity": (2, "Integer (0-5) - Amount of information to output. 0 results in no output"),
}

class ConfigOptionException(Exception): pass

class BadConfigOptionException(ConfigOptionException): pass
class ConfigOptionNotSetException(ConfigOptionException): pass

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
        try:
            return self._config[attr]
        except KeyError:
            if attr in self._defaults.keys():
                raise ConfigOptionNotSetException("'%s' has not be set" % attr)
            else:
                raise BadConfigOptionException("'%s' is not a valid configuration option" % attr)

    def __str__(self):
        return str(self._config)

config = Config(defaults)

if len(sys.argv) != 2:
    textWrapper = TextWrapper(initial_indent = "    ", width = 78)
    print >> sys.stderr, """Usage: %s <config file>

The config file is a python script setting some or all of the following variables:
""" % sys.argv[0]
    for k, v in sorted(defaults.items()):
        print >> sys.stderr, "  " + k + ":"
        o = v[1].find("-")
        if o < 0:
            textWrapper.subsequent_indent = "        "
        else:
            textWrapper.subsequent_indent = " " * (6 + o)
        print >> sys.stderr, "\n".join(textWrapper.wrap(v[1]))
        if v[0] is not None:
            print >> sys.stderr, "      Default:", repr(v[0])
    sys.exit()
else:
    config(sys.argv[1])

xml, chan = create_rss_channel(config)

# walk through all files and subfolders
for path, subFolders, files in os.walk(config.source):
    for f in files:
        # We use the extension to work out the media type
        ext = os.path.splitext(f)[1]
        # Get the full path of the file
        fullPath = os.path.join(path, f)
        # find the path relative to the starting folder, e.g. /subFolder/file
        relativePath = os.path.relpath(fullPath, config.source)
        print_diag(INFOMATION, relativePath)

        try:
            config.maxAge # Test for this option having been set
            mTime = datetime.datetime.fromtimestamp(os.path.getmtime(fullPath))
            timediff = datetime.datetime.now() - mTime
            if timediff.days > config.maxAge:
                print_diag(DEBUG, "%s is older than maxAge" % f)
                if config.deleteOld and (ext in fileTypes.keys() or config.deleteAllOld):
                    # This is an old audio file and we've been told to delete it
                    print_diag(IMPORTANT, "%s is older than maxAge - deleting" % f)
                    os.remove(fullPath)
                continue
        except ConfigOptionNotSetException:
            pass

        if not ext in fileTypes.keys():
            continue
        try:
            audioTags = mutagen.File(fullPath)
        except Exception, e:
            print_diag(CRITICAL, "Got Mutagen exception for '%s': " % fullPath + str(e))
            continue
        print_diag(INFOMATION, "Tag class: " + audioTags.__class__.__name__)
        print_diag(INFOMATION, audioTags.pprint())

        try:
            tags = tagTypes[audioTags.__class__.__name__](audioTags, os.path.getmtime(fullPath))
        except KeyError:
            print_diag(CRITICAL, "Unable to process tag class " + audioTags.__class__.__name__)
            continue


        print_diag(INFOMATION, tags["title"])
        print_diag(INFOMATION, tags["album"])
        print_diag(INFOMATION, tags["date"])
        print_diag(INFOMATION, tags["comment"])

        # Add the item to the RSS XML
        url = urlquote(config.sourceUrl, relativePath)

        item = ET.SubElement(chan, "item")
        ET.SubElement(item, "title").text = config.episodeTitle % tags
        ET.SubElement(item, "description").text = tags["comment"]
        ET.SubElement(item, "link").text = url
        ET.SubElement(item, "guid").text = url
        ET.SubElement(item, "pubDate").text = formatDate(tags["date"])
        ET.SubElement(item, "enclosure", {
            "url": url,
            "length": str(os.path.getsize(fullPath)),
            "type": fileTypes[ext],
            })
        
    #end for loop
#end for loop

# Write the XML
xml.write(config.rssFile, "UTF-8")

print_diag(EXTRA_DEBUG, "complete")

