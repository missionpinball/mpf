"""Python logging formatters."""
import json
import logging
import base64
from datetime import datetime


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code."""
    if isinstance(obj, datetime):
        serial = obj.isoformat()
        return serial
    raise TypeError("Type not serializable")


def format_time(record, datefmt=None):
    """Override default to use strftime, e.g. to get microseconds."""
    created = datetime.fromtimestamp(record.created)
    if not datefmt:
        datefmt = "%Y-%m-%dT%H:%M:%S.{:03f}%z".format(record.msecs)
    return created.strftime(datefmt)


class JSONFormatter(logging.Formatter):

    """A formatter that renders log records as JSON objects.

    Format: {"timestamp":"...", "level":"...", "name":"...", "message":"..."}
    """

    def format(self, record):
        """Encode log record as JSON."""
        log = {
            'timestamp': format_time(record, self.datefmt),
            'level': record.levelname,
            'name': record.name,
            'message': record.getMessage(),
            'ident': 'ServiceLog',
        }
        if record.exc_info:
            try:
                traceback = self.formatException(record.exc_info)
                traceback = base64.b64encode(traceback.encode('utf-8'))
                traceback = traceback.decode('utf-8')
            except TypeError:
                traceback = 'unable to serialize exception'
            log['traceback'] = traceback
        if isinstance(record.msg, dict):
            log['json_message'] = record.msg

        log = json.dumps(log, default=json_serial)
        return log
