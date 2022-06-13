#!/usr/bin/env python

#               all | foil | art | signed | alter
# -------------------------------------------------
# text        |  x  |  x   |     |    x   |
# multiverse  |     |      |     |        |
# csv         |  x  |  x   |     |    x   |
# printable   |  x  |  x   |  x  |    ?   |

import re, os, json, scrython, time

def get_default_collectors_number(name, set_abbr):
    oracle_id = scrython.Named(exact=name).oracle_id()
    page = 1
    cards = scrython.Search(q=f'oracle_id:{oracle_id}', unique='prints', page=page)
    total_cards = cards.total_cards()
    data = cards.data()

    while cards.has_more():
        page += 1
        time.sleep(.1)
        cards = scrython.Search(q=f'oracle_id:{oracle_id}', unique='prints', page=page)
        data.extend(cards.data())

    assert len(data) == total_cards
    in_correct_set = [card for card in data if card['set'].lower() == set_abbr.lower()]

    default = min(in_correct_set, key=lambda card: card['collector_number'])['collector_number']
    assert type(default) == str
    assert default != ''
    return default


if not os.path.exists('collector_numbers.json'):
    os.mknod('collector_numbers.json')

collector_numbers = {}

if os.path.getsize('collector_numbers.json') > 0:
    with open('collector_numbers.json', 'r') as collector_numbers_file:
        collector_numbers = json.load(collector_numbers_file)
try:
    with open('printable.txt', 'r') as f:
        with open('output.csv', 'w') as out:
            out.write(f"Quantity|Name|Set|Collector Number|Variation|List|Foil|Promo Pack|Prerelease|Language\n")
            for line in f:
                pattern = r'^([0-9]+)x ([^(]+) \(([A-Z0-9]{3,4})(:([A-Za-z0-9]+))?\)( \*(f|list|pp|f-pp|f-pre|[A-Z]{2})\*)?$'
                matches = re.match(pattern, line)
                if matches == None:
                    raise Exception(f"Input is in wrong format. Expected to match '{pattern}' but couldn't. Input was {line}")

                quantity = matches.group(1)
                name = matches.group(2)
                set_abbr = matches.group(3)
                if set_abbr == '000':
                    if name == 'Arbor Elf':
                        set_abbr = 'pw21'
                    elif name == 'Archfiend of Ifnir':
                        set_abbr = 'pakh'
                    elif name == 'Ember Swallower':
                        set_abbr = 'pths'
                    elif name == 'Mind Stone':
                        set_abbr = 'pw21'
                    else:
                        raise Exception(f"Unhandled 000 set. {name}")
                # tappedout and scryfall use different codes
                if set_abbr == 'MYS1':
                    set_abbr = 'MB1'
                elif set_abbr == 'EO2':
                    set_abbr = 'E02'
                elif set_abbr == 'PFL':
                    set_abbr = 'PD2'
                # These appear to be just wrong in tappedout?
                elif set_abbr == 'TSB':
                    if name in ['Swamp', 'Aarakocra Sneak']:
                        set_abbr = 'CLB'
                # 3 is a wrapper to make the varaition optional
                variation = matches.group(5)
                collector_number = None
                # Collector numbers can have non-numbers in them
                # this might not work :shrug:
                if variation:
                    if variation.isnumeric():
                        collector_number = variation
                        variation = None
                    else:
                        print(f"WARNING: Variation isn't numeric {name} {variation}")
                else:
                    key = f"{name}|{set_abbr}"
                    if collector_numbers.get(key) == None:
                        print(f"Looking up collector_number for {name} {set_abbr}")
                        time.sleep(.1)
                        collector_numbers[key] = get_default_collectors_number(name, set_abbr)
                    collector_number = collector_numbers[key]
                # 6 wraps around the *'s
                foil_or_language = matches.group(7)
                foil = False
                language = "EN"
                the_list = False
                promo_pack = False
                prerelease = False
                if foil_or_language:
                    if foil_or_language == 'f':
                        foil = True
                    elif foil_or_language == 'list':
                        the_list = True
                    elif foil_or_language == 'pp':
                        promo_pack = True
                    elif foil_or_language == 'f-pp':
                        foil = True
                        promo_pack = True
                    elif foil_or_language == 'f-pre':
                        foil = True
                        prerelease = True
                    else:
                        language = foil_or_language

                out.write(f"{quantity}|{name}|{set_abbr}|{collector_number}|{variation}|{the_list}|{foil}|{promo_pack}|{prerelease}|{language}\n")
except BaseException as e:
    with open('collector_numbers.json', 'w') as collector_numbers_file:
        json.dump(collector_numbers, collector_numbers_file)
    raise e

with open('collector_numbers.json', 'w') as collector_numbers_file:
    json.dump(collector_numbers, collector_numbers_file)

# Sanity checks
import csv
with open('output.csv', 'r') as out:
    output_reader = csv.DictReader(out, delimiter='|')
    total_cards = 0
    for row in output_reader:
        total_cards += int(row["Quantity"])
        assert(len(row.keys()) == 10)

assert total_cards == 5668



