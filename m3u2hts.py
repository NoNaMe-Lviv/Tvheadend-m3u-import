#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import logging
import os
import json
import re
import uuid
import sys
import collections
import shutil


def get_uuid():
    ''' create 16 random chars '''
    return uuid.uuid4().hex


def valid_hts_path(hts_home):
    ''' check, if the given path to tvheadend is valid '''
    if not os.path.exists(hts_home):
        logging.error('Wrong path to tvheadend files.')
        return False
    if os.path.isfile(os.path.join(hts_home, 'hts.log')) and os.path.exists(os.path.join(hts_home, 'input')):
        logging.info('Path to tvheadend is correct.')
        return True


def check_channel_dir(hts_home):
    ''' check, if channel directory exists '''
    try:
        channel_dir = os.path.join(hts_home, 'channel')
        if not os.path.exists(channel_dir):
            os.mkdir(channel_dir)

        config_dir = os.path.join(channel_dir, 'config')
        if not os.path.exists(config_dir):
            os.mkdir(config_dir)

        return True
    except OSError:
        logging.error('Could not write %s. No Permissions', config_dir)
        return False


def create_networks_config(networks_path, networkid, network_name, charset):
    ''' create the config file in networks directory '''
    network_config = collections.OrderedDict([("priority", 1),
                                             ("spriority", 1),
                                             ("max_streams", 0),
                                             ("max_bandwidth", 0),
                                             ("max_timeout", 60),
                                             ("networkname", network_name),
                                             ("nid", 0),
                                             ("autodiscovery", False),
                                             ("skipinitscan", True),
                                             ("idlescan", False),
                                             ("sid_chnum", False),
                                             ("ignore_chnum", False),
                                             ("satip_source", 0),
                                             ("charset", charset),
                                             ("localtime", False)])

    with open(os.path.join(networks_path, networkid)) as f:
        json.dump(network_config, f, indent=8)


def write_service_data(serviceid, muxid, working_dir, tvg_name_safe, network, charset):
    ''' write the service data into a file '''
    service_data = collections.OrderedDict([("sid", 1),
                                            ("lcn", 0),
                                            ("lcn_minor", 0),
                                            ("lcn2", 0),
                                            ("svcname", tvg_name_safe),
                                            ("provider", network),
                                            ("dvb_servicetype", 1),
                                            ("dvb_ignore_eit", False),
                                            ("charset", charset),
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
    if not os.path.exists(os.path.join(working_dir, muxid, 'services')):
        os.mkdir(os.path.join(working_dir, muxid, 'services'))
    with open(os.path.join(working_dir, muxid, 'services', serviceid), 'w') as f:
        json.dump(service_data, f, indent=8)


def write_mux_data(tvg_name_safe, url, interface, tvg_name, working_dir, muxid, charset):
    ''' write the mux data into a file '''
    config_data = collections.OrderedDict([("priority", 0),
                                           ("spriority", 0),
                                           ("iptv_url", "pipe://ffpipe.sh " + tvg_name_safe + " " + url),
                                           ("iptv_interface", interface),
                                           ("iptv_atsc", False),
                                           ("charset", charset),
                                           ("iptv_muxname", tvg_name),
                                           ("iptv_sname", tvg_name),
                                           ("iptv_respawn", True),
                                           ("enabled", True),
                                           ("epg", 1),
                                           ("onid", 1),
                                           ("tsid", 1),
                                           ("scan_result", 1),
                                           ("pmt_06_ac3", 0)])

    if not os.path.exists(os.path.join(working_dir, muxid)):
        os.mkdir(os.path.join(working_dir, muxid))
    with open(os.path.join(working_dir, muxid, 'config'), 'w') as f:
        json.dump(config_data, f, indent=8)


def write_channel_data(hts_home, channelid, tvg_name, channel_number, serviceid):
    ''' write channel data into a file '''
    channel_data = collections.OrderedDict([("enabled", True),
                                            ("name", tvg_name),
                                            ("number", channel_number),
                                            ("epgauto", False),
                                            ("dvr_pre_time", 0),
                                            ("dvr_pst_time", 0),
                                            ("services", [serviceid]),
                                            ("tags", []),
                                            ("bouquet", "")])

    with open(os.path.join(hts_home, 'channel', 'config', channelid), 'w') as f:
        json.dump(channel_data, f, indent=8)


def write_xmltv_channel(hts_home, channelid, tvg_id, tvg_name):
    ''' write channel in epg source '''
    data = None
    xmltv_channel_file = os.path.join(hts_home, 'epggrab', 'xmltv', 'channels', tvg_id)
    if os.path.isfile(xmltv_channel_file):
        with open(xmltv_channel_file, 'r') as f:
            data = json.load(f, object_pairs_hook=collections.OrderedDict)
        try:
            if channelid not in data['channels']:
                with open(xmltv_channel_file, 'w') as f:
                    data['channels'].append(channelid)
                    json.dump(data, f, indent=8)
        except TypeError:
            print(channelid, data, tvg_id)
            raise
    else:
        xmltv_channel_data = collections.OrderedDict([("name", tvg_name),
                                                      ("channels", [channelid])])
        with open(xmltv_channel_file, 'w') as f:
            json.dump(xmltv_channel_data, f, indent=8)


def read_m3u(m3u, lang):
    ''' geather mux information form m3u file '''
    mux_info = collections.OrderedDict()
    data = ''
    if not os.path.isfile(m3u):
        try:
            import requests
        except ImportError:
            logging.error('Could not import "requests" module.')
            sys.exit(-1)

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
            # NOTE: only for iptv.ink for now
            match = re.findall(r'\#EXTINF\:(.*?)\ tvg-id="(.*?)"\ group-title="(.*?)"\ tvg-logo="(.*?)", [\[\w\ ]+\](.*?)\[\/COLOR\]', line, re.DOTALL)
            if match:
                if len(match[0]) == 5:
                    channel_number, tvg_id, groupt, tvg_logo, tvg_name = match[0]
                    if groupt[:2] in lang:
                        logging.debug('Found: %s, %s, %s, %s, %s', channel_number, tvg_id, groupt, tvg_logo, tvg_name.encode('utf-8'))
                        mux_info[i] = [channel_number, tvg_id, tvg_name]
                else:
                    logging.error('Line %04d from %s is unsupported. Exiting', i, m3u)
                    raise match

        if line.startswith('http:') and i - 1 in mux_info.keys():
            mux_info[i - 1].append(line)

    return mux_info


def search_for_networks(hts_home, network_name='IPTV'):
    ''' search for existing networks
        INFO: can only handle one network correct for now '''
    networkid = ''
    input_path = os.path.join(hts_home, 'input')

    iptv_path = os.path.join(input_path, 'iptv')
    if not os.path.exists(iptv_path):
        os.mkdir(iptv_path)
        logging.debug('Could not find %s folder. Creating.', iptv_path)

    networks_path = os.path.join(input_path, 'iptv', 'networks')
    if not os.path.exists(networks_path):
        os.mkdir(networks_path)
        logging.debug('Could not find %s folder. Creating.', networks_path)

    iptv_networks = os.listdir(networks_path)
    if len(iptv_networks) == 0:
        networkid = get_uuid()
        os.mkdir(os.path.join(networks_path, networkid))
        create_networks_config(networks_path, networkid, network_name)
    else:
        networkid = iptv_networks[0]

    logging.debug('Network ID is: %s', networkid)

    return networkid


def create_files(muxes_info, interface, network_name, hts_home, charset):
    ''' create config files for muxes, services and channels '''
    logging.info('Creating muxes and services.')
    networkid = search_for_networks(hts_home, network_name)
    working_dir = os.path.join(hts_home, 'input', 'iptv', 'networks', networkid, 'muxes')
    if not os.path.exists(working_dir):
        os.mkdir(working_dir)

    for i, values in enumerate(muxes_info.values()):
        channel_number, tvg_id, tvg_name, url = i, values[1], values[2], values[3]
        tvg_name_safe = tvg_name.upper().replace(' ', '_').replace('Ä', 'AE').replace('Ö', 'OE').replace('Ü', 'UE').replace('ß', 'SS')

        muxid = get_uuid()
        write_mux_data(tvg_name_safe, url, interface, tvg_name, working_dir, muxid, charset)

        serviceid = get_uuid()
        write_service_data(serviceid, muxid, working_dir, tvg_name_safe, network_name, charset)

        channelid = get_uuid()
        write_channel_data(hts_home, channelid, tvg_name, int(channel_number), serviceid)

        write_xmltv_channel(hts_home, channelid, tvg_id, tvg_name)


def remove_old_config(hts_home):
    ''' remove old files '''
    channels_dir = os.path.join(hts_home, 'channel', 'config')
    xmltv_channels_dir = os.path.join(hts_home, 'epggrab', 'xmltv', 'channels')
    networkid = search_for_networks(hts_home)
    networks_path = os.path.join(hts_home, 'input', 'iptv', 'networks', networkid, 'muxes')
    paths = [channels_dir, xmltv_channels_dir, networks_path]
    for path in paths:
        logging.info('Removing files in: %s', path)
        list_dir = os.listdir(path)
        if len(list_dir) == 0:
            continue
        for f in list_dir:
            if os.path.isfile(os.path.join(path, f)):
                os.remove(os.path.join(path, f))
            else:
                shutil.rmtree(os.path.join(path, f))


def main():
    parser = argparse.ArgumentParser(description='Convert M3U file to TVHeadend muxes/channels. You maybe need to run this script with root rights.')
    parser.add_argument('-m', '--m3u_file', default='http://tv.iptv.ink/iptv.ink', help='Path to M3U file. [default: %(default)s]')
    parser.add_argument('-i', '--interface', action='store', default='eth0', help='Name of interface. [default: %(default)s].')
    parser.add_argument('-n', '--network', action='store', default='IPTV', help='Name of IPTV network. [default: %(default)s].')
    parser.add_argument('-l', '--language', nargs='+', type=str, choices=['DE', 'AT', 'CH', 'FR', 'NE', 'UK', 'IT', 'TR', 'RU', 'CZ'], default=['DE', 'AT', 'CH'], help='Only extract channels in that language. [default: %(default)s].')
    parser.add_argument('-c', '--charset', choices=['AUTO', 'ISO-6937', 'ISO-8859-1', 'UTF-8', 'GB2312', 'UCS2', 'AUTO_POLISH'], default='UTF-8', help='Set charset. [default: %(default)s].')
    parser.add_argument('-d', '--dir', default='/home/hts/.hts/tvheadend', help='Path to tvheadend directory. [default: %(default)s].')
    parser.add_argument('--remove_old', help='Remove old configuration', action='store_true')
    parser.add_argument('-v', '--verbose', help='Be Verbose', action='store_true')
    args = parser.parse_args()

    logging.getLogger(__file__)

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s:%(levelname)s:%(message)s', datefmt='%H:%M:%S')
    else:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s:%(levelname)s:%(message)s', datefmt='%H:%M:%S')

    if not valid_hts_path(args.dir):
        sys.exit(-1)

    if args.m3u_file is not None:
        if check_channel_dir(args.dir):
            if args.remove_old:
                remove_old_config(args.dir)
            muxes_info = read_m3u(args.m3u_file, args.language)
            create_files(muxes_info, args.interface, args.network, args.dir, args.charset)
    else:
        logging.error("No m3u specified!")

if __name__ == '__main__':
    main()
