# video-clipper
This Perl CGI returns a portion of a MP4 video given a start timestamp and duration. It can be used with mod_rewrite.

It's been many years since I've written this, so these notes may not be 100% accurate.

## Why temp files?
As I recall, the reason we needed to use temporary files was because `ffmpeg` refused to write out mp4 files to a pipe. It has to do with `ffmpeg` wanting to seek back to the front of the file to update some headers. So, temp files it was. In our use case, we originally had it running on tmpfs, then later on disk. In either case it worked well and we never ran into any scaling issues due to this. So, we didn't do any optimizations on that front.

## Why weren't we caching these?
We were dealing with a relatively large amount of very long tail content. It was more important for us to keep as much of the working set of videos in the intermediate cache rather than to dilute it with these. We also expected the cache hit rate to be low with these clips. In that case, deleting these as quickly as possible was probably better.

We are also fetching the source viedos from the intermediate cache itself at `127.0.0.1`. So, if for some reason the source video wasn't in cache, it will be once this runs.

## Account restriction
The `@restrictions` array and the `check_restrictions` stuff can be gutted. I threw that in mostly because I wasn't sure how heavy this was going to be. The path style was bit specific to how the platform is setup and not particularly portable to other environment. 