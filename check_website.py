#! /usr/bin/python
import json
from pprint import pprint
import subprocess
from subprocess import PIPE 
import sys, os
from datetime import datetime
#import datetime, date
import argparse
import requests
import httplib
import time
import socket
import urllib2
import re

parser = argparse.ArgumentParser()
parser.add_argument("-H", help="website url", required=True)
parser.add_argument("-w", help="set the warning ", type=float)
parser.add_argument("-c", help="set the critical", type=float)
parser.add_argument("-u", help="set website uri")
parser.add_argument("-pw", help="set packet loss warning limit, default is 50%")
parser.add_argument("-pc", help="set packet loss critical limit, default is 90%")
parser.add_argument("-dw", help="set dns resolution warning limit, default is 1s")
parser.add_argument("-dc", help="set dns resolution critical limit, default is 2s")
args = parser.parse_args()
 
hostname = args.H

dns_start = time.time()
ip_address = socket.gethostbyname(hostname)
dns_end = time.time()
#setting up variable overrides
if args.pw:
    pl_w= args.pw
else:
    pl_w = 50

if args.pc:
   pl_c = args.pc
else:
   pl_c = 90

if args.dw:
   dns_w = args.dw
else:
   dns_w = 1

if args.dc:
    dns_c = args.dc
else:
    dns_c = 2


if args.u:
    url = "http://" + args.H + "/" + args.u
else:
    url = "http://" + args.H + "/"

#print url
#path to phantomjs binary
path = '/usr/bin/phantomjs'
#path to netsniff.js tool
pathjs = '/usr/local/nagios/libexec/netsniff.js'

process = subprocess.Popen([path, '--load-images=yes', '--local-to-remote-url-access=yes', '--disk-cache=no', pathjs, url], stdout=PIPE, stderr=PIPE, shell=False)
stdout, stderr = process.communicate()

#print stdout
json_data = json.loads(stdout)
start_time = json_data['log']['pages'][0]['startedDateTime']
end_time = json_data['log']['pages'][0]['endedDateTime']
initial_request = json_data['log']['pages'][0]['initialResourceLoadTime']
page_size = json_data['log']['pages'][0]['size']
requests_count  = json_data['log']['pages'][0]['resourcesCount']
element_count = json_data['log']['pages'][0]['domElementsCount']
start = datetime.strptime(start_time, '%Y-%m-%dT%H:%M:%S.%fZ')
end = datetime.strptime(end_time, '%Y-%m-%dT%H:%M:%S.%fZ')
#print start
#print end
duration = end - start
#print duration
seconds = duration.seconds + duration.microseconds / 1000000.0 
#ms = duration.seconds + duration.microseconds / 1000.0
ms = seconds * 1000 
#print "Load time : " + str(ms) + "ms"
#print "Load time " + str(seconds) + " s"
#print "Initial request time " + str(initial_request) + " ms"
#print "Page size " + str(page_size) + " bytes"
#print "Requests made " + str(requests_count)
#print "DOM Elements " + str(element_count)
#print type(args.w)
#print type(miliseconds)

http_start = time.time()		
curl = "curl -L -s -o /dev/null -w '%{http_code}' " + hostname
ps = subprocess.Popen(curl, stdout=PIPE, stderr=PIPE, shell=True)
stdout, stderr = ps.communicate()
status_code = stdout
http_end = time.time()
#print type(status_code)
http_time = "%.2f" % ((http_end - http_start) * 1000)
#print "http time :" + str(http_time)
#print "HTTP: " + str(status_code)
#print "HTTP: " + str(get_status_code(hostname, "/fsdjfpaoisdj"))
dns_time_s = ((dns_end - dns_start) * 10)
#print "DNS time: " + str(dns_time_s)
dns_time_ms = "%.2f" % ((dns_end - dns_start) * 1000)
#print "DNS time ms: " + str(dns_time_ms)
ping = "/bin/ping -c 4 -q " + hostname + " | tail --lines=2"
ps = subprocess.Popen(ping, stdout=PIPE, stderr=PIPE, shell=True)
stdout, stderr = ps.communicate()
#print stdout

match = re.search('(\d*)% packet loss', stdout)
pl = match.group(1)
pl = int(pl)
if pl != 100:
    match = re.search('([\d]*\.[\d]*)/([\d]*\.[\d]*)/([\d]*\.[\d]*)/([\d]*\.[\d]*)', stdout)
    ping_avg = match.group(2)
else:
    #if all packets were lost there is no RTA
    ping_avg = "0"

perf_data = " |website_load_time=" + str(ms) + "ms" + " website_DOM_elements=" + str(element_count) + " ping_pl=" + str(pl) + " ping_avg=" + str(ping_avg) + "ms" + " dns_resolution=" + str(dns_time_ms) + "ms" + " http_time=" + str(http_time) + "ms"

if any( [args.c < seconds, status_code != "200", pl > pl_c, dns_time_s > dns_c] ):
    #args.c < seconds:
    # print "Status 200 and load less than warning arg and pl is less than 80 and dns time is less than 1s"
    print "CRITICAL: load time: " + str(seconds) + " HTTP " + str(status_code) + perf_data
    sys.exit(2)
elif any( [args.w < seconds, status_code != "200", pl > pl_w, dns_time_s > dns_w] ):
    #args.w < seconds:
    print "WARNING: load time: " + str(seconds) + " HTTP " + str(status_code) + perf_data
    sys.exit(1)
else: 
    print "OK: load time: " + str(seconds) + " HTTP " + str(status_code) + perf_data
    sys.exit(0)
