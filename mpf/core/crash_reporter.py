"""Crash reporter for MPF.

Based on https://github.com/lobocv/crashreporter/tree/master (also MIT licensed).
"""
import inspect
import logging
import re
import traceback
import requests
from datetime import datetime
from pprint import pprint
from types import FunctionType, MethodType, ModuleType, BuiltinMethodType, BuiltinFunctionType

from mpf.exceptions.base_error import BaseError
from mpf._version import __version__


_repr = repr


def repr(object):
    """Return obj representation if possible."""
    try:
        return _repr(object)
    except Exception as e:
        logging.error(e)
        return 'String Representation not found'


def string_variable_lookup(tb, s):
    """
    Look up the value of an object in a traceback by a dot-lookup string.
    ie. "self.crash_reporter.application_name"
    Returns ValueError if value was not found in the scope of the traceback.
    :param tb: traceback
    :param s: lookup string
    :return: value of the
    """

    refs = []
    dot_refs = s.split('.')
    dot_lookup = 0
    dict_lookup = 1
    for ii, ref in enumerate(dot_refs):
        dict_refs = re.findall(r'(?<=[)(?:[\'"])([^\'\"]*)(?:[\'"])(?=])', ref)
        if dict_refs:
            bracket = ref.index('[')
            refs.append((dot_lookup, ref[:bracket]))
            refs.extend([(dict_lookup, t) for t in dict_refs])
        else:
            refs.append((dot_lookup, ref))

    scope = tb.tb_frame.f_locals.get(refs[0][1], ValueError)
    if scope is ValueError:
        return scope
    for lookup, ref in refs[1:]:
        try:
            if lookup == dot_lookup:
                scope = getattr(scope, ref, ValueError)
            else:
                scope = scope.get(ref, ValueError)
        except Exception as e:
            logging.error(e)
            scope = ValueError

        if scope is ValueError:
            return scope
        elif isinstance(scope, (FunctionType, MethodType, ModuleType, BuiltinMethodType, BuiltinFunctionType)):
            return ValueError
    return scope


def get_object_references(tb, source, max_string_length=1000):
    """
    Find the values of referenced attributes of objects within the traceback scope.
    :param tb: traceback
    :return: list of tuples containing (variable name, value)
    """
    referenced_attr = set()
    for line in source.split('\n'):
        referenced_attr.update(set(re.findall(
            r'[A-z]+[0-9]*\.(?:[A-z]+[0-9]*\.?)+(?!\')(?:\[(?:[\'"]).*(?:[\'"])])*(?:\.[A-z]+[0-9]*)*', line)))
    referenced_attr = sorted(referenced_attr)
    info = []
    for attr in referenced_attr:
        v = string_variable_lookup(tb, attr)
        if v is not ValueError:
            ref_string = format_reference(v, max_string_length=max_string_length)
            info.append((attr, ref_string))
    return info


def get_local_references(tb, max_string_length=1000):
    """
    Find the values of the local variables within the traceback scope.
    :param tb: traceback
    :return: list of tuples containing (variable name, value)
    """
    if 'self' in tb.tb_frame.f_locals:
        _locals = [('self', repr(tb.tb_frame.f_locals['self']))]
    else:
        _locals = []
    for k, v in tb.tb_frame.f_locals.items():
        if k == 'self':
            continue
        try:
            vstr = format_reference(v, max_string_length=max_string_length)
            _locals.append((k, vstr))
        except TypeError:
            pass
    return _locals


def format_reference(ref, max_string_length=1000):
    """
    Converts an object / value into a string representation to pass along in the payload
    :param ref: object or value
    :param max_string_length: maximum number of characters to represent the object
    :return:
    """
    def _pass(*args):
        return None
    _numpy_info = ('dtype', 'shape', 'size', 'min', 'max')
    additional_info = []
    if isinstance(ref, (list, tuple, set, dict)):
        # Check for length of reference
        length = getattr(ref, '__len__', _pass)()
        if length is not None:
            additional_info.append(('length', length))

    if additional_info:
        v_str = ', '.join(['%s: %s' % a for a in additional_info] + [repr(ref)])
    else:
        v_str = repr(ref)

    if len(v_str) > max_string_length:
        v_str = v_str[:max_string_length] + ' ...'

    return v_str


def analyze_traceback(tb, inspection_level=None, limit=None):
    """
    Extract trace back information into a list of dictionaries.
    :param tb: traceback
    :return: list of dicts containing filepath, line, module, code, traceback level and source code for tracebacks
    """
    info = []
    tb_level = tb
    extracted_tb = traceback.extract_tb(tb, limit=limit)
    for ii, (filepath, line, module, code) in enumerate(extracted_tb):
        func_source, func_lineno = inspect.getsourcelines(tb_level.tb_frame)

        d = {"file": filepath,
             "error_line_number": line,
             "module": module,
             "error_code": code,
             "module_line_number": func_lineno,
             "custom_inspection": {},
             "source_code": ''}
        if inspection_level is None or len(extracted_tb) - ii <= inspection_level:
            # Perform advanced inspection on the last `inspection_level` tracebacks.
            d['source_code'] = ''.join(func_source)
            d['local_variables'] = get_local_references(tb_level)
            d['object_variables'] = get_object_references(tb_level, d['source_code'])
        tb_level = getattr(tb_level, 'tb_next', None)
        info.append(d)

    return info


def _send_crash_report(report):
    r = requests.post("http://localhost:8080/report", json=report)
    if r.status_code != 200:
        print("Failed to send report. Got response code {}. Error: {}", r.status_code, r.content)
    else:
        print(r.content.decode())


def report_crash(e: BaseException, location, config):
    """Report crash."""
    log = logging.getLogger("crash_reporter")
    try:
        trace = analyze_traceback(e.__traceback__)
    except BaseException:
        log.exception(
            "Failed to generate crash report. Please report this in our forum!")
        return

    report = {
        'timestamp': str(datetime.now()),
        'location': location,
        'exception_type': str(e.__class__),
        'trace': trace,
        'version': __version__
    }

    if isinstance(e, BaseError):
        report["error_no"] = e.get_error_no()
        report["error_context"] = e.get_context()
        report["error_logger_name"] = e.get_logger_name()

    reporting_mode = config.get("mpf", {}).get("report_crashes", "ask")

    if reporting_mode == "always":
        log.info("Will report crash as \"report_crashes\" mode is \"%s\"", reporting_mode)
        _send_crash_report(report)
    elif reporting_mode == "ask":
        while True:
            print("\n----------------------------------------------------")
            print("MPF CRASH REPORTER")
            print("----------------------------------------------------")
            print("You can choose to anonymously report the above incident to the MPF team to "
                  "let us know for this particular issue.")
            print("Enter 'show' to see exactly what will be send.")
            print("This information will be used to improve MPF (improve ergonomics and fix issues).")
            print("You can set this permanently in your config using mpf:report_crashes: \"never\" or \"always\"")
            print("----------------------------------------------------\n")
            try:
                response = input("Do you want to report the crash to the MPF team (yes/no/show)? ")
            except KeyboardInterrupt:
                response = "no"
            if response in ("show", "s"):
                print("Full crash report to be send:\n\n")
                pprint(report, width=160)
            elif response in ("n", "no"):
                print("Will not send report.")
                return
            elif response in ("y", "yes"):
                print("Will send report.")
                _send_crash_report(report)
                return
            else:
                print("Invalid input")
    else:
        log.info("Will not report crash as \"report_crashes\" mode is \"%s\"", reporting_mode)
        return
