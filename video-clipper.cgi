#!/usr/bin/perl -w
# Simple Video Clipper
# Given a video available over HTTP, allow the user specify a start and duration,
# and return a video clip of that for download.
# 
# Eugene Wong <ewong@internap.com>

use strict;
use CGI qw(:standard);
use File::Temp;

my $baseurl = "http://127.0.0.1/";
my $ffmpeg  = "/usr/bin/ffmpeg";
my $cache   = "/usr/cache/video-clipper";
my $bufsize = 65536;
my $check_restrictions = 1;   # Whether to restrict to certain accounts
my $debug = 0;
my $tempfile;

# restrict usage only to these accounts
my @restrictions = (
  "ewong",
  "metaint"
);

$SIG{TERM} = sub {
  if(defined($tempfile) && -f $tempfile) {
    unlink $tempfile;
  }
  exit;
};

# You'll need mod_rewrite and something like this in your config if you
# want to be able to use an URL like this:
# http://host/path/to/file.mp4?start=300&duration=10
#
# RewriteEngine On
# RewriteCond %{QUERY_STRING} ^(.*)$ [NC]
# RewriteRule ^(.+) /cgi-bin/cutter.cgi?src=$1&%1 [NC,L]

$baseurl = $baseurl."/" if ($baseurl !~ m,/$,);
$cache   = $cache."/"   if ($cache   !~ m,/$,);

# parse query string.  force all keys to lowercase.
my @querypairs = split(/&/, $ENV{QUERY_STRING});
my %params;

foreach my $pair (@querypairs) {
  my ($key, $value) = split(/=/, $pair);
  $key =~ tr/A-Z/a-z/;
  $params{$key} = $value;
}

# permitted query keys:
# - src (path)
# - start (seconds)
# - duration (seconds, optional.  Just go to end of video if not specified.)
# The ones we don't understand are ignored.

# some stupid error detection junk
my $error = 0;

if (defined($params{start})) {
  $error = 1 if ($params{start} !~ /^\d+$/);
} else {
  $error = 1;
}

if (defined($params{duration})) {
  $error = 1 if ($params{duration} !~ /^\d+$/);
}

if (defined($params{src})) {
  $error = 1 if ($params{src} !~ /^[\w\-\/\.]+$/);
  $error = 1 if ($params{src} !~ /\.mp4$/);
} else {
  $error = 1;
}

if ($error) {
  print header(
    -type   => 'text/plain',
    -status => '405 Method Not Allowed' );
  print "405 Method Not Allowed.\n";
  print "$ENV{QUERY_STRING}\n" if $debug;
  exit 1;
}

# Check to see if these accounts are allowed
if ($check_restrictions) {
  my $okay = 0;
  foreach my $account (@restrictions)  {
    $okay = 1 if ($params{src} =~ m,^$account/,);
  }
  if (!$okay) {
    print header(
      -type   => 'text/plain',
      -status => '403 Access Denied' );
    print "403 Access Denied.\n";
    print "$ENV{QUERY_STRING}\n" if $debug;
    exit 1;
  }
}

# Making our new filename.  Assuming foo.mp4...
# if start is 10 and duration is 300, then foo-10-300.mp4
# if start is 10 and there's no duration, then foo-10.mp4
my @junk = split(/\//, $params{src});
my $name = $junk[-1];
$name =~ s/\.mp4$//g;
$name = $name."-".$params{start};
if (defined($params{duration})) {
  $name = $name."-".$params{duration};
}
$name = $name.".mp4";

# tmpnam() is not great, we basically just use that to generate a temporary
# filename, then change it to our cache directory.  The cache directory probably
# should be a tmpfs directory to keep things speed.
my $count = 0;
do {
  $tempfile = tmpnam();
  $tempfile =~ s,^/tmp/,$cache,;
  $count++;
} while (-e $tempfile && $count < 5);

# Can't find a usable temp file after several tries.
if ( $count >= 5 ) {
  print header(
    -type   => 'text/plain',
    -status => '500 Internal Server Error' );
  print "500 Internal Server Error.\n";
  print STDERR "Can't identify a usable temp file: $ENV{QUERY_STRING}";
  exit 1;
}

my @cmd;
if ($params{duration}) {
  @cmd=("-y", "-ss", $params{start}, "-i", $baseurl.$params{src}, "-t", $params{duration}, "-acodec", "copy", "-vcodec", "copy", "-f", "mp4", $tempfile);
} else {
  @cmd=("-y", "-ss", $params{start}, "-i", $baseurl.$params{src}, "-acodec", "copy", "-vcodec", "copy", "-f", "mp4", $tempfile);
}

if ($debug) {
  unshift @cmd, ($ffmpeg, "-loglevel", "info");
} else {
  unshift @cmd, ($ffmpeg, "-loglevel", "error");
}

print STDERR "Executing [".join(' ', @cmd)."]" if $debug;
system @cmd;

# if ffmpeg fails to run for any reason, return 404.
# Not much sense to look for different errors as long as we
# are logging what's going on.
if ($?) {
  print header(
    -type   => 'text/plain',
    -status => '404 Not Found' );
  print "404 Not Found.\n";
  print "$ENV{QUERY_STRING}\n" if $debug;
  print STDERR "ffmpeg failed on $ENV{QUERY_STRING}";
  unlink $tempfile if (-e $tempfile);
  exit 0;
}

# Open and serve up the temporary file that ffmpeg created.
my $fh;
$|=1;
unless (open $fh, "<", $tempfile) {
  # if we can't read the tempfile for some reason, return 503
  # and display an error message.
  print header(
    -type   => 'text/plain',
    -status => '503 Service Unavailable' );
  print "503 Service Unavailable\n";
  print "Error: $!\n" if $debug;
  print STDERR "Can't open $tempfile: $!";
  unlink $tempfile if (-e $tempfile);
  exit 1;
}

# read and display the tempfile ffmpeg generated.
print header (
  -type                           => "application/octet-stream",
  -attachment                     => $name,
  '-Cache-Control'                => "max-age=0; no-cache",
  '-Access-Control-Allow-Origin'  => "*" );

binmode ($fh);
my $buf;
while ( read($fh,$buf,$bufsize) ) {
  print $buf;
}

close $fh;
unlink $tempfile;
