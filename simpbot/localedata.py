# -*- coding: utf-8 -*-
# Simple Bot (SimpBot)
# Copyright 2016-2017, Ismael Lugo (kwargs)

import re
import sys
from os import path
from . import workarea

logging = __import__('logging').getLogger('localedata')


langsep = '-'
ext = '.dat'  # extension name


class Error(Exception):
    def __init__(self, string, line=None, extra=None):
        if line is not None:
            string = string + ' in line #%s' % line
        if extra is not None:
            string = string + ': ' + extra
        self.string = string

    def __str__(self):
        return self.string

    def __repr__(self):
        return '%s("%s")' % (self.__class__.__name__, self.string)


class MsgidError(Error):
    def __init__(self, string, msgid=None, line=None, extra=None, package=None):
        if package is not None:
            string += ' Package: "%s"' % package
        if msgid is None:
            string = 'msgid ' + string
        else:
            string = 'msgid "' + msgid + '"" ' + string
        super(MsgidError, self).__init__(string, line, extra)


class MsgstrError(Error):
    pass


class ConfigError(Error):
    pass


class LocaleData:

    def __init__(self, abspath, comment_prefixes=('#',)):
        self.localedata = workarea.workarea(abspath)
        self.comment_prefixes = comment_prefixes
        self.optregex = re.compile('(?P<option>msgid|msgstr|msgend|config)( {1,'
        '}(?P<value>.*))?', re.IGNORECASE)
        self.cache = {}

    def exists(self, lang, package):
        """
        Check whether locale data is available for the given locale.  Ther
        return value is `True` if it exists, `False` otherwise.

        :param lang: language code
        :param package: the package name
        """
        return self.localedata.exists(lang.upper() + langsep + package + ext)

    def fullsupport(self):
        return self.langs('fullsupport')

    def load(self, lang, package):
        if not self.in_cache(lang, package):
            self.read(lang, package)
        return self.get(lang, package)

    def langs(self, package):
        """Return a list of all languages availables for a package.

        :param package: the package name
        """
        package = package + ext
        avail = []
        for locale in self.localedata.listdir():
            try:
                lang, pack = locale.split(langsep, 1)
            except ValueError:
                raise Error('Invalid locale name: %s', locale)
            if pack == package:
                avail.append(lang.upper())
        return avail

    def in_cache(self, lang, package_name):
        return lang in self.cache and package_name in self.cache[lang]

    def _read(self, fp, lang, package_name, abspath, update_cache=False):
        lang = lang.upper()
        if self.in_cache(lang, package_name) and not update_cache:
            return

        read = fp.read()

        strip = True
        tostrip = ''
        addline = False
        comment = True
        nline = 0
        equal = lambda bool: bool == 'yes'

        def chkequal(bool, line):
            if not bool in ('yes', 'y', 'not', 'no', 'n'):
                raise ConfigError('Bad boolean', nline, line)

        def stripequal(value):
            value = value.strip()
            chkequal(value, line)
            return equal(value)

        last_msgid = None
        msgid_line = None
        localedata = Locale(lang, package_name, abspath)

        for line in read.splitlines():
            nline += 1
            if line == '' and not addline:
                continue

            if strip and not line.isspace() and line.startswith(' '):
                if tostrip:
                    line = line.replace(strip, 1)
                else:
                    line = line.lstrip()

            # comment line?
            comment_line = False
            for prefix in self.comment_prefixes:
                if line.startswith(prefix) and comment:
                    comment_line = True
                    break
            if comment_line:
                continue

            res = self.optregex.match(line)
            if res:
                opt, value = res.group('option', 'value')
                if opt == 'config' and value:
                    try:
                        config, value = value.lower().split(' ', 1)
                    except ValueError:
                        raise ConfigError('Bad config', nline, line)

                    if config == 'nostrip':
                        strip = stripequal(value)
                        continue
                    elif config == 'addline':
                        addline = stripequal(value)
                        continue
                    elif config == 'comment':
                        comment = stripequal(value)
                        continue
                    else:
                        raise ConfigError('Bad boolean', nline, line)

                elif opt == 'msgid':
                    if value is None or value == '':
                        raise MsgidError('missing value', None, nline, line, package_name)
                    elif not last_msgid is None and localedata[last_msgid] is None:
                        raise MsgidError('without msgstr', last_msgid, msgid_line, package_name)

                    localedata[value] = ''
                    last_msgid = value
                    msgid_line = nline
                    strip = True
                    tostrip = ''
                    addline = False
                elif opt == 'msgstr':
                    if value is None:
                        value = ''
                    if last_msgid is None:
                        raise MsgstrError('msgstr without msgid', nline)

                    if localedata[last_msgid] is None:
                        if value != '' and addline:
                            value += '\n'
                        localedata[last_msgid] = value
                        continue
                    if addline:
                        value += '\n'
                    localedata[last_msgid] += value
                elif opt == 'msgend':
                    if not last_msgid is None:
                        continue
                    elif localedata[last_msgid] is None:
                        raise MsgidError('without msgstr', last_msgid, msgid_line, package_name)

                    last_msgid = None
                    strip = True
                    tostrip = ''
                    addline = False

            else:
                if last_msgid is None:
                    continue

                if addline:
                    line += '\n'
                localedata.msgid[last_msgid] += line
        if not lang in self.cache:
            self.cache[lang] = {}
        self.cache[lang][package_name] = localedata

    def read(self, lang, package):
        if not self.exists(lang, package):
            return 0
        lang = lang.upper()
        abspath = self.localedata.join(lang.upper() + langsep + package + ext)
        with open(abspath, 'r') as fp:
            self._read(fp, lang, package, abspath)
        return 1

    def get(self, lang, package):
        lang = lang.upper()
        if self.in_cache(lang, package):
            return self.cache[lang][package]

    def clear_cache(self):
        self.cache.clear()

    def remove_from_cache(self, lang, package):
        lang = lang.upper()
        if self.in_cache(lang, package):
            del self.cache[lang][package]
            return 1
        return 0

    def getfull(self, lang=None, package=None, optlang=None):
        from . import envvars
        if package is None:
            package = sys._getframe(1).f_globals['__name__']
        if lang is None:
            lang = envvars.default_lang

        if self.exists(lang, package):
            return self.load(lang, package)

        langs = self.langs(package)
        if len(langs) == 0:
            raise Error('Invalid package ' + package)
        elif len(langs) == 1:
            return self.load(langs.pop(), package)
        elif optlang in langs:
            return self.load(optlang, package)
        elif envvars.default_lang in langs:
            return self.load(envvars.default_lang, package)
        else:
            raise Error('Invalid lang: "%s" only support %s' % (package, lang))


class Locale:

    def __init__(self, lang, package_name, abspath):
        self.lang = lang
        self.msgid = {}
        self.package = package_name
        self.abspath = abspath

    def __call__(self, msgid):
        return self.__getitem__(msgid)

    def __repr__(self):
        return "<locale lang='%s' path='%s'>" % (self.lang, self.abspath)

    def __getitem__(self, msgid):
        if msgid in self.msgid:
            return self.msgid[msgid]
        else:
            raise MsgidError('Invalid MSGID: ' + msgid)

    def __delitem__(self, msgid):
        if msgid in self.msgid:
            del self.msgid[msgid]
        else:
            raise MsgidError('Invalid MSGID: ' + msgid)

    def __setitem__(self, msgid, msgstr):
        if msgid in self.msgid and not self.msgid[msgid] in (None, ''):
            logging.warning("Package: '%s' MSGID: '%s' updating MSGTR!",
            self.abspath, msgid)
        self.msgid[msgid] = msgstr

    def __iter__(self):
        return iter(self.msgid)

    def get(self, msgid, msgstr=None):
        if msgstr is not None:
            self.__setitem__(msgid, msgstr)
        else:
            return self.__getitem__(msgid)

    def remove(self, msgid):
        self.__delitem__(msgid)

    def has_msgid(self, msgid):
        return msgid in self.msgid


simplocales = LocaleData(path.join(path.dirname(__file__), 'localedata'))
get = simplocales.getfull