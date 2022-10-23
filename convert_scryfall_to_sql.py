#!/usr/bin/env python
import sqlite3, json, sys, os

if len(sys.argv) != 3:
    print("Expected exactly two arguments, the path to the ALL data and the path to the DEFAULT data")

with open(sys.argv[1]) as f:
    all_data = json.load(f)

with open(sys.argv[2]) as f:
    default_data = json.load(f)

if len(all_data) < len(default_data):
    print("ALL database has fewer cards than DEFAULT database, arguments are probably in wrong order.")
    exit(1)

default_set = set()

# Populate default_set with all the scryfall_ids
# of the default cards
for card in default_data:
    scryfall_id = card['id']

    if scryfall_id in default_set:
        print("Found duplicate id somehow")
        exit(2)

    default_set.add(scryfall_id)

if os.path.exists('all.db'):
    os.remove('all.db')

con = sqlite3.connect('all.db')
cur = con.cursor()

cur.execute('''CREATE TABLE Langs
            (
            ID   INTEGER PRIMARY KEY AUTOINCREMENT,
            Lang VARCHAR             NOT NULL UNIQUE
            )
            ''')

cur.execute('''CREATE TABLE Layouts
            (
            ID     INTEGER     PRIMARY KEY AUTOINCREMENT,
            Layout VARCHAR                 NOT NULL UNIQUE
            )
            ''')

cur.execute('''CREATE TABLE ImageStatuses
            (
            ID          INTEGER     PRIMARY KEY AUTOINCREMENT,
            ImageStatus VARCHAR                 NOT NULL UNIQUE
            )
            ''')

cur.execute('''CREATE TABLE Legalities
            (
            ID       INTEGER     PRIMARY KEY AUTOINCREMENT,
            Legality VARCHAR                 NOT NULL UNIQUE
            )
            ''')

cur.execute('''CREATE TABLE SetTypes
            (
            ID   INTEGER PRIMARY KEY AUTOINCREMENT,
            Type VARCHAR             NOT NULL UNIQUE
            )
            ''')

cur.execute('''CREATE TABLE Sets
            (
            ID           UUID    PRIMARY KEY             NOT NULL,
            Name         VARCHAR                         NOT NULL UNIQUE,
            TypeID       INTEGER REFERENCES SetTypes(id) NOT NULL,
            Abbreviation VARCHAR                         NOT NULL UNIQUE
            )
            ''')

cur.execute('''CREATE TABLE Rarities
            (
            ID     INTEGER     PRIMARY KEY AUTOINCREMENT,
            Rarity VARCHAR                 NOT NULL UNIQUE
            )
            ''')

cur.execute('''CREATE TABLE BorderColors
            (
            ID          INTEGER     PRIMARY KEY AUTOINCREMENT,
            BorderColor VARCHAR             NOT NULL UNIQUE
            )
            ''')

cur.execute('''CREATE TABLE Frames
            (
            ID    INTEGER     PRIMARY KEY AUTOINCREMENT,
            Frame VARCHAR                 NOT NULL UNIQUE
            )
            ''')

# Needs colors junction
cur.execute('''CREATE TABLE Faces
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
            NormalImageURI VARCHAR
            )
            ''')

# We _could_ make a table for the MultiverseIDs and
# have this be forign keys to each table, but that seems
# unnecessary
cur.execute('''CREATE TABLE MultiverseIDCards
            (
            ID           INTEGER PRIMARY KEY         ,
            CardID       UUID                NOT NULL,
            MultiverseID INTEGER             NOT NULL
            )
            ''')

# The (1) is ignored in sqlite, but
# it's nice just to have
cur.execute('''CREATE TABLE Colors
            (
            ID    INTEGER PRIMARY KEY,
            Color CHAR(1) NOT NULL UNIQUE
            )
            ''')

cur.execute('''CREATE TABLE ColorCards
            (
            ID      INTEGER  PRIMARY KEY,
            CardID  UUID     NOT NULL,
            ColorID INTEGER  NOT NULL
            )
            ''')

cur.execute('''CREATE TABLE ColorIdentityCards
            (
            ID      INTEGER  PRIMARY KEY,
            CardID  UUID     NOT NULL,
            ColorID INTEGER  NOT NULL
            )
            ''')

cur.execute('''CREATE TABLE Keywords
            (
            ID      INTEGER PRIMARY KEY,
            Keyword VARCHAR NOT NULL UNIQUE
            )
            ''')

cur.execute('''CREATE TABLE KeywordCards
            (
            ID        INTEGER PRIMARY KEY,
            CardID    UUID    NOT NULL,
            KeywordID INTEGER NOT NULL
            )
            ''')

cur.execute('''CREATE TABLE Games
            (
            ID   INTEGER PRIMARY KEY,
            Game VARCHAR NOT NULL UNIQUE
            )
            ''')

cur.execute('''CREATE TABLE GameCards
            (
            ID     INTEGER PRIMARY KEY,
            CardID UUID    NOT NULL,
            GameID INTEGER NOT NULL
            )
            ''')

cur.execute('''CREATE TABLE Finishes
            (
            ID     INTEGER PRIMARY KEY,
            Finish VARCHAR NOT NULL UNIQUE 
            )
            ''')

cur.execute('''CREATE TABLE FinishCards
            (
            ID       INTEGER PRIMARY KEY,
            CardID   UUID    NOT NULL,
            FinishID INTEGER NOT NULL
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
cur.execute('''CREATE TABLE Cards
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


insert_statement = 'INSERT INTO cards(ID, OracleID, MtgoID, MtgoFoilID, TcgplayerID, CardmarketID, Name, LangID, DefaultLang, ReleasedAt, LayoutID, HighresImage, ImageStatusID, NormalImageURI, ManaCost, Cmc, TypeLine, OracleText, Power, Toughness, LegalStandardID, LegalFutureID, LegalHistoricID, LegalGladiatorID, LegalPioneerID, LegalExplorerID, LegalModernID, LegalLegacyID, LegalPauperID, LegalVintageID, LegalPennyID, LegalCommanderID, LegalBrawlID, LegalHistoricBrawlID, LegalAlchemyID, LegalPauperCommanderID, LegalDuelID, LegalOldschoolID, LegalPremodernID, Reserved, Oversized, Promo, Reprint, Variation, SetID, CollectorNumber, Digital, RarityID, FlavorText, Artist, IllustrationID, BorderColorID, FrameID, FullArt, Textless, Booster, StorySpotlight) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) RETURNING ID'

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
    res = cur.execute('INSERT INTO Langs (Lang) VALUES(?) RETURNING ID', (lang,))
for layout in layouts:
    res = cur.execute('INSERT INTO Layouts (Layout) VALUES(?) RETURNING ID', (layout,))
for image_status in image_statuses:
    res = cur.execute('INSERT INTO ImageStatuses (ImageStatus) VALUES(?) RETURNING ID', (image_status,))
for rarity in rarities:
    res = cur.execute('INSERT INTO Rarities (Rarity) VALUES(?) RETURNING ID', (rarity,))
for border_color in border_colors:
    res = cur.execute('INSERT INTO BorderColors (BorderColor) VALUES(?) RETURNING ID', (border_color,))
for frame in frames: 
    res = cur.execute('INSERT INTO Frames (Frame) VALUES(?) RETURNING ID', (frame,))
for set_type in set_types:
    res = cur.execute('INSERT INTO SetTypes (Type) VALUES(?) RETURNING ID', (set_type,))
for legality in legalities:
    res = cur.execute('INSERT INTO Legalities (Legality) VALUES(?) RETURNING ID', (legality,))
for set_ in sets:
    res = cur.execute('SELECT ID FROM SetTypes WHERE Type == ?', (set_[2],))
    set_type_id = res.fetchone()[0]
    res = cur.execute('INSERT INTO Sets (ID, Name, TypeID, Abbreviation) VALUES(?,?,?,?) RETURNING ID', (set_[0], set_[1], set_type_id, set_[3],))
for face in faces:
    res = cur.execute('INSERT INTO Faces (CardID, Name, ManaCost, TypeLine, OracleText, FlavorText, Artist, ArtistID, IllustrationID, NormalImageURI) VALUES(?,?,?,?,?,?,?,?,?,?) RETURNING ID', face)
for color in colors:
    res = cur.execute('INSERT INTO Colors (Color) VALUES(?) RETURNING ID', (color,))
for keyword in keywords:
    res = cur.execute('INSERT INTO Keywords (Keyword) VALUES(?) RETURNING ID', (keyword,))
for game in games:
    res = cur.execute('INSERT INTO Games (Game) VALUES(?) RETURNING ID', (game,))
for finish in finishes:
    res = cur.execute('INSERT INTO Finishes (Finish) VALUES(?) RETURNING ID', (finish,))


num_cards = len(all_data)
for index, card in enumerate(all_data):
    if index % 1000 == 0:
        print(f"{index}/{num_cards} {index/num_cards:.2f}")
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

    res = cur.execute(insert_statement, values)
    card_id = res.fetchone()[0]


    for color in card.get('colors', []):
        res = cur.execute('SELECT ID FROM Colors WHERE Color == ?', (color,))
        color_id = res.fetchone()[0]

        cur.execute('INSERT INTO ColorCards (CardID, ColorId) VALUES(?,?)', (card['id'], color_id,))

    for color in card['color_identity']:
        res = cur.execute('SELECT ID FROM Colors WHERE Color == ?', (color,))
        color_id = res.fetchone()[0]

        cur.execute('INSERT INTO ColorIdentityCards (CardID, ColorId) VALUES(?,?)', (card['id'], color_id,))

    for keyword in card['keywords']:
        res = cur.execute('SELECT ID FROM Keywords WHERE Keyword == ?', (keyword,))
        keyword_id = res.fetchone()[0]

        cur.execute('INSERT INTO KeywordCards (CardID, KeywordID) VALUES(?,?)', (card['id'], keyword_id,))

    for game in card['games']:
        res = cur.execute('SELECT ID FROM Games WHERE Game == ?', (game,))
        game_id = res.fetchone()[0]

        cur.execute('INSERT INTO GameCards (CardID, GameID) VALUES(?,?)', (card['id'], game_id,))

    for finish in card['finishes']:
        res = cur.execute('SELECT ID FROM Finishes WHERE Finish == ?', (finish,))
        finish_id = res.fetchone()[0]

        cur.execute('INSERT INTO FinishCards (CardID, FinishID) VALUES(?,?)', (card['id'], finish_id,))

con.commit()
#['object', 'id', 'oracle_id', 'multiverse_ids', 'mtgo_id', 'mtgo_foil_id', 'tcgplayer_id', 'cardmarket_id', 'name', 'lang', 'released_at', 'uri', 'scryfall_uri', 'layout', 'highres_image', 'image_status', 'image_uris', 'mana_cost', 'cmc', 'type_line', 'oracle_text', 'power', 'toughness', 'colors', 'color_identity', 'keywords', 'legalities', 'games', 'reserved', 'foil', 'nonfoil', 'finishes', 'oversized', 'promo', 'reprint', 'variation', 'set_id', 'set', 'set_name', 'set_type', 'set_uri', 'set_search_uri', 'scryfall_set_uri', 'rulings_uri', 'prints_search_uri', 'collector_number', 'digital', 'rarity', 'flavor_text', 'card_back_id', 'artist', 'artist_ids', 'illustration_id', 'border_color', 'frame', 'full_art', 'textless', 'booster', 'story_spotlight', 'edhrec_rank', 'penny_rank', 'prices', 'related_uris']

t = {
  "object": "card",
  "id": "0000579f-7b35-4ed3-b44c-db2a538066fe",
  "oracle_id": "44623693-51d6-49ad-8cd7-140505caf02f",
  "multiverse_ids": [
    109722
  ],
  "mtgo_id": 25527,
  "mtgo_foil_id": 25528,
  "tcgplayer_id": 14240,
  "cardmarket_id": 13850,
  "name": "Fury Sliver",
  "lang": "en",
  "released_at": "2006-10-06",
  "uri": "https://api.scryfall.com/cards/0000579f-7b35-4ed3-b44c-db2a538066fe",
  "scryfall_uri": "https://scryfall.com/card/tsp/157/fury-sliver?utm_source=api",
  "layout": "normal",
  "highres_image": True,
  "image_status": "highres_scan",
  "image_uris": {
    "small": "https://cards.scryfall.io/small/front/0/0/0000579f-7b35-4ed3-b44c-db2a538066fe.jpg?1562894979",
    "normal": "https://cards.scryfall.io/normal/front/0/0/0000579f-7b35-4ed3-b44c-db2a538066fe.jpg?1562894979",
    "large": "https://cards.scryfall.io/large/front/0/0/0000579f-7b35-4ed3-b44c-db2a538066fe.jpg?1562894979",
    "png": "https://cards.scryfall.io/png/front/0/0/0000579f-7b35-4ed3-b44c-db2a538066fe.png?1562894979",
    "art_crop": "https://cards.scryfall.io/art_crop/front/0/0/0000579f-7b35-4ed3-b44c-db2a538066fe.jpg?1562894979",
    "border_crop": "https://cards.scryfall.io/border_crop/front/0/0/0000579f-7b35-4ed3-b44c-db2a538066fe.jpg?1562894979"
  },
  "mana_cost": "{5}{R}",
  "cmc": 6,
  "type_line": "Creature — Sliver",
  "oracle_text": "All Sliver creatures have double strike.",
  "power": "3",
  "toughness": "3",
  "colors": [
    "R"
  ],
  "color_identity": [
    "R"
  ],
  "keywords": [],
  "legalities": {
    "standard": "not_legal",
    "future": "not_legal",
    "historic": "not_legal",
    "gladiator": "not_legal",
    "pioneer": "not_legal",
    "explorer": "not_legal",
    "modern": "legal",
    "legacy": "legal",
    "pauper": "not_legal",
    "vintage": "legal",
    "penny": "legal",
    "commander": "legal",
    "brawl": "not_legal",
    "historicbrawl": "not_legal",
    "alchemy": "not_legal",
    "paupercommander": "restricted",
    "duel": "legal",
    "oldschool": "not_legal",
    "premodern": "not_legal"
  },
  "games": [
    "paper",
    "mtgo"
  ],
  "reserved": False,
  "foil": True,
  "nonfoil": True,
  "finishes": [
    "nonfoil",
    "foil"
  ],
  "oversized": False,
  "promo": False,
  "reprint": False,
  "variation": False,
  "set_id": "c1d109bc-ffd8-428f-8d7d-3f8d7e648046",
  "set": "tsp",
  "set_name": "Time Spiral",
  "set_type": "expansion",
  "set_uri": "https://api.scryfall.com/sets/c1d109bc-ffd8-428f-8d7d-3f8d7e648046",
  "set_search_uri": "https://api.scryfall.com/cards/search?order=set&q=e%3Atsp&unique=prints",
  "scryfall_set_uri": "https://scryfall.com/sets/tsp?utm_source=api",
  "rulings_uri": "https://api.scryfall.com/cards/0000579f-7b35-4ed3-b44c-db2a538066fe/rulings",
  "prints_search_uri": "https://api.scryfall.com/cards/search?order=released&q=oracleid%3A44623693-51d6-49ad-8cd7-140505caf02f&unique=prints",
  "collector_number": "157",
  "digital": False,
  "rarity": "uncommon",
  "flavor_text": "\"A rift opened, and our arrows were abruptly stilled. To move was to push the world. But the sliver's claw still twitched, red wounds appeared in Thed's chest, and ribbons of blood hung in the air.\"\n—Adom Capashen, Benalish hero",
  "card_back_id": "0aeebaf5-8c7d-4636-9e82-8c27447861f7",
  "artist": "Paolo Parente",
  "artist_ids": [
    "d48dd097-720d-476a-8722-6a02854ae28b"
  ],
  "illustration_id": "2fcca987-364c-4738-a75b-099d8a26d614",
  "border_color": "black",
  "frame": "2003",
  "full_art": False,
  "textless": False,
  "booster": True,
  "story_spotlight": False,
  "edhrec_rank": 5652,
  "penny_rank": 10628,
  "prices": {
    "usd": "0.30",
    "usd_foil": "4.50",
    "usd_etched": None,
    "eur": "0.16",
    "eur_foil": "1.84",
    "tix": "0.02"
  },
  "related_uris": {
    "gatherer": "https://gatherer.wizards.com/Pages/Card/Details.aspx?multiverseid=109722",
    "tcgplayer_infinite_articles": "https://infinite.tcgplayer.com/search?contentMode=article&game=magic&partner=scryfall&q=Fury+Sliver&utm_campaign=affiliate&utm_medium=api&utm_source=scryfall",
    "tcgplayer_infinite_decks": "https://infinite.tcgplayer.com/search?contentMode=deck&game=magic&partner=scryfall&q=Fury+Sliver&utm_campaign=affiliate&utm_medium=api&utm_source=scryfall",
    "edhrec": "https://edhrec.com/route/?cc=Fury+Sliver"
  }
}

faces = [
    {
      "object": "card_face",
      "name": "Spikefield Hazard",
      "mana_cost": "{R}",
      "type_line": "Instant",
      "oracle_text": "Spikefield Hazard deals 1 damage to any target. If a permanent dealt damage this way would die this turn, exile it instead.",
      "colors": [
        "R"
      ],
      "flavor_text": "\"Stop screaming! You'll only bring down more spikes.\"\n—Raff Slugeater, goblin shortcutter",
      "artist": "Tomasz Jedruszek",
      "artist_id": "bba69285-2445-4a4b-a847-59397be972ea",
      "illustration_id": "41ff249a-5698-43da-880b-9a880ef84937",
      "image_uris": {
        "small": "https://cards.scryfall.io/small/front/a/6/a69541db-3f4e-412f-aa8e-dec1e74f74dc.jpg?1604198070",
        "normal": "https://cards.scryfall.io/normal/front/a/6/a69541db-3f4e-412f-aa8e-dec1e74f74dc.jpg?1604198070",
        "large": "https://cards.scryfall.io/large/front/a/6/a69541db-3f4e-412f-aa8e-dec1e74f74dc.jpg?1604198070",
        "png": "https://cards.scryfall.io/png/front/a/6/a69541db-3f4e-412f-aa8e-dec1e74f74dc.png?1604198070",
        "art_crop": "https://cards.scryfall.io/art_crop/front/a/6/a69541db-3f4e-412f-aa8e-dec1e74f74dc.jpg?1604198070",
        "border_crop": "https://cards.scryfall.io/border_crop/front/a/6/a69541db-3f4e-412f-aa8e-dec1e74f74dc.jpg?1604198070"
      }
    },
    {
      "object": "card_face",
      "name": "Spikefield Cave",
      "flavor_name": "",
      "mana_cost": "",
      "type_line": "Land",
      "oracle_text": "Spikefield Cave enters the battlefield tapped.\n{T}: Add {R}.",
      "colors": [],
      "flavor_text": "\"Silence until we're through. Even a whisper's echo can dislodge death from above.\"\n—Raff Slugeater, goblin shortcutter",
      "artist": "Tomasz Jedruszek",
      "artist_id": "bba69285-2445-4a4b-a847-59397be972ea",
      "illustration_id": "0f0c1e52-06d8-4129-af66-97ec23586721",
      "image_uris": {
        "small": "https://cards.scryfall.io/small/back/a/6/a69541db-3f4e-412f-aa8e-dec1e74f74dc.jpg?1604198070",
        "normal": "https://cards.scryfall.io/normal/back/a/6/a69541db-3f4e-412f-aa8e-dec1e74f74dc.jpg?1604198070",
        "large": "https://cards.scryfall.io/large/back/a/6/a69541db-3f4e-412f-aa8e-dec1e74f74dc.jpg?1604198070",
        "png": "https://cards.scryfall.io/png/back/a/6/a69541db-3f4e-412f-aa8e-dec1e74f74dc.png?1604198070",
        "art_crop": "https://cards.scryfall.io/art_crop/back/a/6/a69541db-3f4e-412f-aa8e-dec1e74f74dc.jpg?1604198070",
        "border_crop": "https://cards.scryfall.io/border_crop/back/a/6/a69541db-3f4e-412f-aa8e-dec1e74f74dc.jpg?1604198070"
      }
    }
  ]
