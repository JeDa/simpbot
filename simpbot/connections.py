# -*- coding: utf-8 -*-
# Simple Bot (SimpBot)
# Copyright 2016, Ismael Lugo (kwargs)

from six.moves import _thread
from six.moves import configparser
from . import envvars
from .irc import client
from .dbstore import dbstore
from .request import manager
from .commands import ProccessCommands
from .bottools import text
from .bottools import dummy
from . import localedata

i18n = localedata.get()
logging = __import__('logging').getLogger('connections')


@text.lower
def add(network, rchan, ruser, maxu, maxc, *args, **kwargs):
    if network in envvars.networks:
        logging.warning(i18n['network duplicated'], network)
        return False
    irc = client(network, *args, **kwargs)
    irc.dbstore = dbstore.dbstore(network, maxc, maxu, rchan, ruser)
    irc.request = manager.manager(irc)
    irc.commands = ProccessCommands(irc)
    envvars.networks[network] = irc
    return True


@text.lower
def get(network):
    if not network in envvars.networks:
        return
    return envvars.networks[network]


@text.lower
def remove(network):
    if not network in envvars.networks:
        return False
    irc_ = envvars.networks[network]
    if irc_.connected:
        irc_.disconnect()
    del envvars.networks[network]


def load_servers():
    sections = ['user', 'server', 'simpbot', 'database']
    options = {
        'user': ['nick', 'user'],
        'nickserv': ['sasl', 'username', 'password'],
        'server': ['network', 'address', 'port'],
        'simpbot': ['autoconnect', 'prefix', 'wtime', 'msgps', 'timeout'],
        'database': ['chanregister', 'userregister']}

    for servercfg in envvars.servers.listdir():
        if not envvars.servers.isfile(servercfg):
            continue
        conf = configparser.ConfigParser(**envvars.cfg_kwargs)
        path = envvars.servers.join(servercfg)
        conf.read(path)
        invalid = False
        for section in sections:
            if dummy.invalid_section(conf, section, options[section]):
                logging.error(i18n['bad config'], path)
                invalid = True
                break
        if invalid:
            continue

        nick = conf.get('user', 'nick')
        user = conf.get('user', 'user')

        nickserv = None
        sasl = None
        if conf.has_section('nickserv'):
            if not dummy.invalid_section(conf, 'nickserv', options['nickserv']):
                sasl = conf.getboolean('nickserv', 'sasl')
                nickserv = [
                    conf.get('nickserv', 'username'),
                    conf.get('nickserv', 'password')
                ]

        network = conf.get('server', 'network')
        address = conf.get('server', 'address')
        port = conf.get('server', 'port')
        if conf.has_option('server', 'password'):
            password = conf.get('server', 'password')
        else:
            password = None

        autoconnect = conf.getboolean('simpbot', 'autoconnect')
        prefix = conf.get('simpbot', 'prefix')
        msgps = conf.getfloat('simpbot', 'msgps')
        timeout = conf.getint('simpbot', 'timeout')
        wtime = conf.getint('simpbot', 'wtime')
        if conf.has_option('simpbot', 'default_lang'):
            lang = conf.get('simpbot', 'default_lang')
            if not localedata.simplocales.exists(lang, 'fullsupport'):
                lang = envvars.default_lang
        else:
            lang = envvars.default_lang

        chanregister = conf.get('database', 'chanregister')
        userregister = conf.get('database', 'userregister')
        if conf.has_option('database', 'maxusers'):
            maxusers = conf.getint('dabase', 'maxusers')
        else:
            maxusers = 0
        if conf.has_option('database', 'maxchans'):
            maxchans = conf.getint('dabase', 'maxchans')
        else:
            maxchans = 0

        if not add(network, chanregister, userregister, maxusers, maxchans,
            address, port, nick, user, nickserv, sasl, timeout, msgps, wtime,
            password, prefix):
            continue

        if autoconnect:
            network = network.lower()
            _thread.start_new(envvars.networks[network].try_connect, (), {})