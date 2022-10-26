#!/usr/bin/env python
import sqlite3, ijson, sys, os

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

con = sqlite3.connect('all.db')
cur = con.cursor()

cur.execute('''CREATE TABLE IF NOT EXISTS Langs
            (
            ID   INTEGER PRIMARY KEY AUTOINCREMENT,
            Lang VARCHAR             NOT NULL UNIQUE
            )
            ''')

cur.execute('''CREATE TABLE IF NOT EXISTS Layouts
            (
            ID     INTEGER     PRIMARY KEY AUTOINCREMENT,
            Layout VARCHAR                 NOT NULL UNIQUE
            )
            ''')

cur.execute('''CREATE TABLE IF NOT EXISTS ImageStatuses
            (
            ID          INTEGER     PRIMARY KEY AUTOINCREMENT,
            ImageStatus VARCHAR                 NOT NULL UNIQUE
            )
            ''')

cur.execute('''CREATE TABLE IF NOT EXISTS Legalities
            (
            ID       INTEGER     PRIMARY KEY AUTOINCREMENT,
            Legality VARCHAR                 NOT NULL UNIQUE
            )
            ''')

cur.execute('''CREATE TABLE IF NOT EXISTS SetTypes
            (
            ID   INTEGER PRIMARY KEY AUTOINCREMENT,
            Type VARCHAR             NOT NULL UNIQUE
            )
            ''')

cur.execute('''CREATE TABLE IF NOT EXISTS Sets
            (
            ID           UUID    PRIMARY KEY             NOT NULL,
            Name         VARCHAR                         NOT NULL UNIQUE,
            TypeID       INTEGER REFERENCES SetTypes(id) NOT NULL,
            Abbreviation VARCHAR                         NOT NULL UNIQUE
            )
            ''')

cur.execute('''CREATE TABLE IF NOT EXISTS Rarities
            (
            ID     INTEGER     PRIMARY KEY AUTOINCREMENT,
            Rarity VARCHAR                 NOT NULL UNIQUE
            )
            ''')

cur.execute('''CREATE TABLE IF NOT EXISTS BorderColors
            (
            ID          INTEGER     PRIMARY KEY AUTOINCREMENT,
            BorderColor VARCHAR             NOT NULL UNIQUE
            )
            ''')

cur.execute('''CREATE TABLE IF NOT EXISTS Frames
            (
            ID    INTEGER     PRIMARY KEY AUTOINCREMENT,
            Frame VARCHAR                 NOT NULL UNIQUE
            )
            ''')
# Why UNIQUE(CardID, Name, NormalImageURI)
# CardID + Name isn't sufficent because of SLD Stitch in Time (and others)
# CardID + NormalImageURI isn't sufficent because NormalImageURI is NULL
# when both "faces" are on the same side of the card (ex. aftermath cards)
# TODO: Needs colors junction
cur.execute('''CREATE TABLE IF NOT EXISTS Faces
            (
            ID             INTEGER PRIMARY KEY          AUTOINCREMENT,
            CardID         UUID    REFERENCES Cards(id)      NOT NULL,
            Name           VARCHAR                           NOT NULL,
            ManaCost       VARCHAR                           NOT NULL,
            TypeLine       VARCHAR                                   ,
            OracleText     VARCHAR                           NOT NULL,
            FlavorText     VARCHAR                                   ,
            Artist         VARCHAR                                   ,
            ArtistID       UUID                                      ,
            IllustrationID UUID                                      ,
            NormalImageURI VARCHAR                                   ,
            UNIQUE(CardID, Name, ManaCost, OracleText, IllustrationID)
            )
            ''')

# We _could_ make a table for the MultiverseIDs and
# have this be forign keys to each table, but that seems
# unnecessary
cur.execute('''CREATE TABLE IF NOT EXISTS MultiverseIDCards
            (
            ID           INTEGER PRIMARY KEY         ,
            CardID       UUID                NOT NULL,
            MultiverseID INTEGER             NOT NULL
            )
            ''')

# The (1) is ignored in sqlite, but
# it's nice just to have
cur.execute('''CREATE TABLE IF NOT EXISTS Colors
            (
            ID    INTEGER PRIMARY KEY,
            Color CHAR(1) NOT NULL UNIQUE
            )
            ''')

cur.execute('''CREATE TABLE IF NOT EXISTS ColorCards
            (
            ID      INTEGER  PRIMARY KEY,
            CardID  UUID     NOT NULL,
            ColorID INTEGER  NOT NULL,
            UNIQUE(CardID, ColorID)
            )
            ''')

cur.execute('''CREATE TABLE IF NOT EXISTS ColorIdentityCards
            (
            ID      INTEGER  PRIMARY KEY,
            CardID  UUID     NOT NULL,
            ColorID INTEGER  NOT NULL,
            UNIQUE(CardID, ColorID)
            )
            ''')

cur.execute('''CREATE TABLE IF NOT EXISTS Keywords
            (
            ID      INTEGER PRIMARY KEY,
            Keyword VARCHAR NOT NULL UNIQUE
            )
            ''')

cur.execute('''CREATE TABLE IF NOT EXISTS KeywordCards
            (
            ID        INTEGER PRIMARY KEY,
            CardID    UUID    NOT NULL,
            KeywordID INTEGER NOT NULL,
            UNIQUE(CardID, KeywordID)
            )
            ''')

cur.execute('''CREATE TABLE IF NOT EXISTS Games
            (
            ID   INTEGER PRIMARY KEY,
            Game VARCHAR NOT NULL UNIQUE
            )
            ''')

cur.execute('''CREATE TABLE IF NOT EXISTS GameCards
            (
            ID     INTEGER PRIMARY KEY,
            CardID UUID    NOT NULL,
            GameID INTEGER NOT NULL,
            UNIQUE(CardID, GameID)
            )
            ''')

cur.execute('''CREATE TABLE IF NOT EXISTS Finishes
            (
            ID     INTEGER PRIMARY KEY,
            Finish VARCHAR NOT NULL UNIQUE 
            )
            ''')

cur.execute('''CREATE TABLE IF NOT EXISTS FinishCards
            (
            ID       INTEGER PRIMARY KEY,
            CardID   UUID    NOT NULL,
            FinishID INTEGER NOT NULL,
            UNIQUE(CardID, FinishID)
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
               LangID                  INTEGER                 REFERENCES Langs(id)          NOT NULL,
               DefaultLang             BOOLEAN                                               NOT NULL,
               ReleasedAt              DATE                                                  NOT NULL,
               LayoutID                INTEGER                 REFERENCES Layouts(id)        NOT NULL,
               HighresImage            BOOLEAN                                               NOT NULL,
               ImageStatusID           INTEGER                 REFERENCES ImageStatuses(id)  NOT NULL,
               NormalImageURI          VARCHAR                                                       ,
               ManaCost                VARCHAR                                                       ,
               Cmc                     INTEGER                                                       ,
               TypeLine                VARCHAR                                                       ,
               OracleText              VARCHAR                                                       ,
               Power                   VARCHAR                                                       ,
               Toughness               VARCHAR                                                       ,
               LegalStandardID         INTEGER                 REFERENCES Legalities(id)     NOT NULL,
               LegalFutureID           INTEGER                 REFERENCES Legalities(id)     NOT NULL,
               LegalHistoricID         INTEGER                 REFERENCES Legalities(id)     NOT NULL,
               LegalGladiatorID        INTEGER                 REFERENCES Legalities(id)     NOT NULL,
               LegalPioneerID          INTEGER                 REFERENCES Legalities(id)     NOT NULL,
               LegalExplorerID         INTEGER                 REFERENCES Legalities(id)     NOT NULL,
               LegalModernID           INTEGER                 REFERENCES Legalities(id)     NOT NULL,
               LegalLegacyID           INTEGER                 REFERENCES Legalities(id)     NOT NULL,
               LegalPauperID           INTEGER                 REFERENCES Legalities(id)     NOT NULL,
               LegalVintageID          INTEGER                 REFERENCES Legalities(id)     NOT NULL,
               LegalPennyID            INTEGER                 REFERENCES Legalities(id)     NOT NULL,
               LegalCommanderID        INTEGER                 REFERENCES Legalities(id)     NOT NULL,
               LegalBrawlID            INTEGER                 REFERENCES Legalities(id)     NOT NULL,
               LegalHistoricBrawlID    INTEGER                 REFERENCES Legalities(id)     NOT NULL,
               LegalAlchemyID          INTEGER                 REFERENCES Legalities(id)     NOT NULL,
               LegalPauperCommanderID  INTEGER                 REFERENCES Legalities(id)     NOT NULL,
               LegalDuelID             INTEGER                 REFERENCES Legalities(id)     NOT NULL,
               LegalOldschoolID        INTEGER                 REFERENCES Legalities(id)     NOT NULL,
               LegalPremodernID        INTEGER                 REFERENCES Legalities(id)     NOT NULL,
               Reserved                BOOLEAN                                               NOT NULL,
               Oversized               BOOLEAN                                               NOT NULL,
               Promo                   BOOLEAN                                               NOT NULL,
               Reprint                 BOOLEAN                                               NOT NULL,
               Variation               BOOLEAN                                               NOT NULL,
               SetID                   UUID                    REFERENCES Sets(id)           NOT NULL,
               CollectorNumber         VARCHAR                                               NOT NULL,
               Digital                 BOOLEAN                                               NOT NULL,
               RarityID                INTEGER                 REFERENCES Rarities(id)       NOT NULL,
               FlavorText              VARCHAR                                                       ,
               Artist                  VARCHAR                                                       ,
               IllustrationID          UUID                                                          ,
               BorderColorID           INTEGER                 REFERENCES BorderColors(id)   NOT NULL,
               FrameID                 INTEGER                 REFERENCES Frames(id)         NOT NULL,
               FullArt                 BOOLEAN                                               NOT NULL,
               Textless                BOOLEAN                                               NOT NULL,
               Booster                 BOOLEAN                                               NOT NULL,
               StorySpotlight          BOOLEAN                                               NOT NULL
               )
             ''')


insert_statement = '''INSERT INTO Cards(ID, OracleID, MtgoID, MtgoFoilID, TcgplayerID, CardmarketID, Name, LangID, DefaultLang, ReleasedAt, LayoutID, HighresImage, ImageStatusID, NormalImageURI, ManaCost, Cmc, TypeLine, OracleText, Power, Toughness, LegalStandardID, LegalFutureID, LegalHistoricID, LegalGladiatorID, LegalPioneerID, LegalExplorerID, LegalModernID, LegalLegacyID, LegalPauperID, LegalVintageID, LegalPennyID, LegalCommanderID, LegalBrawlID, LegalHistoricBrawlID, LegalAlchemyID, LegalPauperCommanderID, LegalDuelID, LegalOldschoolID, LegalPremodernID, Reserved, Oversized, Promo, Reprint, Variation, SetID, CollectorNumber, Digital, RarityID, FlavorText, Artist, IllustrationID, BorderColorID, FrameID, FullArt, Textless, Booster, StorySpotlight)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(ID) DO
                        UPDATE
                        SET ID = ?, OracleID = ?, MtgoID = ?, MtgoFoilID = ?, TcgplayerID = ?, CardmarketID = ?, Name = ?, LangID = ?, DefaultLang = ?, ReleasedAt = ?, LayoutID = ?, HighresImage = ?, ImageStatusID = ?, NormalImageURI = ?, ManaCost = ?, Cmc = ?, TypeLine = ?, OracleText = ?, Power = ?, Toughness = ?, LegalStandardID = ?, LegalFutureID = ?, LegalHistoricID = ?, LegalGladiatorID = ?, LegalPioneerID = ?, LegalExplorerID = ?, LegalModernID = ?, LegalLegacyID = ?, LegalPauperID = ?, LegalVintageID = ?, LegalPennyID = ?, LegalCommanderID = ?, LegalBrawlID = ?, LegalHistoricBrawlID = ?, LegalAlchemyID = ?, LegalPauperCommanderID = ?, LegalDuelID = ?, LegalOldschoolID = ?, LegalPremodernID = ?, Reserved = ?, Oversized = ?, Promo = ?, Reprint = ?, Variation = ?, SetID = ?, CollectorNumber = ?, Digital = ?, RarityID = ?, FlavorText = ?, Artist = ?, IllustrationID = ?, BorderColorID = ?, FrameID = ?, FullArt = ?, Textless = ?, Booster = ?, StorySpotlight = ? RETURNING ID'''

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

for lang in langs:
    res = cur.execute('INSERT OR IGNORE INTO Langs (Lang) VALUES(?) RETURNING ID', (lang,))
for layout in layouts:
    res = cur.execute('INSERT OR IGNORE INTO Layouts (Layout) VALUES(?) RETURNING ID', (layout,))
for image_status in image_statuses:
    res = cur.execute('INSERT OR IGNORE INTO ImageStatuses (ImageStatus) VALUES(?) RETURNING ID', (image_status,))
for rarity in rarities:
    res = cur.execute('INSERT OR IGNORE INTO Rarities (Rarity) VALUES(?) RETURNING ID', (rarity,))
for border_color in border_colors:
    res = cur.execute('INSERT OR IGNORE INTO BorderColors (BorderColor) VALUES(?) RETURNING ID', (border_color,))
for frame in frames: 
    res = cur.execute('INSERT OR IGNORE INTO Frames (Frame) VALUES(?) RETURNING ID', (frame,))
for set_type in set_types:
    res = cur.execute('INSERT OR IGNORE INTO SetTypes (Type) VALUES(?) RETURNING ID', (set_type,))
for legality in legalities:
    res = cur.execute('INSERT OR IGNORE INTO Legalities (Legality) VALUES(?) RETURNING ID', (legality,))
for set_ in sets:
    res = cur.execute('SELECT ID FROM SetTypes WHERE Type == ?', (set_[2],))
    set_type_id = res.fetchone()[0]
    res = cur.execute('INSERT OR IGNORE INTO Sets (ID, Name, TypeID, Abbreviation) VALUES(?,?,?,?) RETURNING ID', (set_[0], set_[1], set_type_id, set_[3],))
for face in faces:
    res = cur.execute('INSERT OR IGNORE INTO Faces (CardID, Name, ManaCost, TypeLine, OracleText, FlavorText, Artist, ArtistID, IllustrationID, NormalImageURI) VALUES(?,?,?,?,?,?,?,?,?,?) RETURNING ID', face)
    row = res.fetchone()
    if row != None:
        #print(row)
        pass
    else:
        print(face)
        pass
for color in colors:
    res = cur.execute('INSERT OR IGNORE INTO Colors (Color) VALUES(?) RETURNING ID', (color,))
for keyword in keywords:
    res = cur.execute('INSERT OR IGNORE INTO Keywords (Keyword) VALUES(?) RETURNING ID', (keyword,))
for game in games:
    res = cur.execute('INSERT OR IGNORE INTO Games (Game) VALUES(?) RETURNING ID', (game,))
for finish in finishes:
    res = cur.execute('INSERT OR IGNORE INTO Finishes (Finish) VALUES(?) RETURNING ID', (finish,))

all_data_file.seek(0)
all_data = ijson.items(all_data_file, 'item', use_float=True)
num_cards = index + 1
for index, card in enumerate(all_data):
    if index % 1000 == 0:
        #print(f"{index}/{num_cards} {index/num_cards:.2f}")
        pass
    res = cur.execute('SELECT ID FROM Langs WHERE Lang == ?', (card['lang'],))
    lang_id = res.fetchone()[0]

    res = cur.execute('SELECT ID FROM Layouts WHERE Layout == ?', (card['layout'],))
    layout_id = res.fetchone()[0]

    res = cur.execute('SELECT ID FROM ImageStatuses WHERE ImageStatus == ?', (card['image_status'],))
    image_status_id = res.fetchone()[0]

    res = cur.execute('SELECT ID FROM Rarities WHERE Rarity == ?', (card['rarity'],))
    rarity_id = res.fetchone()[0]

    res = cur.execute('SELECT ID FROM BorderColors WHERE BorderColor == ?', (card['border_color'],))
    border_color_id = res.fetchone()[0]

    res = cur.execute('SELECT ID FROM Frames WHERE Frame == ?', (card['frame'],))
    frame_id = res.fetchone()[0]

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
        res = cur.execute('SELECT ID FROM Legalities WHERE Legality == ?', (card['legalities'][format_],))
        legality_id = res.fetchone()[0]

        legalities[format_] = legality_id

    res = cur.execute('SELECT ID FROM SetTypes WHERE Type == ?', (card['set_type'],))
    set_type_id = res.fetchone()[0]

    res = cur.execute('SELECT ID FROM Sets WHERE Name == ?', (card['set_name'],))
    set_id = res.fetchone()[0]

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

    # values * 2 because of the INSERT part and the UPDATE part
    res = cur.execute(insert_statement, values * 2)
    card_id = res.fetchone()[0]


    for color in card.get('colors', []):
        res = cur.execute('SELECT ID FROM Colors WHERE Color == ?', (color,))
        color_id = res.fetchone()[0]

        cur.execute('INSERT OR IGNORE INTO ColorCards (CardID, ColorId) VALUES(?,?)', (card['id'], color_id,))

    for color in card['color_identity']:
        res = cur.execute('SELECT ID FROM Colors WHERE Color == ?', (color,))
        color_id = res.fetchone()[0]

        cur.execute('INSERT OR IGNORE INTO ColorIdentityCards (CardID, ColorId) VALUES(?,?)', (card['id'], color_id,))

    for keyword in card['keywords']:
        res = cur.execute('SELECT ID FROM Keywords WHERE Keyword == ?', (keyword,))
        keyword_id = res.fetchone()[0]

        cur.execute('INSERT OR IGNORE INTO KeywordCards (CardID, KeywordID) VALUES(?,?)', (card['id'], keyword_id,))

    for game in card['games']:
        res = cur.execute('SELECT ID FROM Games WHERE Game == ?', (game,))
        game_id = res.fetchone()[0]

        cur.execute('INSERT OR IGNORE INTO GameCards (CardID, GameID) VALUES(?,?)', (card['id'], game_id,))

    for finish in card['finishes']:
        res = cur.execute('SELECT ID FROM Finishes WHERE Finish == ?', (finish,))
        finish_id = res.fetchone()[0]

        cur.execute('INSERT OR IGNORE INTO FinishCards (CardID, FinishID) VALUES(?,?)', (card['id'], finish_id,))

con.commit()
con.close()
