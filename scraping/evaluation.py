import os
from functools import reduce

import json
from typing import List, Dict

import numpy as np
import matplotlib.pyplot as plt

from scraping import utils
from scraping.Data import Order


def main():
    print(os.path.abspath('../orders.jons'))
    if os.path.exists('../orders.json'):
        with open('../orders.json') as file:
            data = json.load(file)
    else:
        print("orders.json not found")
        return

    if not data:
        return

    orders = []
    for order_dict in data:
        orders.append(Order.from_dict(order_dict))

    print(f'counted {get_order_count(orders)} orders with a total price of {get_total(orders)} Euro')
    print(f'most expensive order was: {get_most_expensive_order(orders)}')
    print(f'audible total: {get_audible_total(orders)}')

    #plot_expenses_by_year(orders)
    plot_audible_by_month(orders)
    plot_all(orders)


def plot_all(orders: List[Order]):
    amazon_totals_by_year = utils.sort_dict_by_key(get_total_by_year(orders))
    years = tuple(amazon_totals_by_year.keys())
    bar_amount = np.arange(len(years))

    audible_totals_by_year = get_audible_total_by_year(orders)
    for year in amazon_totals_by_year.keys():
        if year not in audible_totals_by_year.keys():
            audible_totals_by_year[year] = 0
    audible_totals_by_year = utils.sort_dict_by_key(audible_totals_by_year)

    amazon_plot = plt.bar(bar_amount, list(amazon_totals_by_year.values()), align='center', alpha=0.5)
    audible_plot = plt.bar(bar_amount, list(audible_totals_by_year.values()), align='center', alpha=0.5)

    plt.ylabel('Amount in Euro')
    plt.xlabel('Year')
    plt.xticks(bar_amount, years)
    plt.legend((amazon_plot[0], audible_plot[0]), ('Amazon Purchases', 'Audible Purchases'))

    plt.show()


def plot_expenses_by_year(orders: List[Order]):
    totals_by_year = get_total_by_year(orders)
    objects = tuple(totals_by_year.keys())
    y_pos = np.arange(len(objects))

    plt.bar(y_pos, list(totals_by_year.values()), align='center', alpha=0.5)
    plt.xticks(y_pos, objects)
    plt.ylabel('Amount in Euro')
    plt.xlabel('Year')
    plt.title('Amazon Purchases')

    plt.show()


def plot_audible_by_month(orders: List[Order]):
    totals_by_year = get_audible_total_by_year(orders)
    objects = tuple(totals_by_year.keys())
    y_pos = np.arange(len(objects))

    plt.bar(y_pos, list(totals_by_year.values()), align='center', alpha=0.5)
    plt.xticks(y_pos, objects)
    plt.ylabel('Amount in Euro')
    plt.xlabel('Year')
    plt.title('Audible Purchases')

    plt.show()


def get_total_by_year(orders: List[Order]) -> Dict[int, float]:
    totals_by_year = dict()
    for order in orders:
        if order.date.year not in totals_by_year:
            totals_by_year[order.date.year] = 0
        totals_by_year[order.date.year] += order.price
    return totals_by_year


def get_total(orders: List[Order]):
    return reduce((lambda total, order: total + order.price), orders, 0)


def get_most_expensive_order(orders: List[Order]):
    max_order_price = max(map(lambda order: order.price, orders))
    return list(filter(lambda order: order.price == max_order_price, orders))


def get_order_count(orders: List[Order]):
    return len(orders)


def get_audible_total(orders: List[Order]):
    audible_orders = filter(lambda order: order.order_id[:3] == 'D01', orders)
    total = sum(map(lambda order: order.price, audible_orders))
    return total


def order_contains_audible_items(order: Order) -> bool:
    for item in order.items:
        if "Audible" in item.title:
            return True
    return False


def get_audible_total_by_year(orders: List[Order]) -> Dict[int, float]:
    audible_orders = [order for order in orders if order_contains_audible_items(order)]
    orders_by_year = {}
    for order in audible_orders:
        if order.date.year not in orders_by_year.keys():
            orders_by_year[order.date.year] = 0
        orders_by_year[order.date.year] += order.price
    return orders_by_year


if __name__ == '__main__':
    main()