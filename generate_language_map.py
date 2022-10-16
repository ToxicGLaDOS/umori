#!/usr/bin/env python

# Generates a dict of this schema and outputs it to language_map.json
# {
#   <scryfall_id> : {
#     [
#       {
#         "scryfall_id": <scryfall_id>,
#         "lang": <lang_code>,
#         # The first entry is always the default language
#         # but we provide the default key in case it's more convenient
#         "default": true
#       },
#       {
#         "scryfall_id": <scryfall_id_of_card_with_same_set_and_collector_number>,
#         "lang": <lang_code>,
#         "default": false
#       },
#       ...
#     ]
#   },
#   ...
# }

from datetime import datetime, timedelta
import sys, json, time, re

if len(sys.argv) != 3:
    print("Expected exactly two arguements <path scryfall ALL bulk data>, <path scryfall DEFAULT bulk data>")
    exit(1)

all_cards_path = sys.argv[1]
default_cards_path = sys.argv[2]

# Santity check that both databases are from the same time
all_cards_matches = re.match(r'all-cards-(\d{14})\.json', all_cards_path)
default_cards_matches = re.match(r'default-cards-(\d{14})\.json', default_cards_path)

# We allow the bulk data files to be renamed, but spit out a warning
if all_cards_matches and default_cards_matches:
    datetime_format = "%Y%m%d%H%M%S"
    all_cards_time = datetime.strptime(all_cards_matches.group(1), datetime_format)
    default_cards_time = datetime.strptime(default_cards_matches.group(1), datetime_format)

    greater = max(all_cards_time, default_cards_time)
    lesser  = min(all_cards_time, default_cards_time)

    # If the files are from more than 6 hours apart abort
    # 6 hours is arbitrary, they seem to upload daily and within ~10 mins
    # of each other, so 6 hours should be plenty of time
    if (greater - lesser) > timedelta(hours=6):
        print("Bulk data isn't from same time. This can cause issues with cards being found in one, but not the other. Refusing to continue.")
        exit(5)
else:
    print("WARNING: It looks like you renamed the bulk data files. Can't verify they're from the same time. Bulk data downloaded at different times can cause issues. Will continue though.")


# Final output dict
output = {}

# Temp data holder for first pass over ALL data
temp_dict = {}

# Set of ids in default_data used to speed up checking for default lang over default_data itself
# (checking set membership is fast)
default_set = set()

with open(all_cards_path) as f:
    now = time.time()
    # This takes a while
    all_data = json.load(f)

print(f"Finished loading ALL database in {time.time() - now:.2f} seconds")

with open(default_cards_path) as f:
    now = time.time()
    # This takes a while
    default_data = json.load(f)


print(f"Finished loading DEFAULT database in {time.time() - now:.2f} seconds")
now = time.time()

if len(all_data) < len(default_data):
    print("ALL database has fewer cards than DEFAULT database, arguments are probably in wrong order.")
    exit(3)



# Convert default_data into a map of id -> lang
# because checking for a key is faster than iterating
# through a list to see if an id is in default_data
for card in default_data:
    scryfall_id = card['id']

    if scryfall_id in default_set:
        print("Found duplicate id somehow")
        exit(3)

    # We don't actually use the value at all so
    # we could put anything there.
    default_set.add(scryfall_id)

print(f"Finished creating default_set in {time.time() - now:.2f} seconds")
now = time.time()


num_cards = len(all_data)
for index, card in enumerate(all_data):
    card_set = card['set']
    card_collector_number = card['collector_number']

    key = f'{card_set}:{card_collector_number}'

    if not temp_dict.get(key):
        temp_dict[key] = []

    default = card['id'] in default_set

    obj = {'scryfall_id': card['id'], 'lang': card['lang'], 'default': default}
    temp_dict[key].append(obj)

    langs = [obj['lang'] for obj in temp_dict[key]]

    # Sanity check to make sure we don't end up with duplicate langs somehow
    if sorted(langs) != sorted(list(set(langs))):
        print(temp_dict[key]['langs'])
        print(list(set(temp_dict[key]['langs'])))
        exit(2)


    if index % 10000 == 0:
        print(f"Finished {index}/{num_cards} ({index/num_cards*100:.2f}%)")


print(f"Finished finding languages in {time.time() - now:.2f} seconds")
now = time.time()

# Generate output
for set_collector_number, ids_langs in temp_dict.items():
    defaults = map(lambda id_lang: id_lang['default'], ids_langs)
    default_trues = list(filter(lambda default: default, defaults))
    if len(default_trues) != 1:
        print(f"Card {set_collector_number} had non-one number of default languages ({len(default_trues)})")
        print(f"ids_langs: {ids_langs}")
        exit(4)

    for id_lang in ids_langs:
        scryfall_id = id_lang['scryfall_id']

        output[scryfall_id] = sorted(ids_langs, key=lambda id_lang: 0 if id_lang['default'] else 1)


print(f"Finished reformatting data in {time.time() - now:.2f} seconds")
now = time.time()

# Write output
with open('language_map.json', 'w') as f:
    json.dump(output, f)

print(f"Finished writing data in {time.time() - now:.2f} seconds")


