# -*- coding: utf-8 -*-
# Simple Bot (SimpBot)
# Copyright 2016, Ismael Lugo (kwargs)

from simpbot.bottools import irc as irctool
from simpbot.handlers import rpl
from simpbot.handlers import handler
import re

################################## WHOIS #####################################


@handler(rpl(311, '!{nick} !{user} !{host} \* :!{realname}+'))
def user_rpl(irc, ev):
    irc.request.set_user(*ev('user', 'host', 'nick', 'realname'))


@handler(rpl(312, '!{nick} !{server} :!{server_info}+'))
def server(irc, ev):
    if not irc.request.has_user(ev('nick')):
        return
    irc.request.get_user(ev('nick')).set('server', ev('server', 'server_info'))


@handler(rpl(313, '!{nick} :!{msg}+'))
def ircoper(irc, ev):
    if not irc.request.has_user(ev('nick')):
        return
    irc.request.get_user(ev('nick')).set('ircoper', True)


@handler(rpl(317, '!{nick} !{lastmsg} !{since} :!{msg}'))
def idle(irc, ev):
    if not irc.request.has_user(ev('nick')):
        return
    user = irc.request.get_user(ev('nick'))
    user.lastmsg = int(ev('lastmsg'))
    user._idle = int(ev('since'))
    user.update()


@handler(rpl(318, '!{nick} :!{msg}+'))
def end_whois(irc, ev):
    if not irc.request.has_user(ev('nick')):
        return
    user = irc.request.get_user(ev('nick'))
    user.set('completed', True)


@handler(rpl(319, '!{nick} :!{channels}+'))
def channels(irc, ev):
    if not irc.request.has_user(ev('nick')):
        return

    features = irc.features
    regex = '([%s])?([%s]{1,}[^ ]+)'
    if hasattr(features, 'statusmsg') and hasattr(features, 'chantypes'):
        regex = regex % (
            re.escape(irc.features.statusmsg),
            re.escape(irc.features.chantypes))
    else:
        regex = regex % ('@\+', '#')
    # Realizar chequeo de canales...
    user = irc.request.get_user(ev('nick'))
    for modes, channel in re.findall(regex, ev('channels')):
        user.set_status(channel, 'reset', modes)
    user.update()


@handler(rpl(330, '!{nick} !{account} :is logged in as'))
def account(irc, ev):
    if not irc.request.has_user(ev('nick')):
        return
    irc.request.get_user(ev('nick')).set('account', ev('account'))


@handler(rpl(671, '!{nick} :!{msg}+'))
def ssl(irc, ev):
    if not irc.request.has_user(ev('nick')):
        return
    irc.request.get_user(ev('nick')).set('ssl', True)

################################### WHO ######################################


@handler(rpl(352, '!{data}+'))
def simpuser(irc, ev):
    regex = ('(?P<target>[^ ]+) (?P<user>[^ ]+) (?P<host>[^ ]+)'
    '( (?P<host2>[^ ]+))? (?P<server>[^ ]+) (?P<nick>[^ ]+) [HG]'
    '(?P<status>[%s]{0,}) :[0-9] (?P<realname>.+)')
    data = re.match(regex % re.escape(irc.features.statusmsg), ev('data'))
    if not data:
        return

    user = irc.request.set_user(*data.group('user', 'host', 'nick', 'realname'))
    user.set('server', data.group('server'))
    if irctool.ischannel(data.group('target'), irc=irc):
        chan = irc.request.get_chan(data.group('target'))
        chan.append(user)
        user.set_status(data.group('target'), 'reset', data.group('status'))
        user.set('completed', True)
        user.update()


@handler(rpl(354, '152 !{data}+'))
def extuser(irc, ev):
    regex = ('(?P<target>[^ ]+) (?P<user>[^ ]+) (?P<host>[^ ]+)'
    '( (?P<host2>[^ ]+))? (?P<server>[^ ]+) (?P<nick>[^ ]+) [HG]'
    '(?P<status>[%s]{0,}) (?P<account>[^ ]+) :(?P<realname>.+)')
    data = re.match(regex % re.escape(irc.features.statusmsg), ev('data'))
    if not data:
        return

    user = irc.request.set_user(*data.group('user', 'host', 'nick', 'realname'))
    user.set('server', data.group('server'))
    if data.group('account') != '0':
        user.set('account', data.group('account'))

    if irctool.ischannel(data.group('target'), irc=irc):
        chan = irc.request.get_chan(data.group('target'))
        chan.append(user)
        user.set_status(data.group('target'), 'reset', data.group('status'))
        user.set('completed', True)
        user.update()


################################ nosuch #####################################


@handler(rpl(401, '!{target} :No such nick/channel'))
def nosuch(irc, ev):
    user = irc.request.set_user(ev('target'), None, None)
    if user.host:
        user.reset()