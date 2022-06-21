#!/usr/bin/env python

#               all | foil | art | signed | alter
# -------------------------------------------------
# text        |  x  |  x   |     |    x   |
# multiverse  |     |      |     |        |
# csv         |  x  |  x   |     |    x   |
# printable   |  x  |  x   |  x  |    ?   |

import re, os, json, scrython, time

# Use local scryfall database for this
def get_default_collectors_number(name, set_abbr):
    # Tappedout does Turn / Burn
    # Scryfall  does Turn // Burn
    if '/' in name and '//' not in name:
        name = name.replace('/', '//')
    cards = [card for card in scryfall_db if card['name'].lower() == name.lower() and card['set'].lower() == set_abbr.lower()]
    # Cards with multiple faces, adventure cards, split cards, etc. will have a combined name
    # so we have to check the faces
    if len(cards) == 0:
        cards_with_faces = [card for card in scryfall_db if card.get('card_faces') != None]
        cards = [card for card in cards_with_faces if card['set'].lower() == set_abbr.lower() and card['card_faces'][0]['name'].lower() == name.lower()]
    if len(cards) == 0:
        print(cards)
        print(name, set_abbr)
    default = min(cards, key=lambda card: card['collector_number'])['collector_number']
    assert type(default) == str
    assert default != ''
    return default


scryfall_db = []

with open('shrunk.json', 'r') as db:
    scryfall_db = json.load(db)

with open('printable.txt', 'r') as f:
    with open('output.csv', 'w') as out:
        out.write(f"Quantity|Name|Set|Collector Number|Variation|List|Foil|Promo Pack|Prerelease|Language|Scryfall ID\n")
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
            promo_pack = False
            prerelease = False
            # Collector numbers can have non-numbers in them
            if variation:
                if variation.isnumeric():
                    collector_number = variation
                    variation = None
                elif variation == 'PromoPack':
                    collector_number = get_default_collectors_number(name, set_abbr)
                    promo_pack = True
                    variation = None
                else:
                    raise Exception(f"Unhandled variation type. Variation was {variation}. Card was {name} {set_abbr}")
            else:
                collector_number = get_default_collectors_number(name, set_abbr)
            # 6 wraps around the *'s
            foil_or_language = matches.group(7)
            foil = False
            language = "EN"
            the_list = False
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
            card = [card for card in scryfall_db if card['set'].lower() == set_abbr.lower() and card['collector_number'] == collector_number]
            assert len(card) == 1
            card = card[0]
            scryfall_id = card['id']
            out.write(f"{quantity}|{name}|{set_abbr}|{collector_number}|{variation}|{the_list}|{foil}|{promo_pack}|{prerelease}|{language}|{scryfall_id}\n")

# Sanity checks
import csv
with open('output.csv', 'r') as out:
    output_reader = csv.DictReader(out, delimiter='|')
    total_cards = 0
    for row in output_reader:
        total_cards += int(row["Quantity"])
        assert(len(row.keys()) == 11)

assert total_cards == 5668



