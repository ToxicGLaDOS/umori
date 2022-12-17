#!/usr/bin/env python

# NOTES ON PERFORMANCE:
# Using UNLOGGED tables and then using ALTER TABLE ... SET LOGGED seems the same as just using LOGGED tables to begin with
# Sqlite3 is waaaay faster, for inserts but waaaay slower on the DELETES. It took about ~15 minutes or so to DELETE all the data in Sqlite3

import psycopg, ijson, sys, os, timeit, requests

if len(sys.argv) != 3:
    print("Expected exactly two arguments, the path to the ALL data and the path to the DEFAULT data")

all_data_file = open(sys.argv[1])
default_data_file = open(sys.argv[2])

all_data = ijson.items(all_data_file, 'item', use_float=True)

default_data = ijson.items(default_data_file, 'item', use_float=True)

#if len(all_data) < len(default_data):
#    print("ALL database has fewer cards than DEFAULT database, arguments are probably in wrong order.")
#    exit(1)

default_set = set()

# Populate default_set with all the scryfall_ids
# of the default cards
for card in default_data:
    scryfall_id = card['id']

    if scryfall_id in default_set:
        print("Found duplicate id somehow")
        exit(2)

    default_set.add(scryfall_id)

#if os.path.exists('all.db'):
#    os.remove('all.db')

con = psycopg.connect(user = "postgres", password = "password", host = "127.0.0.1", port = "5432")

#con = psycopg.connect('all.db')
cur = con.cursor()

#cur.execute('PRAGMA foreign_keys = ON')
now = timeit.default_timer()
start_time = now


cur.execute('''CREATE TABLE IF NOT EXISTS Langs
            (
            ID   INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            Lang VARCHAR             NOT NULL UNIQUE
            )
            ''')


cur.execute('''CREATE TABLE IF NOT EXISTS Layouts
            (
            ID     INTEGER     PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            Layout VARCHAR                 NOT NULL UNIQUE
            )
            ''')


cur.execute('''CREATE TABLE IF NOT EXISTS ImageStatuses
            (
            ID          INTEGER     PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            ImageStatus VARCHAR                 NOT NULL UNIQUE
            )
            ''')


cur.execute('''CREATE TABLE IF NOT EXISTS Legalities
            (
            ID       INTEGER     PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            Legality VARCHAR                 NOT NULL UNIQUE
            )
            ''')


cur.execute('''CREATE TABLE IF NOT EXISTS SetTypes
            (
            ID   INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            Type VARCHAR             NOT NULL UNIQUE
            )
            ''')


cur.execute('''CREATE TABLE IF NOT EXISTS Sets
            (
            ID            UUID    PRIMARY KEY             NOT NULL,
            Name          VARCHAR                         NOT NULL UNIQUE,
            TypeID        INTEGER REFERENCES SetTypes(id) DEFERRABLE INITIALLY DEFERRED NOT NULL,
            Code          VARCHAR                         NOT NULL UNIQUE,
            MtgoCode      VARCHAR                                        ,
            TcgplayerID   VARCHAR                                        ,
            ReleasedAt    DATE                                           ,
            BlockCode     VARCHAR                                        ,
            Block         VARCHAR                                        ,
            ParentSetCode VARCHAR                                        ,
            CardCount     VARCHAR                         NOT NULL       ,
            PrintedSize   VARCHAR                                        ,
            Digital       VARCHAR                         NOT NULL       ,
            FoilOnly      VARCHAR                         NOT NULL       ,
            NonfoilOnly   VARCHAR                         NOT NULL       ,
            IconSVGURI    VARCHAR                         NOT NULL
            )
            ''')


cur.execute('''CREATE TABLE IF NOT EXISTS Rarities
            (
            ID     INTEGER     PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            Rarity VARCHAR                 NOT NULL UNIQUE
            )
            ''')


cur.execute('''CREATE TABLE IF NOT EXISTS BorderColors
            (
            ID          INTEGER     PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            BorderColor VARCHAR             NOT NULL UNIQUE
            )
            ''')


cur.execute('''CREATE TABLE IF NOT EXISTS Frames
            (
            ID    INTEGER     PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            Frame VARCHAR                 NOT NULL UNIQUE
            )
            ''')


cur.execute('''CREATE TABLE IF NOT EXISTS Colors
            (
            ID    INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            Color CHAR(1) NOT NULL UNIQUE
            )
            ''')


# foil and nonfoil are deprecated so we don't care about them
#
# we don't collect the artist_ids because I don't have a good way
# to check what artist_id is for what artist
#
# oracle_id, type_line, cmc (maybe others) are supposed to not be nullable
# but sometimes they are :shrug:
#
# DefaultLang is the only column that's calculated
cur.execute('''CREATE TABLE IF NOT EXISTS Cards
               (
               ID                      UUID        PRIMARY KEY                               NOT NULL,
               OracleID                UUID                                                          ,
               MtgoID                  INTEGER                                                       ,
               MtgoFoilID              INTEGER                                                       ,
               TcgplayerID             INTEGER                                                       ,
               CardmarketID            INTEGER                                                       ,
               Name                    VARCHAR                                               NOT NULL,
               LangID                  INTEGER                 REFERENCES Langs(id) DEFERRABLE INITIALLY DEFERRED          NOT NULL,
               DefaultLang             BOOLEAN                                               NOT NULL,
               ReleasedAt              DATE                                                  NOT NULL,
               LayoutID                INTEGER                 REFERENCES Layouts(id) DEFERRABLE INITIALLY DEFERRED        NOT NULL,
               HighresImage            BOOLEAN                                               NOT NULL,
               ImageStatusID           INTEGER                 REFERENCES ImageStatuses(id) DEFERRABLE INITIALLY DEFERRED  NOT NULL,
               NormalImageURI          VARCHAR                                                       ,
               ManaCost                VARCHAR                                                       ,
               Cmc                     REAL                                                          ,
               TypeLine                VARCHAR                                                       ,
               OracleText              VARCHAR                                                       ,
               Power                   VARCHAR                                                       ,
               Toughness               VARCHAR                                                       ,
               LegalStandardID         INTEGER                 REFERENCES Legalities(id) DEFERRABLE INITIALLY DEFERRED     NOT NULL,
               LegalFutureID           INTEGER                 REFERENCES Legalities(id) DEFERRABLE INITIALLY DEFERRED     NOT NULL,
               LegalHistoricID         INTEGER                 REFERENCES Legalities(id) DEFERRABLE INITIALLY DEFERRED     NOT NULL,
               LegalGladiatorID        INTEGER                 REFERENCES Legalities(id) DEFERRABLE INITIALLY DEFERRED     NOT NULL,
               LegalPioneerID          INTEGER                 REFERENCES Legalities(id) DEFERRABLE INITIALLY DEFERRED     NOT NULL,
               LegalExplorerID         INTEGER                 REFERENCES Legalities(id) DEFERRABLE INITIALLY DEFERRED     NOT NULL,
               LegalModernID           INTEGER                 REFERENCES Legalities(id) DEFERRABLE INITIALLY DEFERRED     NOT NULL,
               LegalLegacyID           INTEGER                 REFERENCES Legalities(id) DEFERRABLE INITIALLY DEFERRED     NOT NULL,
               LegalPauperID           INTEGER                 REFERENCES Legalities(id) DEFERRABLE INITIALLY DEFERRED     NOT NULL,
               LegalVintageID          INTEGER                 REFERENCES Legalities(id) DEFERRABLE INITIALLY DEFERRED     NOT NULL,
               LegalPennyID            INTEGER                 REFERENCES Legalities(id) DEFERRABLE INITIALLY DEFERRED     NOT NULL,
               LegalCommanderID        INTEGER                 REFERENCES Legalities(id) DEFERRABLE INITIALLY DEFERRED     NOT NULL,
               LegalBrawlID            INTEGER                 REFERENCES Legalities(id) DEFERRABLE INITIALLY DEFERRED     NOT NULL,
               LegalHistoricBrawlID    INTEGER                 REFERENCES Legalities(id) DEFERRABLE INITIALLY DEFERRED     NOT NULL,
               LegalAlchemyID          INTEGER                 REFERENCES Legalities(id) DEFERRABLE INITIALLY DEFERRED     NOT NULL,
               LegalPauperCommanderID  INTEGER                 REFERENCES Legalities(id) DEFERRABLE INITIALLY DEFERRED     NOT NULL,
               LegalDuelID             INTEGER                 REFERENCES Legalities(id) DEFERRABLE INITIALLY DEFERRED     NOT NULL,
               LegalOldschoolID        INTEGER                 REFERENCES Legalities(id) DEFERRABLE INITIALLY DEFERRED     NOT NULL,
               LegalPremodernID        INTEGER                 REFERENCES Legalities(id) DEFERRABLE INITIALLY DEFERRED     NOT NULL,
               Reserved                BOOLEAN                                               NOT NULL,
               Oversized               BOOLEAN                                               NOT NULL,
               Promo                   BOOLEAN                                               NOT NULL,
               Reprint                 BOOLEAN                                               NOT NULL,
               Variation               BOOLEAN                                               NOT NULL,
               SetID                   UUID                    REFERENCES Sets(id) DEFERRABLE INITIALLY DEFERRED           NOT NULL,
               CollectorNumber         VARCHAR                                               NOT NULL,
               Digital                 BOOLEAN                                               NOT NULL,
               RarityID                INTEGER                 REFERENCES Rarities(id) DEFERRABLE INITIALLY DEFERRED       NOT NULL,
               FlavorText              VARCHAR                                                       ,
               Artist                  VARCHAR                                                       ,
               IllustrationID          UUID                                                          ,
               BorderColorID           INTEGER                 REFERENCES BorderColors(id) DEFERRABLE INITIALLY DEFERRED   NOT NULL,
               FrameID                 INTEGER                 REFERENCES Frames(id) DEFERRABLE INITIALLY DEFERRED         NOT NULL,
               FullArt                 BOOLEAN                                               NOT NULL,
               Textless                BOOLEAN                                               NOT NULL,
               Booster                 BOOLEAN                                               NOT NULL,
               StorySpotlight          BOOLEAN                                               NOT NULL
               )
             ''')



# Why UNIQUE(CardID, Name, NormalImageURI)
# CardID + Name isn't sufficent because of SLD Stitch in Time (and others)
# CardID + NormalImageURI isn't sufficent because NormalImageURI is NULL
# when both "faces" are on the same side of the card (ex. aftermath cards)
# TODO: Needs colors junction
cur.execute('''CREATE TABLE IF NOT EXISTS Faces
            (
            ID             INTEGER PRIMARY KEY          GENERATED ALWAYS AS IDENTITY,
            CardID         UUID    REFERENCES Cards(id) DEFERRABLE INITIALLY DEFERRED      NOT NULL,
            Name           VARCHAR                           NOT NULL,
            ManaCost       VARCHAR                           NOT NULL,
            TypeLine       VARCHAR                                   ,
            OracleText     VARCHAR                           NOT NULL,
            FlavorText     VARCHAR                                   ,
            Artist         VARCHAR                                   ,
            ArtistID       UUID                                      ,
            IllustrationID UUID                                      ,
            NormalImageURI VARCHAR
            )
            ''')


# We _could_ make a table for the MultiverseIDs and
# have this be forign keys to each table, but that seems
# unnecessary
cur.execute('''CREATE TABLE IF NOT EXISTS MultiverseIDCards
            (
            ID           INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            CardID       UUID    REFERENCES Cards(id) DEFERRABLE INITIALLY DEFERRED NOT NULL,
            MultiverseID INTEGER                      NOT NULL
            )
            ''')


cur.execute('''CREATE TABLE IF NOT EXISTS ColorCards
            (
            ID      INTEGER  PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            CardID  UUID     REFERENCES Cards(id) DEFERRABLE INITIALLY DEFERRED NOT NULL,
            ColorID INTEGER  REFERENCES Colors(id) DEFERRABLE INITIALLY DEFERRED NOT NULL,
            UNIQUE(CardID, ColorID)
            )
            ''')


cur.execute('''CREATE TABLE IF NOT EXISTS ColorIdentityCards
            (
            ID      INTEGER  PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            CardID  UUID     REFERENCES Cards(id) DEFERRABLE INITIALLY DEFERRED NOT NULL,
            ColorID INTEGER  REFERENCES Colors(id) DEFERRABLE INITIALLY DEFERRED NOT NULL,
            UNIQUE(CardID, ColorID)
            )
            ''')


cur.execute('''CREATE TABLE IF NOT EXISTS Keywords
            (
            ID      INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            Keyword VARCHAR NOT NULL UNIQUE
            )
            ''')


cur.execute('''CREATE TABLE IF NOT EXISTS KeywordCards
            (
            ID        INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            CardID    UUID    REFERENCES Cards(id) DEFERRABLE INITIALLY DEFERRED NOT NULL,
            KeywordID INTEGER REFERENCES Keywords(id) DEFERRABLE INITIALLY DEFERRED NOT NULL,
            UNIQUE(CardID, KeywordID)
            )
            ''')


cur.execute('''CREATE TABLE IF NOT EXISTS Games
            (
            ID   INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            Game VARCHAR NOT NULL UNIQUE
            )
            ''')


cur.execute('''CREATE TABLE IF NOT EXISTS GameCards
            (
            ID     INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            CardID UUID    REFERENCES Cards(id) DEFERRABLE INITIALLY DEFERRED NOT NULL,
            GameID INTEGER REFERENCES Games(id) DEFERRABLE INITIALLY DEFERRED NOT NULL,
            UNIQUE(CardID, GameID)
            )
            ''')


cur.execute('''CREATE TABLE IF NOT EXISTS Finishes
            (
            ID     INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            Finish VARCHAR NOT NULL UNIQUE
            )
            ''')


cur.execute('''CREATE TABLE IF NOT EXISTS FinishCards
            (
            ID       INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            CardID   UUID    REFERENCES Cards(id) DEFERRABLE INITIALLY DEFERRED NOT NULL,
            FinishID INTEGER REFERENCES Finishes(id) DEFERRABLE INITIALLY DEFERRED NOT NULL,
            UNIQUE(CardID, FinishID)
            )
            ''')


print(f"Create tables took {timeit.default_timer() - now:.2f} seconds")
now = timeit.default_timer()

cur.execute('DELETE FROM Sets')
cur.execute('DELETE FROM Cards')
cur.execute('DELETE FROM Faces')

print(f"DELETE tables took {timeit.default_timer() - now:.2f} seconds")
now = timeit.default_timer()

insert_statement = '''INSERT INTO Cards(ID, OracleID, MtgoID, MtgoFoilID, TcgplayerID, CardmarketID, Name, LangID, DefaultLang, ReleasedAt, LayoutID, HighresImage, ImageStatusID, NormalImageURI, ManaCost, Cmc, TypeLine, OracleText, Power, Toughness, LegalStandardID, LegalFutureID, LegalHistoricID, LegalGladiatorID, LegalPioneerID, LegalExplorerID, LegalModernID, LegalLegacyID, LegalPauperID, LegalVintageID, LegalPennyID, LegalCommanderID, LegalBrawlID, LegalHistoricBrawlID, LegalAlchemyID, LegalPauperCommanderID, LegalDuelID, LegalOldschoolID, LegalPremodernID, Reserved, Oversized, Promo, Reprint, Variation, SetID, CollectorNumber, Digital, RarityID, FlavorText, Artist, IllustrationID, BorderColorID, FrameID, FullArt, Textless, Booster, StorySpotlight)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    RETURNING ID'''

# First pass to gather all data to put in the small tables
langs = set()
layouts = set()
image_statuses = set()
rarities = set()
border_colors = set()
frames = set()
set_types = set()
legalities = set()
faces = set()
colors = set()
keywords = set()
games = set()
finishes = set()


resp = requests.get("https://api.scryfall.com/sets")
all_sets_data = resp.json()['data']

for set_data in all_sets_data:
    set_types.add(set_data['set_type'])

# This allows index to be used after the loop which effectively counts how many card there are
index = 0
for index, card in enumerate(all_data):
    langs.add(card['lang'])
    layouts.add(card['layout'])
    image_statuses.add(card['image_status'])
    rarities.add(card['rarity'])
    border_colors.add(card['border_color'])
    frames.add(card['frame'])

    if card.get('card_faces'):
        for face in card.get('card_faces'):
            image_uri = face['image_uris']['normal'] if face.get('image_uris') else None
            f = (card['id'], face['name'], face['mana_cost'], face.get('type_line'), face['oracle_text'], face.get('flavor_text'), face.get('artist'), face.get('artist_id'), face.get('illustration_id'), image_uri)
            faces.add(f)

    for format_ in ['standard',
                     'future',
                     'historic',
                     'gladiator',
                     'pioneer',
                     'explorer',
                     'modern',
                     'legacy',
                     'pauper',
                     'vintage',
                     'penny',
                     'commander',
                     'brawl',
                     'historicbrawl',
                     'alchemy',
                     'paupercommander',
                     'duel',
                     'oldschool',
                     'premodern']:
        legalities.add(card['legalities'][format_])

    for color in card.get('colors', []):
        colors.add(color)
    for keyword in card['keywords']:
        keywords.add(keyword)
    for game in card['games']:
        games.add(game)
    for finish in card['finishes']:
        finishes.add(finish)

print(f"Discovering data took {timeit.default_timer() - now:.2f} seconds")
now = timeit.default_timer()

# Maps value to ID in database so we don't have to SELECT later
langs_id_map = {}
layouts_id_map = {}
image_statuses_id_map = {}
rarities_id_map = {}
border_colors_id_map = {}
frames_id_map = {}
legalities_id_map = {}
faces_id_map = {}
colors_id_map = {}
keywords_id_map = {}
games_id_map = {}
finishes_id_map = {}
sets_id_map = {}
set_types_id_map = {}

def insert_or_select(table_name: str, column_names: tuple[str], values):

    columns = ""
    for index, name in enumerate(column_names):
        columns += name
        if index != len(column_names) - 1:
            columns += ', '

    res = cur.execute(f'INSERT INTO {table_name} ({columns}) VALUES(%s) ON CONFLICT DO NOTHING RETURNING ID', values)
    id_ = res.fetchone()

    if id_ != None:
        id_ = id_[0]
    else:
        res = cur.execute(f'SELECT ID FROM {table_name} WHERE {columns} = %s', values)
        id_ = res.fetchone()[0]

    return id_

resp = requests.get("https://api.scryfall.com/sets")
all_sets_data = resp.json()['data']

for set_type in set_types:
    set_type_id = insert_or_select('SetTypes', ('Type',), (set_type,))
    set_types_id_map[set_type] = set_type_id

for set_data in all_sets_data:
    # These can be null
    mtgo_code = set_data.get('mtgo_code')
    tcgplayer_id = set_data.get('tgcplayer_id')
    block_code = set_data.get('block_code')
    block = set_data.get('block')
    parent_set_code = set_data.get('parent_set_code')
    printed_size = set_data.get('printed_size')

    res = cur.execute('''INSERT INTO Sets (ID, Name, TypeID, Code, MtgoCode, TcgplayerID, ReleasedAt, BlockCode, Block, ParentSetCode, CardCount, PrintedSize, Digital, FoilOnly, NonfoilOnly, IconSVGURI)
                      VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                      RETURNING ID''',
                      (set_data['id'], set_data['name'], set_types_id_map[set_data['set_type']], set_data['code'], mtgo_code, tcgplayer_id, set_data['released_at'], block_code, block, parent_set_code, set_data['card_count'], printed_size, set_data['digital'], set_data['foil_only'], set_data['nonfoil_only'], set_data['icon_svg_uri']))

    sets_id_map[set_data['name']] = set_data['id']


for lang in langs:
    id_ = insert_or_select('Langs', ('Lang',), (lang,))
    langs_id_map[lang] = id_
for layout in layouts:
    id_ = insert_or_select('Layouts', ('Layout',), (layout,))
    layouts_id_map[layout] = id_
for image_status in image_statuses:
    id_ = insert_or_select('ImageStatuses', ('ImageStatus',), (image_status,))
    image_statuses_id_map[image_status] = id_
for rarity in rarities:
    id_ = insert_or_select('Rarities', ('Rarity',), (rarity,))
    rarities_id_map[rarity] = id_
for border_color in border_colors:
    id_ = insert_or_select('BorderColors', ('BorderColor',), (border_color,))
    border_colors_id_map[border_color] = id_
for frame in frames:
    id_ = insert_or_select('Frames', ('Frame',), (frame,))
    frames_id_map[frame] = id_
for legality in legalities:
    id_ = insert_or_select('Legalities', ('Legality',), (legality,))
    legalities_id_map[legality] = id_
for color in colors:
    id_ = insert_or_select('Colors', ('Color',), (color,))
    colors_id_map[color] = id_
for keyword in keywords:
    id_ = insert_or_select('Keywords', ('Keyword',), (keyword,))
    keywords_id_map[keyword ] = id_
for game in games:
    id_ = insert_or_select('Games', ('Game',), (game,))
    games_id_map[game] = id_
for finish in finishes:
    id_ = insert_or_select('Finishes', ('Finish',), (finish,))
    finishes_id_map[finish] = id_


color_cards = set()
color_identity_cards = set()
keyword_cards = set()
game_cards = set()
finish_cards = set()

print(f"INSERT (non-cards, non-faces) took {timeit.default_timer() - now:.2f} seconds")
now = timeit.default_timer()

all_data_file.seek(0)
all_data = ijson.items(all_data_file, 'item', use_float=True)
num_cards = index + 1
with cur.copy("COPY Cards (ID, OracleID, MtgoID, MtgoFoilID, TcgplayerID, CardmarketID, Name, LangID, DefaultLang, ReleasedAt, LayoutID, HighresImage, ImageStatusID, NormalImageURI, ManaCost, Cmc, TypeLine, OracleText, Power, Toughness, LegalStandardID, LegalFutureID, LegalHistoricID, LegalGladiatorID, LegalPioneerID, LegalExplorerID, LegalModernID, LegalLegacyID, LegalPauperID, LegalVintageID, LegalPennyID, LegalCommanderID, LegalBrawlID, LegalHistoricBrawlID, LegalAlchemyID, LegalPauperCommanderID, LegalDuelID, LegalOldschoolID, LegalPremodernID, Reserved, Oversized, Promo, Reprint, Variation, SetID, CollectorNumber, Digital, RarityID, FlavorText, Artist, IllustrationID, BorderColorID, FrameID, FullArt, Textless, Booster, StorySpotlight) FROM STDIN") as copy:
    for index, card in enumerate(all_data):
        if index % 1000 == 0:
            print(f"{index}/{num_cards} {index/num_cards:.2f}")
            pass
        lang_id = langs_id_map[card['lang']]

        layout_id = layouts_id_map[card['layout']]

        image_status_id = image_statuses_id_map[card['image_status']]

        rarity_id = rarities_id_map[card['rarity']]

        border_color_id = border_colors_id_map[card['border_color']]

        frame_id = frames_id_map[card['frame']]

        formats = ['standard',
                   'future',
                   'historic',
                   'gladiator',
                   'pioneer',
                   'explorer',
                   'modern',
                   'legacy',
                   'pauper',
                   'vintage',
                   'penny',
                   'commander',
                   'brawl',
                   'historicbrawl',
                   'alchemy',
                   'paupercommander',
                   'duel',
                   'oldschool',
                   'premodern']

        legalities = {}
        # format is a built-in
        for format_ in formats:
            legality_id = legalities_id_map[card['legalities'][format_]]

            legalities[format_] = legality_id

        set_type_id = set_types_id_map[card['set_type']]

        set_id = sets_id_map[card['set_name']]

        default = card['id'] in default_set

        values = (
                card['id'],
                card.get('oracle_id'),
                card.get('mtgo_id'),
                card.get('mtgo_foil_id'),
                card.get('tcgplayer_id'),
                card.get('cardmarket_id'),
                card['name'],
                lang_id,
                default,
                card['released_at'],
                layout_id,
                card['highres_image'],
                image_status_id,
                card['image_uris']['normal'] if card.get('image_uris') else None,
                card.get('mana_cost'),
                card.get('cmc'),
                card.get('type_line'),
                card.get('oracle_text'),
                card.get('power'),
                card.get('toughness'),
                legalities['standard'],
                legalities['future'],
                legalities['historic'],
                legalities['gladiator'],
                legalities['pioneer'],
                legalities['explorer'],
                legalities['modern'],
                legalities['legacy'],
                legalities['pauper'],
                legalities['vintage'],
                legalities['penny'],
                legalities['commander'],
                legalities['brawl'],
                legalities['historicbrawl'],
                legalities['alchemy'],
                legalities['paupercommander'],
                legalities['duel'],
                legalities['oldschool'],
                legalities['premodern'],
                card['reserved'],
                card['oversized'],
                card['promo'],
                card['reprint'],
                card['variation'],
                set_id,
                card['collector_number'],
                card['digital'],
                rarity_id,
                card.get('flavor_text'),
                card.get('artist'),
                card.get('illustration_id'),
                border_color_id,
                frame_id,
                card['full_art'],
                card['textless'],
                card['booster'],
                card['story_spotlight']
                )

        res = copy.write_row(values)
        #card_id = res.fetchone()[0]

        for color in card.get('colors', []):
            color_id = colors_id_map[color]
            color_cards.add((card['id'], color_id))

        for color in card['color_identity']:
            color_id = colors_id_map[color]
            color_identity_cards.add((card['id'], color_id))

        for keyword in card['keywords']:
            keyword_id = keywords_id_map[keyword]
            keyword_cards.add((card['id'], keyword_id))

        for game in card['games']:
            game_id = games_id_map[game]
            game_cards.add((card['id'], game_id))

        for finish in card['finishes']:
            finish_id = finishes_id_map[finish]
            finish_cards.add((card['id'], finish_id))

# add_new is similar to a bluk insert_or_select, but we need to
# return a value in insert_or_select and this is probably faster than
# reusing insert_or_select
def add_new(values: set, table: str, column_names: tuple[str, str]):
    columns = ""
    for index, column in enumerate(column_names):
        columns += column
        if index != len(column_names) - 1:
            columns += ', '

    cur.execute(f"SELECT {columns} FROM {table}")
    # Convert UUID object to str
    values_in_db = set([(str(value_in_db[0]), value_in_db[1]) for value_in_db in cur.fetchall()])

    new_values = values - values_in_db

    for value in new_values:
        cur.execute(f"INSERT INTO {table} ({columns}) VALUES(%s, %s)", (value[0], value[1]))

add_new(color_cards, 'ColorCards', ("CardID", "ColorID"))
add_new(color_identity_cards, 'ColorIdentityCards', ("CardID", "ColorID"))
add_new(keyword_cards, 'KeywordCards', ("CardID", "KeywordID"))
add_new(game_cards, 'GameCards', ("CardID", "GameID"))
add_new(finish_cards, 'FinishCards', ("CardID", "FinishID"))

print(f"INSERT (cards, and card junction tables) took {timeit.default_timer() - now:.2f} seconds")
now = timeit.default_timer()


for face in faces:
    res = cur.execute('INSERT INTO Faces (CardID, Name, ManaCost, TypeLine, OracleText, FlavorText, Artist, ArtistID, IllustrationID, NormalImageURI) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)', face)

print(f"INSERT faces took {timeit.default_timer() - now:.2f} seconds")
now = timeit.default_timer()

now = timeit.default_timer()
con.commit()
print(f"Commit took {timeit.default_timer() - now:.2f} seconds")

con.close()

print(f"Total time {timeit.default_timer() - start_time:.2f} seconds")
