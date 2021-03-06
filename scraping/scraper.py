"""
downloads and parses the data from amazon.de to store it in a orders.json file
"""
# pylint: disable=R0913
# pylint: disable=W0201
# pylint: disable=C0103

import datetime
import json
import logging
from typing import List, Tuple, Optional, Dict, Callable

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver import Firefox, FirefoxProfile
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from termcolor import colored

from scraping.CustomExceptions import PasswordFileNotFound, LoginError
from . import file_handler
from .data import Order, Item
from . import utils as ut

FILE_NAME: str = "orders.json"


class Scraper:
    """
    Scrapping instance, scrapes all Orders in the given year range and outputs it into FILE_NAME
    """

    def __init__(self, email: str, password: Optional[str], headless: bool, start: int, end: int, extensive: bool,
                 progress_observer_callback: Callable[[float], None] = None) -> None:
        assert email, "no E-Mail provided"
        assert '@' in email and '.' in email, "incorrect email layout"  # Todo replace by regex
        assert start <= end, "start year must be before end year"
        assert end >= 2010, "Amazon order history works only for years after 2009"
        assert end <= datetime.datetime.now().year, "End year can not be in the future"

        self.logger = logging.getLogger(__name__)
        self.progress_observer_callback: Callable[[float], None] = progress_observer_callback

        self.email = email
        self.password = password if password else file_handler.load_password()
        if not self.password:
            self.logger.error(colored("Password not given nor pw.txt found", 'red'))
            raise PasswordFileNotFound

        self.start_date: datetime.date = datetime.date(year=start, month=1, day=1)
        self.end_date: datetime.date = datetime.datetime.now().date() if end == datetime.datetime.now().year \
            else datetime.date(year=end, month=12, day=31)
        self.start_scraping_date: datetime.date = datetime.date(year=start, month=1, day=1)

        self.headless = headless
        self.extensive = extensive

        self.orders: List[Order] = []
        self.browser: WebDriver

        self._setup_scraping()
        self._get_orders()

        file_handler.save_file(FILE_NAME, json.dumps([order.to_dict() for order in self.orders]))
        self.browser.quit()

    def _notify_progress_observers(self, progress: float) -> None:
        if self.progress_observer_callback:
            self.progress_observer_callback(progress)

    def _setup_scraping(self) -> None:
        """
        prepares the WebDriver for scraping the data by:
            - setting up the WebDrive
            - log in the user with the given credentials
            - skipping the adding phone number dialog (should it appear)
        :raise LoginError if not possible to login
         """
        firefox_profile = FirefoxProfile()
        firefox_profile.set_preference("browser.tabs.remote.autostart", False)
        firefox_profile.set_preference("browser.tabs.remote.autostart.1", False)
        firefox_profile.set_preference("browser.tabs.remote.autostart.2", False)
        opts = Options()
        opts.headless = self.headless
        if opts.headless:
            self.logger.info(colored("Run in headless mode.", 'blue'))
        self.browser = Firefox(options=opts, firefox_profile=firefox_profile)
        self._navigate_to_orders_page()
        self._complete_sign_in_form()
        if not self._signed_in_successful():
            self.logger.error(colored("Couldn't sign in. Maybe your credentials are incorrect?", 'red'))
            print(colored("Couldn't sign in. Maybe your credentials are incorrect?", 'red'))
            self.browser.quit()
            raise LoginError
        self._skip_adding_phone_number()

    def _navigate_to_orders_page(self) -> None:
        """
        navigates to the orders page
        """
        self.browser.get('https://www.amazon.de/gp/css/order-history?ref_=nav_orders_first')

    def _complete_sign_in_form(self) -> None:
        """ searches for the sign in form enters the credentials and confirms
            if successful amazon redirects the browser to the previous site """
        try:
            email_input = self.browser.find_element_by_id('ap_email')
            email_input.send_keys(self.email)

            password_input = self.browser.find_element_by_id('ap_password')
            password_input.send_keys(self.password)

            self.browser.find_element_by_name('rememberMe').click()

            sign_in_input = self.browser.find_element_by_id('signInSubmit')
            sign_in_input.click()
        except NoSuchElementException:
            self.logger.error(colored("Error while trying to sign in, couldn't find all needed form elements", 'red'))
            print(colored("Error while trying to sign in, couldn't find all needed form elements", 'red'))

    def _signed_in_successful(self) -> bool:
        """ simple check if we are still on the login page """
        return bool(self.browser.current_url != "https://www.amazon.de/ap/signin")

    def _skip_adding_phone_number(self) -> None:
        """ find and click the 'skip adding phone number' button if found on the current page """
        try:
            skip_adding_phone_link = self.browser.find_element_by_id('ap-account-fixup-phone-skip-link')
            skip_adding_phone_link.click()
            self.logger.info(colored('skipped adding phone number', 'blue'))
        except NoSuchElementException:
            self.logger.info(colored('no need to skip adding phone number', 'blue'))

    def _is_custom_date_range(self) -> bool:
        """
        :param start: start date
        :param end: end date
        :return: whether the maximum date range is used or a custom user set range
        """
        return self.start_date.year != 2010 or self.end_date.year != datetime.datetime.now().year

    def _are_orders_for_year_available(self) -> bool:
        """
        checks if there are any orders in the current selected year
        :return: True if there were orders, False if not
        """
        return bool(self.browser.page_source.find('keine Bestellungen aufgegeben') == -1)  # No error!

    def _is_next_page_available(self) -> bool:
        """
        as long as the next page button exists there is a next page
        :return: True if there is a next page, False if not"""
        pagination_element = self.browser.find_element_by_class_name('a-pagination')
        try:
            return 'Weiter' not in pagination_element.find_element_by_class_name('a-disabled').text
        except NoSuchElementException:
            return True

    @staticmethod
    def _is_digital_order(order_id: str) -> bool:
        """
        checks if the order is digital (e.g. Amazon Video or Audio Book)
        :param order_id: the id of the order to check
        :return: True if order is digital, False if not
        """
        return order_id[:3] == 'D01'

    def _is_paging_menu_available(self) -> bool:
        """
        :returns: whether there are multiple pages for the current year by searching for a paging menu
        """
        try:
            return self.browser.find_element_by_class_name('a-pagination') is not None
        except NoSuchElementException:
            return False

    def _get_orders(self) -> None:
        """
        get a list of all orders in the given range (start and end year inclusive)
        to save network capacities it is checked if some orders got already fetched earlier in 'orders.json'

        """
        if self._is_custom_date_range():
            file_handler.remove_file(FILE_NAME)
        else:
            self.orders = file_handler.load_orders(FILE_NAME)

        if self.orders:
            self._scrape_partial()
        else:
            self._scrape_complete()
        self.orders = sorted(self.orders, key=lambda order: order.date)

    def _get_order_info(self, order_info_element: WebElement) -> Tuple[str, float, datetime.date]:
        """
        :param order_info_element:
        :returns: the OrderID, price and date
        """
        order_info_list: List[str] = [info_field.text for info_field in
                                      order_info_element.find_elements_by_class_name('value')]

        # value tags have only generic class names so a constant order in form of:
        # [date, price, recipient_address, order_id] or if no recipient_address is available
        # [date, recipient_address, order_id]
        # is assumed
        if len(order_info_list) < 4:
            order_id = order_info_list[2]
        else:
            order_id = order_info_list[3]

        # price is usually formatted as 'EUR x,xx' but special cases as 'Audible Guthaben' are possible as well
        order_price_str = order_info_list[1]
        if order_price_str.find('EUR') != -1:
            order_price = self._price_str_to_float(order_price_str)
        else:
            order_price = 0

        date_str = order_info_list[0]
        date = ut.str_to_date(date_str)
        return order_id, order_price, date

    def _scrape_complete(self) -> None:
        """
        scrapes all the data without checking for duplicates (when some orders already exist)
        """
        self.orders = self._scrape_orders()

    def _scrape_partial(self) -> None:
        """ scrape data until finding duplicates, at which point the scraping can be canceled since the rest
         is already there """
        self.orders = sorted(self.orders, key=lambda order: order.date)
        self.start_scraping_date = self.orders[-1].date

        scraped_orders: List[Order] = self._scrape_orders()

        # check for intersection of fetched orders
        existing_order_ids = list(map(lambda order: order.order_id, self.orders))
        new_orders: List[Order] = list(filter(lambda order: order.order_id not in existing_order_ids, scraped_orders))
        self.orders.extend(new_orders)

    def _scrape_orders(self) -> List[Order]:
        """
        :returns: a list of all orders in between given start year (inclusive) and end year (inclusive)
        """
        orders: List[Order] = []
        # order filter option 0 and 1 are already contained in option 2 [3months, 6months, currYear, lastYear, ...]
        start_index = 2 + (datetime.datetime.now().year - self.end_date.year)
        end_index = 2 + (datetime.datetime.now().year - self.start_scraping_date.year) + 1

        for order_filter_index in range(start_index, end_index):
            # open the dropdown
            ut.wait_for_element_by_id(self.browser, 'a-autoid-1-announce')
            self.browser.find_element_by_id('a-autoid-1-announce').click()

            # select and click on a order filter
            id_order_filter = f'orderFilter_{order_filter_index}'
            ut.wait_for_element_by_id(self.browser, id_order_filter)
            dropdown_element = self.browser.find_element_by_id(id_order_filter)
            dropdown_element.click()

            pages_remaining = self._are_orders_for_year_available()
            while pages_remaining:

                orders_on_page: List[Order] = self._scrape_page_for_orders()
                orders.extend(orders_on_page)

                current_date: datetime.date = orders_on_page[-1].date

                if orders_on_page and self.start_scraping_date > current_date:
                    break
                if self._is_paging_menu_available():
                    pagination_element = self.browser.find_element_by_class_name('a-pagination')
                else:
                    break

                pages_remaining = self._is_next_page_available()
                if pages_remaining:
                    next_page_link = pagination_element.find_element_by_class_name('a-last') \
                        .find_element_by_css_selector('a').get_attribute('href')
                    self.browser.get(next_page_link)

        return orders

    def _scrape_page_for_orders(self) -> List[Order]:
        """ :returns a list of all orders found on the currently open page """
        orders = []
        for order_element in self.browser.find_elements_by_class_name('order'):

            ut.wait_for_element_by_class_name(order_element, 'order-info', timeout=3)
            order_info_element = order_element.find_element_by_class_name('order-info')
            order_id, order_price, date = self._get_order_info(order_info_element)

            items = []
            # looking in an order there is a 'a-box' for order_info and and 'a-box' for each seller containing detailed
            # items info
            for items_by_seller in order_element.find_elements_by_class_name('a-box')[1:]:

                for index, item_element in enumerate(items_by_seller.find_elements_by_class_name('a-fixed-left-grid')):
                    seller = self._get_item_seller(item_element)
                    title, link = self._get_item_title(item_element)
                    item_price = order_price if self._is_digital_order(order_id) else \
                        self._get_item_price(item_element, index, order_element)
                    categories = self._get_item_categories(link) if self.extensive else dict()

                    items.append(Item(item_price, link, title, seller, categories))

            orders.append(Order(order_id, order_price, date, items))

            current_date: datetime.date = orders[-1].date
            progress: float = self._get_progress(current_date=current_date)
            self._notify_progress_observers(progress)

        return orders

    @staticmethod
    def _get_item_seller(item_element: WebElement) -> str:
        """
        :param item_element: the item div
        :return: returns the seller
        """
        try:
            seller_raw: str = item_element.text.split('durch: ')[1]
            seller: str = seller_raw.split('\n')[0]
            return seller
        except IndexError:
            return 'not available'

    @staticmethod
    def _get_item_title(item_element: WebElement) -> Tuple[str, str]:
        """
        :param item_element: the item div
        :return: returns the title and link of an item
        """
        item_elements = item_element.find_element_by_class_name('a-col-right') \
            .find_elements_by_class_name('a-row')
        item_title_element = item_elements[0]
        title = item_title_element.text
        try:
            link = item_title_element.find_element_by_class_name('a-link-normal').get_attribute('href')
        except NoSuchElementException:
            link = 'not available'

        return title, link

    def _get_item_price(self, item_element: WebElement, item_index: int, order_element: WebElement) -> float:
        """
        :param item_element: the item div
        :param item_index: the index of the item in the order
        :param order_element: the order div
        :return: returns the price of an item
        """
        try:
            item_price_str = item_element.find_element_by_class_name('a-color-price').text
            item_price = self._price_str_to_float(item_price_str)
        except (NoSuchElementException, ValueError):
            item_price = self._get_item_price_through_details_page(order_element, item_index)

        return item_price

    def _get_item_price_through_details_page(self, order_element: WebElement, item_index: int) -> float:
        """
        :param order_element: the order div
        :param item_index: the index of the item in the order
        :returns: the item price found on the order details page
        """
        item_price: float = 0

        try:
            order_details_link = order_element.find_element_by_class_name('a-link-normal').get_attribute('href')

            self.browser.execute_script(f'''window.open("{order_details_link}","_blank");''')
            self.browser.switch_to.window(self.browser.window_handles[1])
            if not ut.wait_for_element_by_class_name(self.browser, 'od-shipments'):
                return item_price

            od_shipments_element = self.browser.find_element_by_class_name('od-shipments')
            price_fields: List[WebElement] = od_shipments_element.find_elements_by_class_name('a-color-price')
            item_price = self._price_str_to_float(price_fields[item_index].text)

        except (NoSuchElementException, ValueError):
            item_price = 0
            self.logger.warning(colored(f'Could not parse price for order:\n{order_element.text}', 'yellow'))

        finally:
            self.browser.close()
            self.browser.switch_to.window(self.browser.window_handles[0])
        return item_price

    def _get_item_categories(self, item_link: str) -> Dict[int, str]:
        """
        :param item_link: the link to the item itself
        :returns: a dict with the categories and the importance as key
        """
        categories: Dict[int, str] = dict()

        self.browser.execute_script(f'''window.open("{item_link}","_blank");''')
        self.browser.switch_to.window(self.browser.window_handles[1])

        if ut.wait_for_element_by_id(self.browser, 'wayfinding-breadcrumbs_container'):
            categories = self._get_item_categories_from_normal()
            self.browser.close()
            self.browser.switch_to.window(self.browser.window_handles[0])
            return categories

        if ut.wait_for_element_by_class_name(self.browser, 'dv-dp-node-meta-info'):
            categories = self._get_item_categories_from_video()
            self.browser.close()
            self.browser.switch_to.window(self.browser.window_handles[0])
            return categories

        self.browser.close()
        self.browser.switch_to.window(self.browser.window_handles[0])

        return categories

    def _get_item_categories_from_normal(self) -> Dict[int, str]:
        """
        :return: the categories for a normal ordered item
        """
        categories = dict()
        categories_element = self.browser.find_element_by_id('wayfinding-breadcrumbs_container')
        for index, category_element in enumerate(categories_element.find_elements_by_class_name("a-list-item")):
            element_is_separator = index % 2 == 1
            if element_is_separator:
                continue
            depth = int(index // 2 + 1)
            categories[depth] = category_element.text
        return categories

    def _get_item_categories_from_video(self) -> Dict[int, str]:
        """
        :return: the genre of a movie as categories
        """
        categories = dict()
        text: str = self.browser.find_element_by_class_name('dv-dp-node-meta-info').text
        genre = text.split("\n")[0]
        genre_list: List[str] = genre.split(", ")
        genre_list[0] = genre_list[0].split(" ")[1]
        for index, genre in enumerate(genre_list):
            categories[index] = genre

        categories[len(genre_list)] = 'movie'
        return categories

    @staticmethod
    def _price_str_to_float(price_str: str) -> float:
        """
        converts the price str to a float value
        :param price_str: the price in string format as it is scraped
        :return: the price as float
        """
        return float((price_str[4:]).replace(',', '.'))

    def _get_progress(self, current_date: datetime.date) -> float:
        """
        calculates the progress by months
        :returns the progress in percentage
        """
        total_days = self.end_date.day - self.start_scraping_date.day + \
                     (self.end_date.month - self.start_scraping_date.month) * 31 + \
                     (self.end_date.year - self.start_scraping_date.year) * 12 * 31
        scraped_days = self.end_date.day - current_date.day + \
                       (self.end_date.month - current_date.month) * 31 + \
                       (self.end_date.year - current_date.year) * 12 * 31
        progress: float = scraped_days / total_days if total_days > 0 else 1.0
        return progress if progress <= 1 else 1.0
