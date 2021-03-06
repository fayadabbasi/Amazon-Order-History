"""
helper functions
"""
# pylint: disable=W1203

import datetime
import logging
import os
import webbrowser
from collections import OrderedDict
from enum import Enum
from typing import List, Dict

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait
from termcolor import colored

MONTHS: List[str] = ['Januar', 'Februar', 'März', 'April', 'Mai', 'Juni', 'Juli', 'August', 'September', 'Oktober',
                     'November', 'Dezember']


class OptionType(Enum):
    """
    Enum if an argument is required or optional
    """
    REQUIRED = 1
    OPTIONAL = 0


class ArgumentType(Enum):
    """
    Enum for arguments
    """
    FLAG = 1
    SINGLE_STRING = 0
    MULTI_STRING = 2
    SINGLE_INT = 3
    MULTI_INT = 4


LOGGER = logging.getLogger(__name__)


def is_int_parsable(int_str: str) -> bool:
    """
    :param int_str: the string value that shall be parsed
    :return: if it was parseable
    """
    try:
        int(int_str)
        return True
    except ValueError:
        return False


def str_to_date(date_str: str) -> datetime.date:
    """ expects a date str formatted in german date format as 'day. month year' e.g. '4. September 2018' """
    day_str, month_str, year_str = date_str.split(' ')

    day = int(day_str.replace('.', ''))
    month = MONTHS.index(month_str) + 1
    year = int(year_str)

    return datetime.date(day=day, month=month, year=year)


def serialize_date(obj: object) -> str:
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    raise TypeError("Type %s not serializable" % type(obj))


def wait_for_element_by_class_name(browser: WebDriver, class_name: str, timeout: float = 3) -> bool:
    """ wait the specified timout for a element to load
        :returns true if element was found
    """
    try:
        WebDriverWait(browser, timeout).until(ec.presence_of_element_located((By.CLASS_NAME, class_name)))
        return True
    except TimeoutException:
        LOGGER.warning(colored(f'Skipping, loading for "{class_name}" too much time! (>{timeout}sec)', 'yellow'))
        return False


def wait_for_element_by_id(browser: WebDriver, element_id: object, timeout: object = 3) -> bool:
    """
    wait the specified timout for a element to load

    :return True if element was found in the given timeout and False otherwise
    """
    try:
        WebDriverWait(browser, timeout).until(ec.presence_of_element_located((By.ID, element_id)))
        return True
    except TimeoutException:
        LOGGER.warning(colored(f'Skipping, loading for "{element_id}" took too much time! (>{timeout}sec)', 'yellow'))
        return False


def sort_dict_by_key(dic: Dict) -> OrderedDict:
    """
    sorts a dict by its keys

    :param dic: the dictionary to sort by keys
    :return: a ordered dict with sorted keys
    """
    return_dict: OrderedDict = OrderedDict()

    keys = list(dic.keys())
    keys.sort()

    for key in keys:
        return_dict[key] = dic[key]

    return return_dict


def open_webbrowser(url: str) -> None:
    """
    Opens a webbrowser and redirects the stdout and stderr. This is because they will occupy the stdout/stderr
    as long as the webbrowser is open
    :param self:
    :param url: the url to open
    """
    _stderr: int = os.dup(2)
    os.close(2)
    _stdout: int = os.dup(1)
    os.close(1)
    fd: int = os.open(os.devnull, os.O_RDWR)
    os.dup2(fd, 2)
    os.dup2(fd, 1)
    try:
        webbrowser.open(url)
        LOGGER.info(colored(f'webbrowser successfully opened {url}', 'blue'))
    finally:
        os.close(fd)
        os.dup2(_stderr, 2)
        os.dup2(_stdout, 1)
        os.close(_stderr)
        os.close(_stdout)
