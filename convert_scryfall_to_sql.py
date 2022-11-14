#!/usr/bin/env python

# NOTES ON PERFORMANCE:
# Using UNLOGGED tables and then using ALTER TABLE ... SET LOGGED seems the same as just using LOGGED tables to begin with
# Sqlite3 is waaaay faster, for inserts but waaaay slower on the DELETES. It took about ~15 minutes or so to DELETE all the data in Sqlite3

import psycopg, ijson, sys, os, timeit

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
            ID           UUID    PRIMARY KEY             NOT NULL,
            Name         VARCHAR                         NOT NULL UNIQUE,
            TypeID       INTEGER REFERENCES SetTypes(id) DEFERRABLE INITIALLY DEFERRED NOT NULL,
            Abbreviation VARCHAR                         NOT NULL UNIQUE
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

cur.execute('DELETE FROM Layouts')
cur.execute('DELETE FROM ImageStatuses')
cur.execute('DELETE FROM Legalities')
cur.execute('DELETE FROM SetTypes')
cur.execute('DELETE FROM Sets')
cur.execute('DELETE FROM Rarities')
cur.execute('DELETE FROM BorderColors')
cur.execute('DELETE FROM Frames')
cur.execute('DELETE FROM Colors')
cur.execute('DELETE FROM Cards')
cur.execute('DELETE FROM Faces')
cur.execute('DELETE FROM MultiverseIDCards')
cur.execute('DELETE FROM ColorCards')
cur.execute('DELETE FROM ColorIdentityCards')
cur.execute('DELETE FROM Keywords')
cur.execute('DELETE FROM KeywordCards')
cur.execute('DELETE FROM Games')
cur.execute('DELETE FROM GameCards')
cur.execute('DELETE FROM Finishes')
cur.execute('DELETE FROM FinishCards')
cur.execute('DELETE FROM Langs')

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
sets = set()
faces = set()
colors = set()
keywords = set()
games = set()
finishes = set()
# This allows index to be used after the loop which effectively counts how many card there are
index = 0
for index, card in enumerate(all_data):
    langs.add(card['lang'])
    layouts.add(card['layout'])
    image_statuses.add(card['image_status'])
    rarities.add(card['rarity'])
    border_colors.add(card['border_color'])
    frames.add(card['frame'])
    set_types.add(card['set_type'])

    sets.add((card['set_id'], card['set_name'], card['set_type'], card['set']))
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
set_types_id_map = {}
legalities_id_map = {}
sets_id_map = {}
faces_id_map = {}
colors_id_map = {}
keywords_id_map = {}
games_id_map = {}
finishes_id_map = {}


for lang in langs:
    res = cur.execute('INSERT INTO Langs (Lang) VALUES(%s) RETURNING ID', (lang,))
    id_ = res.fetchone()[0]
    langs_id_map[lang] = id_
for layout in layouts:
    res = cur.execute('INSERT INTO Layouts (Layout) VALUES(%s) RETURNING ID', (layout,))
    id_ = res.fetchone()[0]
    layouts_id_map[layout] = id_
for image_status in image_statuses:
    res = cur.execute('INSERT INTO ImageStatuses (ImageStatus) VALUES(%s) RETURNING ID', (image_status,))
    id_ = res.fetchone()[0]
    image_statuses_id_map[image_status] = id_
for rarity in rarities:
    res = cur.execute('INSERT INTO Rarities (Rarity) VALUES(%s) RETURNING ID', (rarity,))
    id_ = res.fetchone()[0]
    rarities_id_map[rarity] = id_
for border_color in border_colors:
    res = cur.execute('INSERT INTO BorderColors (BorderColor) VALUES(%s) RETURNING ID', (border_color,))
    id_ = res.fetchone()[0]
    border_colors_id_map[border_color] = id_
for frame in frames: 
    res = cur.execute('INSERT INTO Frames (Frame) VALUES(%s) RETURNING ID', (frame,))
    id_ = res.fetchone()[0]
    frames_id_map[frame] = id_
for set_type in set_types:
    res = cur.execute('INSERT INTO SetTypes (Type) VALUES(%s) RETURNING ID', (set_type,))
    id_ = res.fetchone()[0]
    set_types_id_map[set_type] = id_
for legality in legalities:
    res = cur.execute('INSERT INTO Legalities (Legality) VALUES(%s) RETURNING ID', (legality,))
    id_ = res.fetchone()[0]
    legalities_id_map[legality] = id_
for set_ in sets:
    res = cur.execute('SELECT ID FROM SetTypes WHERE Type = %s', (set_[2],))
    set_type_id = res.fetchone()[0]
    res = cur.execute('INSERT INTO Sets (ID, Name, TypeID, Abbreviation) VALUES(%s,%s,%s,%s) RETURNING ID', (set_[0], set_[1], set_type_id, set_[3],))
    id_ = res.fetchone()[0]
    sets_id_map[set_[1]] = id_
for color in colors:
    res = cur.execute('INSERT INTO Colors (Color) VALUES(%s) RETURNING ID', (color,))
    id_ = res.fetchone()[0]
    colors_id_map[color] = id_
for keyword in keywords:
    res = cur.execute('INSERT INTO Keywords (Keyword) VALUES(%s) RETURNING ID', (keyword,))
    id_ = res.fetchone()[0]
    keywords_id_map[keyword ] = id_
for game in games:
    res = cur.execute('INSERT INTO Games (Game) VALUES(%s) RETURNING ID', (game,))
    id_ = res.fetchone()[0]
    games_id_map[game] = id_
for finish in finishes:
    res = cur.execute('INSERT INTO Finishes (Finish) VALUES(%s) RETURNING ID', (finish,))
    id_ = res.fetchone()[0]
    finishes_id_map[finish] = id_


color_cards = []
color_identity_cards = []
keyword_cards = []
game_cards = []
finish_cards = []

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
            color_cards.append((card['id'], color_id))

        for color in card['color_identity']:
            color_id = colors_id_map[color]
            color_identity_cards.append((card['id'], color_id))

        for keyword in card['keywords']:
            keyword_id = keywords_id_map[keyword]
            keyword_cards.append((card['id'], keyword_id))

        for game in card['games']:
            game_id = games_id_map[game]
            game_cards.append((card['id'], game_id))

        for finish in card['finishes']:
            finish_id = finishes_id_map[finish]
            finish_cards.append((card['id'], finish_id))


with cur.copy("COPY ColorCards (CardID, ColorID) FROM STDIN") as copy:
    for card_color in color_cards:
        copy.write_row(card_color)

with cur.copy("COPY ColorIdentityCards (CardID, ColorID) FROM STDIN") as copy:
    for card_color in color_identity_cards:
        copy.write_row(card_color)

with cur.copy("COPY KeywordCards (CardID, KeywordID) FROM STDIN") as copy:
    for card_keyword in keyword_cards:
        copy.write_row(card_keyword)

with cur.copy("COPY GameCards (CardID, GameID) FROM STDIN") as copy:
    for card_game in game_cards:
        copy.write_row(card_game)

with cur.copy("COPY FinishCards (CardID, FinishID) FROM STDIN") as copy:
    for card_finish in finish_cards:
        copy.write_row(card_finish)

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
