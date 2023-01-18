#!/usr/bin/env python

#               all | foil | collector number | signed | prerelease | alter
# ---------------------------------------------------------------------------
# text        |  x  |  x   |                  |    x   |            |
# multiverse  |     |      |   not directly   |        |            |
# csv         |  x  |  x   |        x         |    x   |     x      |
# printable   |  x  |  x   |        x         |        |     x      |

# Lightning Helix STA:125 used to show up as STA:62 in csv. This seems to be fixed, but we should watch out for errors in the csv

import re, psycopg, csv, config

def import_data(user: str):
    con = psycopg.connect(user = config.get('DB_USER'), password = config.get('DB_PASSWORD'), host = config.get('DB_HOST'), port = config.get('DB_PORT'))
    cur = con.cursor()

    res = cur.execute('SELECT ID FROM Users WHERE Username = %s', (user,))
    user_id = res.fetchone()[0]

    rows_to_insert = []

    res = cur.execute('SELECT ID, Finish FROM Finishes')
    finishes = res.fetchall()

    # Map finish -> id
    finish_id_map= {}

    scryfall_to_db_condition = {
        'NM': 'Near Mint',
        'SL': 'Lightly Played',
        'MP': 'Moderately Played',
        'HP': 'Heavily Played'
    }

    for finish in finishes:
        finish_id_map[finish[1]] = finish[0]

    # Use local scryfall database for this
    def get_default_collectors_number(name: str, set_abbr: str) -> str:
        # Tappedout does Turn / Burn
        # Scryfall  does Turn // Burn
        if '/' in name and '//' not in name:
            name = name.replace('/', '//')
        # Tappedout uses an inconsistent number of _
        # Scryfall always uses _____
        name = re.sub('___+', '_____', name)
        # Tappedout has a typo
        if name == 'Psuedodragon Familiar':
            name = 'Pseudodragon Familiar'
        # Tappedout doesn't care about ñ
        if name == 'Robo-Pinata':
            name = 'Robo-Piñata'

        res = cur.execute('SELECT c.CollectorNumber FROM Cards c INNER JOIN Sets s ON c.SetID = s.ID WHERE lower(c.name) = %s AND s.Code = %s', (name.lower(), set_abbr))
        collector_numbers = [tup[0] for tup in res.fetchall()]

        # We can fail to find a card with the given name if the card has multiple faces
        # Tappedout calls the card the name of the main face, scryfall calls it <main_face> // <other_face>
        if len(collector_numbers) == 0:
            res = cur.execute('SELECT c.CollectorNumber FROM Cards c INNER JOIN Faces f ON f.CardID = c.ID WHERE lower(f.Name) = %s', (name.lower(),))
            collector_numbers = [tup[0] for tup in res.fetchall()]

        # If any collector_numbers are numeric
        if any([collector_number.isnumeric() for collector_number in collector_numbers]):
            # Filter out the cards with non-numeric collector numbers
            numeric_collector_numbers = [collector_number for collector_number in collector_numbers if collector_number.isnumeric()]
            # Sort by collector number as int (sorting by str results in '125' < '64')
            default = min(numeric_collector_numbers, key=lambda collector_number: int(collector_number))
        # ex. Unfinity attractions have all non-numeric collector numbers
        else:
            if len(collector_numbers) == 0:
                print(name, set_abbr)
            default = min(collector_numbers)

            if len(collector_numbers) > 1:
                # Tappedout doesn't seem to differentiate these so print a warning that we've defaulted to
                # the first variation
                print(f"WARNING: Tappedout might not differentiate between the versions of {name} ({set_abbr}), defaulting to collector number {default}.")

        if len(collector_numbers) == 0:
            print(collector_numbers)
            print(name, set_abbr)
            exit(1)

        assert type(default) == str
        assert default != ''
        return default

    with open('export.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            quantity = row['Qty']
            name = row['Name']
            set_abbr = row['Set'].lower()
            # "Set Number" sometimes isn't a collector number
            variation = row['Set Number']
            if set_abbr == '000':
                if name == 'Arbor Elf':
                    set_abbr = 'pw21'
                elif name == 'Archfiend of Ifnir':
                    set_abbr = 'pakh'
                elif name == "Archmage's Charm":
                    set_abbr = 'sch'
                # there isn't a good way to get the correct collector number
                # for 30th Anniversary promos
                elif name == 'Ball Lightning' and variation == '2':
                    set_abbr = 'p30a'
                    variation = '2'
                elif name == 'Ember Swallower':
                    set_abbr = 'pths'
                elif name == 'Fyndhorn Elves':
                    set_abbr = 'p30a'
                    variation = '3'
                elif name == 'Mind Stone':
                    set_abbr = 'pw21'
                elif name == 'Goblin Guide':
                    set_abbr = 'plg21'
                elif name == 'Selfless Spirit':
                    set_abbr = 'prcq'
                elif name == 'Serra Angel' and variation == '5':
                    set_abbr = 'p30a'
                    variation = '1'
                elif name == 'Swiftfoot Boots':
                    set_abbr = 'pw22'
                elif name == 'Thraben Inspector':
                    set_abbr = 'prcq'
                elif name == 'Wall of Roots' and variation == '2':
                    set_abbr = 'p30a'
                    variation = '4'
                else:
                    raise Exception(f"Unhandled 000 set. {name}")
            # tappedout and scryfall use different codes
            if set_abbr == 'mys1':
                set_abbr = 'mb1'
            elif set_abbr == 'eo2':
                set_abbr = 'e02'
            elif set_abbr == 'pfl':
                set_abbr = 'pd2'
            # these appear to be just wrong in tappedout?
            elif set_abbr == 'tsb':
                if name in ['Swamp', 'Aarakocra Sneak']:
                    set_abbr = 'clb'

            collector_number = None
            promo_pack = False
            prerelease = False
            if variation != '-':
                if variation == 'PromoPack':
                    collector_number = get_default_collectors_number(name, set_abbr)
                    promo_pack = True
                else:
                    collector_number = variation
            else:
                collector_number = get_default_collectors_number(name, set_abbr)

            # The collector number is wrong for these cards
            if name == 'Armored Cancrix' and set_abbr == 'm14':
                collector_number = '44'
            elif name == 'Cancel' and set_abbr == 'm14':
                collector_number = '45'
            elif name == 'Keepsake Gorgon' and set_abbr == 'ths':
                collector_number = '93'
            elif name == 'Map the Wastes' and set_abbr == 'frf':
                collector_number = '134'
            elif name == 'Nyxborn Eidolon' and set_abbr == 'bng':
                collector_number = '78'
            elif name == 'Prying Questions' and set_abbr == 'emn':
                collector_number = '101'
            elif name == 'Resolute Veggiesaur' and set_abbr == 'unf':
                collector_number = '153'
            # We need the extra test because there are multiple versions of this wastes
            elif name == 'Wastes' and set_abbr == 'ogw' and collector_number == '134':
                collector_number = '184'


            # This isn't exactly a finish because it also says if it's a list card
            finish = row['Foil']

            # Tappedout spells language wrong in the csv
            language = row['Languange'].lower()
            foil = False
            the_list = False
            if finish != '-':
                if finish == 'f':
                    foil = True
                elif finish == 'list':
                    the_list = True
                elif finish == 'pp':
                    promo_pack = True
                elif finish == 'f-pp':
                    foil = True
                    promo_pack = True
                elif finish == 'f-pre':
                    foil = True
                    prerelease = True
                else:
                    language = finish.lower()

            if the_list:
                set_abbr = 'plist'

            if (promo_pack or prerelease) and set_abbr != 'pths':
                set_abbr = 'p' + set_abbr
                if promo_pack:
                    collector_number += 'p'

                if prerelease:
                    collector_number += 's'

            if language == 'zh':
                print(f"WARNING: Tappedout doesn't have Chinese Traditional as a language option. Verify this card is actually Chinese Simplified. {name} ({set_abbr}:{collector_number})")
                language = 'zhs'

            res = cur.execute('SELECT fc.ID, fc.FinishID FROM FinishCards fc WHERE CardID IN (SELECT c.ID FROM Cards c INNER JOIN Sets s ON c.SetID = s.ID INNER JOIN Langs l ON c.LangID = l.ID WHERE s.Code = %s AND c.CollectorNumber = %s AND l.Lang = %s)', (set_abbr, collector_number, language))
            id_finishes = res.fetchall()
            finish_ids = [id_finish[1] for id_finish in id_finishes]

            # Tappedout allows entry of languages that aren't actually available
            # So if we didn't get any results then we see if that's the issue
            if len(id_finishes) == 0:
                # Check if it was the language that was the problem
                res = cur.execute('SELECT Langs.Lang FROM Cards INNER JOIN Langs ON Cards.LangID = Langs.ID INNER JOIN Sets ON Cards.SetID = Sets.ID WHERE sets.Code = %s AND cards.CollectorNumber = %s', (set_abbr, collector_number))
                languages = res.fetchall()

                if len(languages) > 0 and language not in languages:
                    # If the card doesn't come in this language and there's only one option that's probably what they wanted
                    if len(languages) == 1:
                        print(f"WARNING: {name} ({set_abbr}:{collector_number}) doesn't come in language '{language}', it only comes in {languages[0][0]}. So we're using that.")
                        language = languages[0][0]
                    else:
                        # This is to cover weird edge cases that I haven't seen yet.
                        print(f"Card doesn't come in this language and there are multiple to choose from. Fix it in tappedout and try again. Card: {name} ({set_abbr}:{collector_number}) {language}, Available languages: {languages}")
                        exit(1)

                res = cur.execute('SELECT fc.ID, fc.FinishID FROM FinishCards fc WHERE CardID IN (SELECT c.ID FROM Cards c INNER JOIN Sets s ON c.SetID = s.ID INNER JOIN Langs l ON c.LangID = l.ID WHERE s.Code = %s AND c.CollectorNumber = %s AND l.Lang = %s)', (set_abbr, collector_number, language))
                id_finishes = res.fetchall()
                finish_ids = [id_finish[1] for id_finish in id_finishes]

            # Sometimes the collector number doesn't match up what scryfall has
            # this usually happens when scryfall distingushes between versions of card
            # that tappedout doesn't
            # Ex. Bruna, the Fading Light
            if len(id_finishes) == 0:
                collector_number = get_default_collectors_number(name, set_abbr)
                res = cur.execute('SELECT fc.ID, fc.FinishID FROM FinishCards fc WHERE CardID IN (SELECT c.ID FROM Cards c INNER JOIN Sets s ON c.SetID = s.ID INNER JOIN Langs l ON c.LangID = l.ID WHERE s.Code = %s AND c.CollectorNumber = %s AND l.Lang = %s)', (set_abbr, collector_number, language))
                id_finishes = res.fetchall()
                finish_ids = [id_finish[1] for id_finish in id_finishes]

            # If etched is the only option then we don't need to warn
            if len(id_finishes) > 1:
                if finish_id_map['etched'] in finish_ids:
                    print(f"INFO: Tappedout doesn't have etched as an option in their database and {name} ({set_abbr}:{collector_number}) is available in etched. Ensure the data is correct.")

                if not foil and finish_id_map['nonfoil'] in finish_ids:
                    finish = finish_id_map['nonfoil']
                elif foil and finish_id_map['foil'] in finish_ids:
                    finish = finish_id_map['foil']
                else:
                    print(f"Finish appears to be wrong on card {name} ({set_abbr}:{collector_number}). Valid options are {finishes}")
                    exit(1)

                finishCardID = [f for f in id_finishes if f[1] == finish]
                if len(finishCardID) != 1:
                    print(f"Didn't find exactly one card + finish for card {name} ({set_abbr}:{collector_number}). Options were {finishCardID}")
                    exit(1)

                finishCardID = finishCardID[0][0]
            elif len(id_finishes) == 1:
                # TODO: Warn if the only finish in scryfall doesn't match the one they have in tappedout
                finishCardID = id_finishes[0][0]
            else:
                print(row)
                raise ValueError("Didn't find a matching card + finish + lang combo")

            condition = row['Condition']
            altered = row['Alter'] != '-'
            signed = row['Signed'] != '-'

            condition = scryfall_to_db_condition[condition]

            rows_to_insert.append((user_id, finishCardID, condition, quantity, signed, altered, ''))

    with cur.copy("COPY Collections (UserID, FinishCardID, Condition, Quantity, Signed, Altered, Notes) FROM STDIN") as copy:
        for row in rows_to_insert:
            copy.write_row(row)

    con.commit()

import timeit

now = timeit.default_timer()
import_data('me')

print(f"Took {timeit.default_timer() - now} seconds")
