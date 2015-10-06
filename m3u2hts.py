#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import logging
import os
import json
import re
import requests
import uuid
import sys
import collections


def get_uuid():
    return uuid.uuid4().hex


def read_m3u(m3u, lang):
    ''' geather mux information form m3u file '''
    mux_info = collections.OrderedDict()
    data = ''
    if not os.path.isfile(m3u):
        try:
            data = requests.get(m3u).text
        except requests.exceptions.RequestException:
            logging.error('Could not open url!')
    else:
        logging.info('Open file "%s".', m3u)
        with open(m3u, 'r', encoding='utf-8') as f:
            for line in f:
                data += line

    logging.info('Checking file now...')
    for i, line in enumerate(data.split('\n')):
        if line.startswith('#EXTINF'):
            # TODO: only for iptv.ink for now
            match = re.findall(r'\#EXTINF\:(.*?)\ tvg-id="(.*?)"\ group-title="(.*?)"\ tvg-logo="(.*?)", [\[\w\ ]+\](.*?)\[\/COLOR\]', line, re.DOTALL)
            if match:
                if len(match[0]) == 5:
                    channel_number, url, groupt, tvg_logo, tvg_name = match[0]
                    if groupt[:2] in lang:
                        logging.debug('Found: %s, %s, %s, %s, %s', channel_number, url, groupt, tvg_logo, tvg_name.encode('utf-8'))
                        mux_info[i] = [channel_number, groupt, tvg_logo, tvg_name]
                else:
                    logging.error('Line %04d from %s is unsupported. Exiting', i, m3u)
                    raise match

        if line.startswith('http:') and i - 1 in mux_info.keys():
            mux_info[i - 1].append(line)

    return mux_info


def create_muxes(muxes_info, interface='eth0', network='IPTV'):
    logging.info('Creating muxes and services.')
    #working_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'muxes')
    # /home/hts/.hts/tvheadend/input/iptv/networks/140a0de3af80e879b861e63d3791ac30/
    working_dir = os.path.join('/home', 'hts', '.hts', 'tvheadend', 'input', 'iptv', 'networks', '140a0de3af80e879b861e63d3791ac30', 'muxes')
    if not os.path.exists(working_dir):
        os.mkdir(working_dir)

    for key, values in muxes_info.items():
        _, _, _, tvg_name, url = values[0], values[1], values[2], values[3], values[4]
        tvg_name_safe = tvg_name.upper().replace(' ', '_').replace('Ä', 'AE').replace('Ö', 'OE').replace('Ü', 'UE').replace('ß', 'SS')
        config_data = collections.OrderedDict([("priority", 0),
                                               ("spriority", 0),
                                               ("iptv_url", "pipe://ffpipe.sh " + tvg_name_safe + " " + url),
                                               ("iptv_interface", interface),
                                               ("iptv_atsc", False),
                                               ("iptv_muxname", tvg_name),
                                               ("iptv_sname", tvg_name),
                                               ("iptv_respawn", True),
                                               ("enabled", True),
                                               ("epg", 1),
                                               ("onid", 1),
                                               ("tsid", 1),
                                               ("scan_result", 1),
                                               ("pmt_06_ac3", 0)])
        muxid = get_uuid()
        if not os.path.exists(os.path.join(working_dir, muxid)):
            os.mkdir(os.path.join(working_dir, muxid))
        with open(os.path.join(working_dir, muxid, 'config'), 'w') as f:
            json.dump(config_data, f, indent=8)

        # create service
        service_data = collections.OrderedDict([("sid", 1),
                                                ("lcn", 0),
                                                ("lcn_minor", 0),
                                                ("lcn2", 0),
                                                ("svcname", tvg_name_safe),
                                                ("provider", network),
                                                ("dvb_servicetype", 1),
                                                ("dvb_ignore_eit", False),
                                                ("prefcapid", 0),
                                                ("prefcapid_lock", 0),
                                                ("force_caid", 0),
                                                ("created", 1443998526),
                                                ("last_seen", 1443998526),
                                                ("enabled", True),
                                                ("auto", 0),
                                                ("priority", 0),
                                                ("pcr", 256),
                                                ("pmt", 4096),
                                                ("stream", [collections.OrderedDict([("pid", 256),
                                                                                    ("type", "H264"),
                                                                                    ("position", 0)]),
                                                            collections.OrderedDict([("pid", 257),
                                                                                     ("type", "AAC-LATM"),
                                                                                     ("position", 0),
                                                                                     ("audio_type", 0)])])])
        serviceid = get_uuid()
        if not os.path.exists(os.path.join(working_dir, muxid, 'services')):
            os.mkdir(os.path.join(working_dir, muxid, 'services'))
        with open(os.path.join(working_dir, muxid, 'services', serviceid), 'w') as f:
            json.dump(service_data, f, indent=8)


def main():
    parser = argparse.ArgumentParser(description='Convert M3U file to TVHeadend Muxes.')
    parser.add_argument('-m', '--m3u_file', type=str, help='Path to M3U file. Can be a file on the HDD or internet address.')
    parser.add_argument('-i', '--interface', action='store', default='eth0', help='Name of interface. [default: %(default)s].')
    parser.add_argument('-n', '--network', action='store', default='IPTV', help='Name of IPTV network. [default: %(default)s].')
    parser.add_argument('-l', '--language', nargs='+', type=str, choices=['DE', 'AT', 'CH', 'FR', 'NE', 'UK', 'IT', 'TR', 'RU', 'CZ'], default=['DE', 'AT', 'CH'], help='Only extract channels in that language. [default: %(default)s].')
    parser.add_argument('-v', '--verbose', help='Be Verbose', action='store_true')
    args = parser.parse_args()

    logging.getLogger(__file__)

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s:%(levelname)s:%(message)s', datefmt='%H:%M:%S')
    else:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s', datefmt='%H:%M:%S')

    if args.m3u_file is not None:
        muxes_info = read_m3u(args.m3u_file, args.language)
        create_muxes(muxes_info, args.interface, args.network)
    else:
        raise "No input file specified!"

if __name__ == '__main__':
    main()
