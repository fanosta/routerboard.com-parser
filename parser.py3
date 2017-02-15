#!/usr/bin/python3

import collections
import json

import locale

from lxml import html
from lxml.cssselect import CSSSelector

import requests
import re

locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')


class FrozenDict(collections.Mapping):
    """An immutable dict, see http://stackoverflow.com/a/2704866"""

    def __init__(self, *args, **kwargs):
        self._d = dict(*args, **kwargs)
        self._hash = None

    def __iter__(self):
        return iter(self._d)

    def __len__(self):
        return len(self._d)

    def __getitem__(self, key):
        return self._d[key]

    def __hash__(self):
        # It would have been simpler and maybe more obvious to
        # use hash(tuple(sorted(self._d.iteritems()))) from this discussion
        # so far, but this solution is O(n). I don't know what kind of
        # n we are going to run into, but sometimes it's hard to resist the
        # urge to optimize when it will gain improved algorithmic performance.
        if self._hash is None:
            self._hash = 0
            for pair in self .iteritems():
                self._hash ^= hash(pair)
        return self._hash


def parse_product(element):
    select_name = CSSSelector('[itemprop=name]')
    select_url = CSSSelector('[itemprop=url]')
    select_price = CSSSelector('[itemprop=price]')
    select_desc = CSSSelector('.product_descr p')

    name = select_name(element)
    url = select_url(element)
    price = select_price(element)
    desc = select_desc(element)

    assert len(name) == 1
    assert len(desc) == 1
    assert len(price) == 1
    assert len(url) == 1

    if (len(name) != 1 or len(desc) != 1 or len(price) != 1 or len(url) != 1):
        return None

    return (name[0].text.strip(), {
        'url': url[0].get('href'),
        'desc': re.sub(re.compile(r"\r\s*"), "\n", desc[0].text.strip()),
        'price': locale.atof(price[0].get('content')),
    })


def get_products():
    page = requests.get("https://routerboard.com")
    root = html.fromstring(page.content)

    select_products = CSSSelector(".product_entry:not(.hideBox):not(.hist)")

    products = select_products(root)

    return {name: details for name, details in (
        parse_product(x) for x in products)}


def format_product(name, product):
    return "%s: %s\n  %s\n  %s" % (
        name,
        locale.currency(product['price']),
        product['desc'].replace("\n", "\n  "),
        product['url']
    )

if __name__ == '__main__':
    settings = json.loads(open("settings.json").read())

    db_old = None
    try:
        db_file = open(settings['db_file'], 'r')
        db_old = json.load(db_file)
    except (json.JSONDecodeError, FileNotFoundError):
        pass

    db_new = get_products()
    db_file = open(settings['db_file'], 'w')

    if db_old is not None:
        for name in (db_new.keys() - db_old.keys()):
            print("+ %s\n" % format_product(name, db_new[name]))
        for name in (db_old.keys() - db_new.keys()):
            print("- %s\n" % format_product(name, db_old[name]))

    json.dump(db_new, db_file, sort_keys=True, indent=4)

    db_file.close()
