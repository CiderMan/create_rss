create_rss
==========

A simple application to take local audio files and create an RSS feed of podcasts for them
<pre>
$ python create_rss.py
Usage: create_rss.py &lt;config file&gt;

The config file is a python script setting some or all of the following variables:

  deleteAllOld:
    Boolean - If 'maxAge' is set and 'deleteOld' is True, deletes all old
              files not just audio files
      Default: False
  deleteOld:
    Boolean - Whether files older than 'maxAge' should be deleted
      Default: False
  episodeTitle:
    String - The string format to use for the title of each episode. Available
             attributes are 'title', 'album' and 'comment'
      Default: '%(title)s'
  maxAge:
    Integer - The max age, indays, for items to be included in the RSS feed
  rssDescription:
    String - The RSS feed description
      Default: 'Random podcast description'
  rssFile:
    String (required) - The RSS (i.e. XML) file to produce
  rssLink:
    String - The website corresponding to the RSS feed
      Default: 'http://www.example.com/'
  rssTitle:
    String - The RSS feed title
      Default: 'Random podcast title'
  rssTtl:
    Integer - How long (in minutes) a feed can be cached before being
              refreshed
      Default: 60
  source:
    String (required) - The directory containing content for this feed
  sourceUrl:
    String (required) - The URL for the 'source' directory on the internet
  verbosity:
    Integer (0-5) - Amount of information to output. 0 results in no output
      Default: 2
</pre>
