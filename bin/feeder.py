#!/usr/bin/env python3
# -*-coding:UTF-8 -*

# import argparse
import configparser
import json
import sys
import os
import time
import uuid

from datetime import datetime
from hashlib import sha256
from pyail import PyAIL

dir_path = os.path.dirname(os.path.realpath(__file__))
pathConf = os.path.join(dir_path, '../etc/conf.cfg')

source = 'ail_feeder_matrix'

# # TODO pyail -> extract AIL config from parser ##########################################################

# Check the configuration and do some preliminary structure checks
try:
    config = configparser.ConfigParser()
    config.read(pathConf)

    # Check AIL configuration, set variables and do the connection test to AIL API
    if 'AIL' not in config:
        print('[ERROR] The [AIL] section was not defined within conf.cfg. Ensure conf.cfg contents are correct.')
        sys.exit(0)

    ail_conf = {}
    AIL = []

    try:
        # Set variables required for the Telegram Feeder
        source_uuid = config.get('AIL', 'feeder_uuid')

        ail_url = config.get('AIL', 'url')
        ail_key = config.get('AIL', 'apikey')
        ail_verifycert = config.getboolean('AIL', 'verifycert')
        ail_conf[ail_url] = {'api': ail_key, 'verifycert': ail_verifycert}
    except Exception as e:
        print(e)
        print('[ERROR] Check ../etc/conf.cfg to ensure the following variables have been set:\n')
        print('[AIL] feeder_uuid \n')
        print('[AIL] url \n')
        print('[AIL] apikey \n')
        sys.exit(0)

    try:
        ail = PyAIL(ail_url, ail_key, ssl=ail_verifycert)
    except Exception as e:
        print('[ERROR] Unable to connect to AIL Framework API. Please check [AIL] url, apikey and verifycert in ../etc/conf.cfg.\n')
        sys.exit(0)
        
except FileNotFoundError:
    print('[ERROR] ../etc/conf.cfg was not found. Copy conf.cfg.sample to conf.cfg and update its contents.')
    sys.exit(0)

def create_message_id(meta, data):
    id_string = f'{meta["date"]["timestamp"]}|{meta["chat"]["id"]}|{meta["sender"]["id"]}|'.encode() + data
    id_hash = sha256(id_string).hexdigest()
    return str(uuid.uuid5(uuid.NAMESPACE_URL, id_hash))

def extract_meta_from_matrix_dict(matrix_dict):
    meta = {}
    # date
    date = matrix_dict['timestamp']
    timestamp = time.mktime(datetime.strptime(date, "%Y-%m-%d %H:%M:%S").utctimetuple())
    meta['date'] = {'timestamp': timestamp}
    # chat
    chat_id = matrix_dict['chat_id']
    chat_network = chat_id.split(':')[1]
    meta['chat'] = {'id': chat_id}
    meta['network'] = chat_network
    # sender
    sender_id = matrix_dict['sender_alias']
    sender_username = sender_id
    meta['sender'] = {'id': sender_username, 'username': sender_username}
    return meta

def extract_message_from_matrix_dict(matrix_dict):
    return matrix_dict.get('message')

def process_matrix_dict(matrix_dict):
    meta = extract_meta_from_matrix_dict(matrix_dict)
    data = extract_message_from_matrix_dict(matrix_dict)
    meta['id'] = create_message_id(meta, data)
    print(meta)
    ail.feed_json_item(data, meta, source, source_uuid)

def create_json_from_file(f_path):
    messages = []
    with open(f_path, 'rb') as f:
        data = f.read()
    if data:
        data = data.split(b'\n{\n    timestamp:')
        # unpack first dict
        data0 = data[0].split(b'\n', 4)
        timestamp = data0[1].replace(b'    timestamp: ', b'', 1)[:-1].decode()
        chat_id = data0[2].replace(b'    chat_id: ', b'', 1)[:-1].decode()
        sender = data0[3].replace(b'    sender_alias: ', b'', 1)[:-1].decode()
        message = data0[4].replace(b'    message: ', b'', 1)[:-2]
        messages.append({'timestamp': timestamp, 'chat_id': chat_id, 'sender_alias': sender, 'message': message})
        # unpack dicts
        if len(data) > 1:
            for d in data[1:]:
                d = d.split(b'\n', 3)
                timestamp = d[0][1:-1].decode()
                chat_id = d[1].replace(b'    chat_id: ', b'', 1)[:-1].decode()
                sender = d[2].replace(b'    sender_alias: ', b'', 1)[:-1].decode()
                message = d[3].replace(b'    message: ', b'', 1)[:-2]
                messages.append({'timestamp': timestamp, 'chat_id': chat_id, 'sender_alias': sender, 'message': message})
                # print({'timestamp': timestamp, 'chat_id': chat_id, 'sender_alias': sender, 'message': message})
    return messages


if __name__ == '__main__':
    file_path = 'my_matrix_file.json'
    for message_dict in create_json_from_file(file_path):
        process_matrix_dict(message_dict)
