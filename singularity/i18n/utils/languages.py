#!/usr/bin/env python
#
# languages.py - Read language names from several sources and save them for E:S
#
#    Copyright (C) 2012 Rodrigo Silva (MestreLion) <linux@rodrigosilva.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. See <http://www.gnu.org/licenses/gpl.html>

import sys
import os.path as osp
import json
import argparse

class Locale(object):
    """Wrapper for a Locale object in various sources, like babel and pyicu"""

    @staticmethod
    def getAvailableSources():
        """Return a list of all available Locale info sources.

        First item is by definition the default source used when none is given.
        Last item is by definition the game's PO headers
        """
        return ['icu', 'babel', 'pofiles']

    @staticmethod
    def getGameTranslations():
        """Return a list of available game translations (both ll and ll_CC)

        Generated list is suitable to be used as a filter to
        getLanguages() method. Do not confuse with the languages
        data dict that is generated by this module.

        This function is just here as a reference, but I won't use this
        at all. You may even delete it, I truly don't care.
        """
        game_translations = set()
        for language in g.available_languages():
            game_translations.add(language)
            if "_" in language:
                game_translations.add(language.split("_",1)[0])
        return dict(game_translations)

    @classmethod
    def getAvailableLocales(cls, source):
        """Return a list of all available locale codes for the given source"""

        return cls.dispatch_source_method(source, 'getAvailableLocales',
                                          default_func=lambda: [])

    @classmethod
    def getLocaleNames(cls, source, code):
        """Return a tuple of locale english name and localized name"""

        return cls.dispatch_source_method(source, 'getLocaleNames',
                                          args=(code,),
                                          default_func=lambda: None)

    @classmethod
    def getLanguages(cls, locales=None, tupletype=True, source=None):
        """Return a languages dict of Locale info from a given source

        locales input is a list of locale codes to be selected among
        the available ones. Non-available codes are silently ignored.
        If locales is omitted or empty, output will have all available
        locales.

        Output languages dict has locale codes as keys, and either a
        2-tuple or a dict(English, native) as values.

        Values represent the Display Name of the language expressed
        in English and in native language for each locale code
        """
        if locales:
            locales = set(locales) & set(cls(source=source).getAvailableLocales())
        else:
            locales = cls.getAvailableLocales(source)

        output = {}
        for code in locales:
            names  = cls.getLocaleNames(source, code)
            if (names):
                english, native = names
                if not (english or native): continue
                if native: native = native.title()
                if tupletype:
                    output[code] = (english, native)
                else:
                    output[code] = dict(english=english, native=native)

        return output

    @staticmethod
    def saveLanguagesData(languages, filename):
        """Docstring... for *this*? You gotta be kidding me...

        Ok... there it goes: Save a languages dict, like the one
        generated by getLanguages() method, to a JSON data file
        Happy now?
        """
        with open(filename, 'w') as fd:
            json.dump(languages, fd, indent=0, separators=(',', ': '),
                      sort_keys=True)
            fd.write('\n') # add EOF newline

    @staticmethod
    def loadLanguagesData(filename):
        """Again? Can't you read code?

        Ok, ok... Load and return a language dict from a JSON data file
        """
        with open(filename) as fd:
            return json.load(fd)


    def __init__(self, code=None, source=None):
        """Initialize a Locale of the given code from the given source

        If source is blank or omitted, the default one from by
        getAvailableSources() is used.

        code must be string with ll or ll_CC format. If blank or
        omitted, only getAvailableLocales() method will work,
        all other attributes will be None.
        """

        # Attributes
        self.source       = source
        self.code         = code
        self.english_name = None
        self.native_name  = None

        # Handle source
        if not self.source: self.source = self.getAvailableSources()[0]
        if self.source not in self.getAvailableSources():
            raise ValueError("{0} is not a valid source."
                             " Available sources are: {1}".format(
                                source, ", ".join(self.getAvailableSources())))
        self.source = self.source.lower()

        # Override default attributes methods and members according to the given source
        self.english_name, self.native_name = self.getLocaleNames(source)

    @classmethod
    def dispatch_source_method(cls, source, func_name, args=(), default_func=lambda: None):
        import types
        
        # Create temporary globals.
        temp_globals = dict(globals())

        # Execute import before dispatch to update globals with the return.
        do_import = getattr(cls, str(source) + '_import', lambda *args: None)
        temp_globals.update(do_import(source))
        
        method_name = str(source) + '_' + func_name
        method = getattr(cls, method_name, default_func)
        
        temp_func = types.FunctionType(method.__code__, temp_globals, method_name)
        temp_method = types.MethodType(temp_func, cls, cls.__class__)
        
        return temp_method(*args)

    # icu dispatched functions

    @classmethod
    def icu_import(cls, source):
        try:
            import icu # new module name, 1.0 onwards
        except ImportError:
            try:
                import PyICU as icu # old module name, up to 0.9
            except ImportError:
                raise ImportError("'{0}' requires icu"
                                  " or PyICU module".format(source))
        return locals()
    
    @classmethod
    def icu_getAvailableLocales(cls):
        return icu.Locale.getAvailableLocales().keys
        
    @classmethod
    def icu_getLocaleNames(cls, code):
        locale = icu.Locale(code)
        return (locale.getDisplayName(), locale.getDisplayName(locale))

    # babel dispatched functions

    @classmethod
    def babel_import(cls, source):
        try:
            import babel
        except ImportError:
            raise ImportError("'{0}' requires babel module".format(source))
            
        return locals()

    @classmethod
    def babel_getAvailableLocales(cls):
        return babel.localedata.list

    @classmethod
    def babel_getLocaleNames(cls, code):
        locale = babel.Locale.parse(code)
        return (locale.english_name, locale.get_display_name())

    # pofiles dispatched functions
   
    @classmethod
    def pofiles_import(cls, source):
        import singularity.code.polib as polib
        import os as os

        return locals()

    @classmethod
    def pofiles_getAvailableLocales(cls):
        import os as os
        return [dirname.split("_", 1)[1]
                for file_dir in dirs.get_read_dirs("i18n")
                for dirname in os.listdir(file_dir)
                if osp.isdir(os.path.join(file_dir, dirname))
                and dirname.startswith("lang_")
                and any(filename == "messages.po" and osp.isfile(osp.join(file_dir, dirname, filename))
                    for filename in os.listdir(os.path.join(file_dir, dirname)))]

    @classmethod
    def pofiles_getLocaleNames(cls, code):
        pofile = dirs.get_readable_i18n_files("messages.po", code, localized_item=False, only_last=True)
        po = polib.pofile(pofile)
        return (po.metadata['Language-Name'], po.metadata['Language-Native-Name'])

def get_esdir(myname):
    mydir  = osp.dirname(myname)
    esdir  = osp.abspath(osp.join(osp.dirname(myname), '../..'))
    return esdir

def build_option_parser():
    description = '''Read language names from several sources and save them for E:S.

If run as a script, tries to read language names (in both English and
Native language) from several Locale info sources, like babel or PyICU. Then
merges this info with E:S' translation PO files headers, and save it by
updating a JSON file in data/languages.dat, which is later read by Options
Screen of E:S to present each one of the available languages in their own
native language.

This module is importable as well. In this case it only sets game's directory
and imports code.g. You can use the Locale class for all of its features.

In either case, modules 'icu', 'babel' and 'polib' are optional but highly
recommended.
'''

    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("-d", "--directory", dest="directory", default=None,
    help="Use E:S root directory DIR (default dirname(__file__)/../..)", metavar="DIR")

    return parser.parse_args()

def main(args):
    dirs.create_directories(False)

    # Get locale data from the first source that works
    languages = {}
    sources = Locale.getAvailableSources()
    for source in sources[:-1]: # we load 'pofiles' later
        try:
            languages = Locale.getLanguages(source=source)
            break
        except ImportError:
            continue

    datafile = dirs.get_readable_file_in_dirs("languages.json", "i18n")

    try:
        # load current data file and merge it
        languages.update(Locale.loadLanguagesData(datafile))
    except IOError:
        pass

    # also merge with translations file
    languages.update(Locale.getLanguages(source=sources[-1]))

    try:
        # Save updated data file
        Locale.saveLanguagesData(languages, datafile)

        print("{0:d} languages saved to {1}".format(len(languages),
                                                    osp.relpath(datafile)))
    except IOError as reason:
        sys.stderr.write("Could not save languages data file:"
                         " {0}\n".format(reason))

if __name__ == '__main__':
    args = build_option_parser()
    
    if (args.directory):
        esdir = osp.abspath(args.directory)
    else:
        esdir = get_esdir(sys.argv[0])
else:
    esdir = get_esdir(__file__)

sys.path.insert(0, esdir)

try:
    from singularity.code import g, dirs
except ImportError:
    sys.exit("Could not find game's code.g")

if __name__ == '__main__':
    try:
        sys.exit(main(args))
    except Exception as e:
        ex_type, ex, tb = sys.exc_info()
        traceback.print_tb(tb)
        sys.exit(1)
    except KeyboardInterrupt:
        pass
    except SystemExit as ex:
        raise ex
