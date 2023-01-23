import psycopg, config, convert_scryfall_to_sql, requests, os, logging

def get_stream(url):
    s = requests.Session()
    with s.get(url, headers=None, stream=True) as resp:
        for chunk in resp.iter_content(chunk_size=512):
            yield chunk

def import_from_scryfall():
    response = requests.get("https://api.scryfall.com/bulk-data")
    all_cards_path = "all_cards.json"
    default_cards_path = "default_cards.json"
    all_data_file = open(all_cards_path, 'wb')
    default_data_file = open(default_cards_path, 'wb')
    for bulk_data in response.json()['data']:
        if bulk_data['type'] == 'all_cards':
            uri = bulk_data['download_uri']
            logging.info(f"Downloading all_cards data from {uri}")
            for chunk in get_stream(uri):
                all_data_file.write(chunk)

        elif bulk_data['type'] == 'default_cards':
            uri = bulk_data['download_uri']
            logging.info(f"Downloading default_cards data from {uri}")
            for chunk in get_stream(uri):
                default_data_file.write(chunk)

    all_data_file.close()
    default_data_file.close()

    # Reopen with read permissions
    all_data_file = open(all_cards_path, 'r')
    default_data_file = open(default_cards_path, 'r')

    logging.info(f"Converting scryfall data into database")
    convert_scryfall_to_sql.convert(all_data_file, default_data_file)

    os.remove(all_cards_path)
    os.remove(default_cards_path)

def create_tables():
    con = psycopg.connect(user = config.get('DB_USER'), password = config.get('DB_PASSWORD'), host = config.get('DB_HOST'), port = config.get('DB_PORT'))
    cur = con.cursor()

    # We use a lock here because multiple concurrent CREATE TABLE commands
    # cause issues with postgres, see here
    # https://www.postgresql.org/message-id/CA+TgmoZAdYVtwBfp1FL2sMZbiHCWT4UPrzRLNnX1Nb30Ku3-gg@mail.gmail.com
    cur.execute('SELECT pg_advisory_lock(0)')

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
                   StorySpotlight          BOOLEAN                                               NOT NULL,
                   UNIQUE(SetID, CollectorNumber, LangID)
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


    cur.execute('''CREATE TABLE IF NOT EXISTS Users
                (
                ID           INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
                Username     VARCHAR NOT NULL,
                PasswordHash VARCHAR NOT NULL,
                UNIQUE(Username)
                )
                ''')

    # Why aren't we salting these hashes?
    # https://security.stackexchange.com/questions/209936/do-i-need-to-use-salt-with-api-key-hashing
    cur.execute('''CREATE TABLE IF NOT EXISTS APITokens
                (
                ID         INTEGER     PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
                UserID     INTEGER     REFERENCES Users(ID) NOT NULL,
                TokenHash  BYTEA       UNIQUE NOT NULL,
                ValidUntil TIMESTAMPTZ
                )
                ''')

    res = cur.execute("""
                SELECT *
                  FROM pg_type typ
                       INNER JOIN pg_namespace nsp
                                  ON nsp.oid = typ.typnamespace
                  WHERE nsp.nspname = current_schema()
                        AND typ.typname = 'condition'""")

    # Create condition type if it doesn't exist
    condition_type = res.fetchone()
    if condition_type == None:
        cur.execute("""CREATE TYPE condition AS ENUM
                    ('Damaged', 'Heavily Played', 'Moderately Played', 'Lightly Played', 'Near Mint')""")


    cur.execute('''CREATE TABLE IF NOT EXISTS Collections
                (
                ID           INTEGER   PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
                UserID       INTEGER   REFERENCES Users(ID)       DEFERRABLE INITIALLY DEFERRED NOT NULL,
                FinishCardID INTEGER   REFERENCES FinishCards(ID) DEFERRABLE INITIALLY DEFERRED NOT NULL,
                Condition    condition NOT NULL,
                Signed       BOOLEAN   NOT NULL,
                Altered      BOOLEAN   NOT NULL,
                Notes        VARCHAR   NOT NULL,
                Quantity     INTEGER   NOT NULL,
                UNIQUE(UserID, FinishCardID, Condition, Signed, Altered, Notes)
                )
                ''')
    con.commit()
    cur.execute('SELECT pg_advisory_unlock(0)')
    con.close()
