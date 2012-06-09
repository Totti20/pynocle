#!/usr/bin/env python
"""
Utilities for pynocle project.
"""

import abc
import fnmatch
import os
import traceback


class PynocleError(Exception):
    """Base class for custom exception hierarchy."""
    pass


class AggregateError(PynocleError):
    """Error that holds a group of other errors.  Exceptions should be a
    collection of sys.exc_infos.  It is expected to raise this error with
    the first aggregate's traceback.
    """
    def __init__(self, exc_infos):
        self.exc_infos = exc_infos
        formatted = [''.join(traceback.format_exception(*ei))
                     for ei in exc_infos]
        self.formatted_exc_infos = '\n'.join(formatted)
        PynocleError.__init__(self)

    def __str__(self):
        return 'Errors:\n{0}\n{1}{0}'.format('-' * 10,
                                             self.formatted_exc_infos)

    __repr__ = __str__


class MissingDependencyError(PynocleError):
    """If you hit this exception, it means you tried to use a feature
    in pynocle that required a dependency you weren't set up with!
    """
    pass


class IReportFormatter(object):
    """General abc for all report formatters."""
    __metaclass__ = abc.ABCMeta

    def outstream(self):
        """Returns a file-like object to write to.

        If subclasses provide a _outstream attribute, this method will return that, otherwise override it.
        """
        #noinspection PyUnresolvedReferences
        return self._outstream


    @abc.abstractmethod
    def format_report_header(self):
        """Writes the information that should be at the top of the report to self.outstream()."""

    def format_report_footer(self):
        """Writes the information that should be at the bottom of the report.  Usually a no-op."""

    @abc.abstractmethod
    def format_data(self, data):
        """Writes data to self.outstream()"""


def write_report(filename, data, formatter_factory):
    """Opens a stream for the file at filename and writes the header/data/footer using the provided formatter.

    filename: Filename of the report.
    data: Data to write into the report.
    formatter_factory: Callable that takes the filestream at filename and returns an IReportFormatter.
    """
    with open(filename, 'w') as f:
        fmt = formatter_factory(f)
        fmt.format_report_header()
        fmt.format_data(data)
        fmt.format_report_footer()


class ExtensionFormatterRegistry(object):
    def __init__(self, mapping=()):
        self.mapping = dict(mapping)

    def Register(self, ext, value):
        self.mapping[ext] = value

    def GetFormatter(self, ext, default=None):
        return self.mapping.get(ext, default)

    def GetFormatterFactory(self, ext, default=None, **kwargs):
        result = self.GetFormatter(ext, default)
        if not result:
            return result
        return lambda stream: result(stream, **kwargs)


class _FindAll:
    """Helper state class for getting all filenames from a group of files and folders."""
    def __init__(self, files_and_folders, pattern):
        self.processed_files = []
        self.processed_files_set = set()
        self.pattern = pattern
        self.findall(map(os.path.abspath, files_and_folders))

    def not_yet_processed(self, filename):
        return filename not in self.processed_files_set

    def findfiles(self, filenames):
        """Updates processed_files with new python files in filenames."""
        if not filenames:
            return
        files = fnmatch.filter(filenames, self.pattern)
        unique = filter(self.not_yet_processed, files)
        self.processed_files.extend(unique)
        self.processed_files_set.update(unique)

    def findall(self, files_and_folders):
        """Counts the lines of code recursively in all files and folders."""
        self.findfiles(filter(os.path.isfile, files_and_folders))
        for d in filter(os.path.isdir, files_and_folders):
            paths = map(lambda x: os.path.join(d, x), os.listdir(d))
            self.findall(paths)


def find_all(files_and_folders, pattern='*.py'):
    """Given a collection of files and folders, return all the absolute path of files in the collection
    and recursively under any folders in the collection that fnmatch pattern.
    """
    fa = _FindAll(files_and_folders, pattern)
    return fa.processed_files

def splitpath_root_file_ext(path):
    """Returns a tuple of path, pure filename, and extension."""
    head, tail = os.path.split(path)
    filename, ext = os.path.splitext(tail)
    return head, filename, ext

def flatten(node, getchildren):
    """Return a generator that walks node and children recursively.

    node: Any node that has children.
    getchildren: A callable that takes node and returns a collection of children that will be walked recursively.
    """
    yield node
    for child in getchildren(node):
        for gc in flatten(child, getchildren):
            yield gc

def swap_keys_and_values(d):
    """Returns a new dictionary where keys are d.values() and values are d.keys().  If there are duplicate values,
    raises a KeyError.
    """
    result = dict(zip(d.values(), d.keys()))
    if len(d) != len(result):
        raise KeyError, 'There were duplicate values in argument.  Values: %s' % d.values()
    return result

def prettify_path(path, leading=None):
    """If path begins with leading, strip it and remove any new leading slashes.  Also removes the extension and ensures
    all seps are os.sep.

    leader: If None, cwd.
    """
    leading = (leading or os.getcwd()).replace(os.altsep, os.sep)
    s = os.path.splitext(path.replace(os.altsep, os.sep))[0]
    if s.startswith(leading):
        s = s.replace(leading, '')
    return s.strip(os.sep)