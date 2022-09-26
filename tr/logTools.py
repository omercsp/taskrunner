import logging
import datetime
import inspect
from os.path import basename


__logger = None


class TrLogging(object):
    def __init__(self, log_file: str, log_level: int) -> None:
        self._logger = logging.getLogger()
        self._raw_formatter = logging.Formatter('%(message)s')
        self._default_formatter = logging.Formatter('%(levelname).1s %(message)s')
        self._file_handler = logging.FileHandler(log_file, encoding='utf-8')
        self._file_handler.setFormatter(self._default_formatter)
        self._file_handler.setLevel(log_level)
        self._logger.addHandler(self._file_handler)
        self._logger.setLevel(log_level)
        self.raw_format = False

    def set_raw_format(self) -> None:
        self.raw_format = True
        self._file_handler.setFormatter(self._raw_formatter)

    def set_default_format(self) -> None:
        self.raw_format = False
        self._file_handler.setFormatter(self._default_formatter)

    def is_enabled_for(self, level: int) -> bool:
        return self._logger.isEnabledFor(level)

    @staticmethod
    def _frame_str() -> str:
        frame = inspect.stack()[4]
        return f"[{basename(frame.filename)}:{frame.lineno}] {frame.function}".ljust(38, '.')

    def log(self, verbosity: int, msg_args) -> None:
        if not self._logger.isEnabledFor(verbosity):
            return
        if isinstance(msg_args, tuple) and len(msg_args) == 1:
            msg_args = str(msg_args[0])
        if isinstance(msg_args, str):
            if self.raw_format:
                self._logger.log(verbosity, msg_args)
            else:
                self._logger.log(verbosity, f"{self._frame_str()}: {msg_args}")
            return
        assert type(msg_args) is tuple
        if self.raw_format:
            self._logger.log(verbosity, msg_args[0].format(*msg_args[1:]))
        else:
            self._logger.log(
                verbosity, ("{}: " + msg_args[0]).format(self._frame_str(), *msg_args[1:]))


def start_raw_logging() -> None:
    global __logger
    if __logger is None:
        return
    __logger.set_raw_format()


def stop_raw_logging() -> None:
    global __logger
    if __logger is None:
        return
    __logger.set_default_format()


def raw_msg(msg) -> None:
    global __logger
    if __logger is None:
        return
    __logger.set_raw_format()
    __logger.log(logging.INFO, msg)
    __logger.set_default_format()


def blank(count=1) -> None:
    global __logger
    if __logger is None:
        return
    __logger.set_raw_format()
    for _ in range(0, count):
        __logger.log(logging.INFO, "")
    __logger.set_default_format()


def _process_msg_arr(verbosity: int, msg_args: tuple) -> None:
    global __logger
    if __logger is None:
        return
    __logger.log(verbosity, msg_args)


def init_logging(log_file: str, logfile_verbosity: int) -> None:
    global __logger
    assert __logger is None
    if not log_file:
        return
    __logger = TrLogging(log_file, logging.INFO if logfile_verbosity == 0 else logging.DEBUG)
    blank(2)
    __logger.set_raw_format()
    info("======================================================================")
    info("taskrunner: {}".format(datetime.datetime.now().strftime("%I:%M:%S on %B %d, %Y")))
    info("======================================================================")
    __logger.set_default_format()


def logging_enabled_for(level: int) -> bool:
    global __logger
    if not __logger:
        return False
    return __logger.is_enabled_for(level)


def verbose(*msg_args) -> None:
    _process_msg_arr(logging.DEBUG, msg_args)


def info(*msg_args) -> None:
    _process_msg_arr(logging.INFO, msg_args)


def warn(*msg_args) -> None:
    _process_msg_arr(logging.WARN, msg_args)


def error(*msg_args) -> None:
    _process_msg_arr(logging.ERROR, msg_args)


def error_and_print(msg) -> None:
    print(msg)
    _process_msg_arr(logging.ERROR, msg)


def warn_and_print(msg) -> None:
    print(msg)
    _process_msg_arr(logging.WARN, msg)
