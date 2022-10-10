#!/usr/bin/env python

import sys, json, time

if len(sys.argv) > 2:
    print("Expected exactly one argument. The path to the scryfall database")
    sys.exit(1)

elif len(sys.argv) < 2:
    print("Expected exactly one argument. The path to the scryfall database")
    sys.exit(2)

scryfall_db_path = sys.argv[1]
original_data = []
shrunk_data = []


start = time.time()
with open(scryfall_db_path) as db:
    # This is gonna take a long time and a lot of memory
    # ~25 Seconds and ~5Gb
    original_data = json.load(db)

read_done = time.time()
print(f'read done in: {read_done - start:.1f}')

for card in original_data:
    shrunk_card = {}
    # A couple secret lair drops have the same card with
    # different art on the front and back, (ex. Propaganda)
    # these don't have an oracle_id on the outermost part
    # of the dict, instead it's on each card face.
    # So far, these are the only cards that work like this
    # and both sides have the same oracle_id as the normal card
    if not card.get('oracle_id'):
        shrunk_card['oracle_id'] = card['card_faces'][0]['oracle_id']
    else:
        shrunk_card['oracle_id'] = card['oracle_id']

    if card.get('card_faces'):
        shrunk_card['card_faces'] = []
        for face in card['card_faces']:
            shrunk_face = {}
            shrunk_face['name'] = face['name']

            shrunk_card['card_faces'].append(shrunk_face)

    shrunk_card['name'] = card['name']
    shrunk_card['collector_number'] = card['collector_number']
    shrunk_card['set'] = card['set']
    shrunk_card['id'] = card['id']

    shrunk_data.append(shrunk_card)

iterate_done = time.time()
print(f'iterate done in: {iterate_done - read_done:.1f}')

with open('shrunk.json', 'w') as out:
    json.dump(shrunk_data, out)

write_done = time.time()

print(f'''write: {write_done - iterate_done:.1f}
total: {write_done - start:.1f}''')
