from flask import Flask, request, url_for, redirect, abort, render_template_string, flash
from urllib.parse import urlparse, urljoin
from flask_login import LoginManager, login_required, login_user, logout_user
import json, sqlite3, psycopg
import hashlib, binascii
import flask_login
import secrets
import config
from datetime import datetime
from argon2 import PasswordHasher

login_manager = LoginManager()

app = Flask(__name__)
login_manager.init_app(app)

HASH_FUNCTION = 'SHA3-512'
app.config['SECRET_KEY'] = config.SECRET_KEY


con = psycopg.connect(user = "postgres", password = "password", host = "127.0.0.1", port = "5432")
cur = con.cursor()


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

ph = PasswordHasher()
password_hash = ph.hash('foo')

cur.execute('''INSERT INTO Users(Username, PasswordHash) VALUES(%s, %s) ON CONFLICT DO NOTHING''', ('me', password_hash))

con.commit()

class User:
    def __init__(self, id, password):
        self.id = id
        self.password = password
        self.is_authenticated = True
        self.is_active = True
        self.is_anonymous = False

    def get_id(self):
        return self.id

# Matches the function name that you want to go to
login_manager.login_view = "login"

users = {}
users['me'] = User('me', 'foo')
PAGE_SIZE = 25

# Ensures the url isn't leaving our site
# Good for making sure redirects are safe
def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
           ref_url.netloc == test_url.netloc

@login_manager.user_loader
def load_user(user_id):
    return users.get(user_id)

@app.route("/")
def index():
    return '''
<style>
    .grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, 150px)
    }
</style>
<div class="grid"></div>'''

def get_database_connection():
    con = psycopg.connect(user = "postgres", password = "password", host = "127.0.0.1", port = "5432")
    return con

def get_user_id(cur: psycopg.Cursor) -> tuple[int, None] | tuple[None, dict]:
    auth_header = request.headers.get('Authorization')
    if auth_header:
        header_parts = auth_header.split(' ')
        invalid_format_error = {'successful': False, 'error': f"Authorization header not formatted correctly. Expected \"Bearer <token>\""}

        if len(header_parts) != 2:
            return None, invalid_format_error

        bearer, token = header_parts
        if bearer != 'Bearer':
            return None, invalid_format_error

        user_id, error = get_user_id_from_token(cur, token)
        if error:
            return None, error
    else:
        user_id, error = get_user_id_from_session(cur)
        if error:
            return None, error

    return user_id, None


def get_user_id_from_session(cur: psycopg.Cursor) -> tuple[int, None] | tuple[None, dict]:
    username = flask_login.current_user.get_id()

    res = cur.execute('SELECT ID FROM Users WHERE Username = %s', (username,))
    user_id = res.fetchone()

    if user_id == None:
        return (None, {'successful': False, 'error': "Couldn't find user ID in database."})

    user_id = user_id[0]

    return (user_id, None)

def get_user_id_from_token(cur: psycopg.Cursor, token: str) -> tuple[int, None] | tuple[None, dict]:
    hasher = hashlib.new(HASH_FUNCTION)
    hasher.update(binascii.unhexlify(token))
    hashed_token_bytes = hasher.digest()

    cur.execute('''SELECT Users.ID, APITokens.ValidUntil FROM Users
                   INNER JOIN APITokens ON APITokens.UserID = Users.ID
                   WHERE APITokens.TokenHash = %s''', (hashed_token_bytes, ))

    row = cur.fetchone()
    if row == None:
        error = {'successful': False, 'error': "Token is invalid"}
        return None, error

    user_id, valid_until = row
    if valid_until < datetime.now().astimezone():
        error = {'successful': False, 'error': 'That token has expired'}
        return None, error

    return user_id, None

def api_collection_search(search_text: str, page: int):
    con = get_database_connection()
    cur = con.cursor()

    cards = []

    user_id, error = get_user_id(cur)
    if error:
        return json.dumps(error)

    res = cur.execute('''SELECT colls.ID, cards.ID, cards.Name, finishes.Finish, colls.Condition, langs.Lang, colls.Signed, colls.Altered, colls.Notes, colls.Quantity FROM Collections colls
                      INNER JOIN FinishCards finishCards ON colls.FinishCardID = finishCards.ID
                      INNER JOIN Cards cards ON finishCards.CardID = cards.ID
                      INNER JOIN Finishes finishes ON finishCards.FinishID = finishes.ID
                      INNER JOIN Langs langs ON cards.langID = langs.ID
                      WHERE colls.UserID = %s
                      ORDER BY cards.Name, cards.ReleasedAt DESC
                      ''', (user_id,))
    results = res.fetchall()

    for collection_id, scryfall_id, name, finish, condition, language, signed, altered, notes, quantity in results:
        if search_text.lower() in name.lower():
            cards.append({'collection_id': collection_id, 'scryfall_id': str(scryfall_id), 'finish': finish, 'quantity': quantity,
                          'condition': condition, 'language': language, 'signed': signed,
                          'altered': altered, 'notes': notes})

    length = len(cards)

    start = PAGE_SIZE * page
    end = start + PAGE_SIZE
    cards = cards[start:end]

    return json.dumps({'cards': cards, 'length': length})

@app.route("/api/all_cards/languages")
def api_all_cards_languages():
    con = get_database_connection()
    cur = con.cursor()

    args = request.args
    scryfall_id = args.get('scryfall_id')

    if not scryfall_id:
        error = {'successful': False, 'error': 'Expected query param "scryfall_id"'}
        return json.dumps(error)

    res = cur.execute('''SELECT A.ID, A.DefaultLang, Langs.Lang FROM Cards A
                CROSS JOIN Cards B
                INNER JOIN Langs ON A.LangID = Langs.ID
                WHERE B.ID = %s AND A.CollectorNumber = B.CollectorNumber AND A.SetID = B.SetID''', (scryfall_id,))

    rows = res.fetchall()
    if len(rows) == 0:
        error = {'successful': False, 'error': f"Couldn't find a card with scryfall_id \"{scryfall_id}\""}
        return json.dumps(error)

    languages = []

    for row in rows:
        id_ = row[0]
        default = row[1]
        lang = row[2]
        obj = {
                'scryfall_id': str(id_),
                'default': bool(default),
                'lang': lang
                }

        languages.append(obj)

    return json.dumps(languages)

@app.route("/api/by_id")
def api_by_id():
    con = get_database_connection()
    cur = con.cursor()

    args = request.args
    scryfall_id = args.get('scryfall_id')

    if scryfall_id == None:
        error = {'successful': False, 'error': 'Expected query param "scryfall_id"'}
        return json.dumps(error)

    res = cur.execute("""SELECT Cards.ID, Cards.NormalImageURI, Finishes.Finish, Langs.Lang FROM Cards
                      INNER JOIN FinishCards ON Cards.ID = FinishCards.CardID
                      INNER JOIN Finishes ON FinishCards.FinishID = Finishes.ID
                      INNER JOIN Langs ON Cards.LangID = Langs.ID
                      WHERE Cards.ID = %s""", (scryfall_id,))
    entries = res.fetchall()

    if len(entries) == 0:
        error = {'successful': False, 'error': f"Couldn't find card with provided scryfall_id \"{scryfall_id}\""}
        return json.dumps(error)

    card = {'scryfall_id': scryfall_id, 'finishes': [], 'image_uri': entries[0][1], 'lang': entries[0][3]}
    for entry in entries:
        card['finishes'].append(entry[2])


    return json.dumps(card)


def api_all_cards_search(search_text: str, page: int, default: bool):
    con = get_database_connection()
    cur = con.cursor()

    cards = []
    search_string = f'%{search_text}%'

    if default:
        res = cur.execute('''SELECT COUNT(*) FROM Cards
                          WHERE LOWER(Name) LIKE %s AND DefaultLang = true''',
                          (search_string,))
        length = res.fetchone()[0]

        res = cur.execute('''SELECT ID FROM Cards
                          WHERE LOWER(Name) LIKE %s AND DefaultLang = true
                          ORDER BY Name, ReleasedAt DESC
                          LIMIT %s OFFSET %s
                          ''',
                          (search_string, PAGE_SIZE, page * PAGE_SIZE))
    else:
        res = cur.execute('''SELECT COUNT(*) FROM Cards
                          WHERE LOWER(Name) LIKE %s
                          ''',
                          (search_string,))
        length = res.fetchone()[0]

        res = cur.execute('''SELECT ID FROM Cards
                          WHERE LOWER(Name) LIKE %s
                          ORDER BY Name, ReleasedAt DESC
                          LIMIT %s OFFSET %s
                          ''',
                          (search_string, PAGE_SIZE, page * PAGE_SIZE))

    card_results = res.fetchall()

    for card in card_results:
        cards.append({'scryfall_id': str(card[0])})

    return json.dumps({'cards': cards, 'length': length})


@app.route("/api/all_cards/many", methods=["POST"])
def api_all_card_many():
    con = get_database_connection()
    cur = con.cursor()

    request_json = request.json

    content_type = request.headers.get('Content-Type')
    if (content_type != 'application/json'):
        error = {'successful': False, 'error': f"Expected Content-Type: application/json, found {content_type}"}
        return json.dumps(error)

    if request_json == None:
        error = {'successful': False, 'error': "Expected json body, but didn't find one"}
        return json.dumps(error)

    scryfall_ids = request_json.get('scryfall_ids')

    if scryfall_ids == None:
        error = {'successful': False, 'error': "Couldn't find expected key \"scryfall_ids\""}
        return json.dumps(error)

    if type(scryfall_ids) != list:
        error = {'successful': False, 'error': f"Expected key \"scryfall_ids\" to be of type list, got {str(type(scryfall_ids).__name__)}"}
        return json.dumps(error)


    cards = []
    for scryfall_id in scryfall_ids:
        # The ORDER BY is a quick and dirty way to make sure that we get the front image first.
        # This works because the URI follows the format
        # https://cards.scryfall.io/normal/<front or back>/...
        # So we just sort it so front is first
        # TODO: Make this less jank (might require adding which face is which when converting the JSON)
        res = cur.execute('''
                           SELECT Cards.Name, Finishes.Finish, Cards.CollectorNumber, Sets.Code, Cards.NormalImageURI, Faces.NormalImageURI FROM Cards
                           INNER JOIN FinishCards ON FinishCards.CardID = Cards.ID
                           INNER JOIN Finishes ON FinishCards.FinishID = Finishes.ID
                           LEFT  JOIN Faces ON Faces.CardID = Cards.ID
                           INNER JOIN Sets ON Sets.ID = Cards.SetID
                           WHERE Cards.ID = %s
                           ORDER BY Faces.NormalImageURI DESC
                          ''', (scryfall_id,))

        rows = res.fetchall()
        if len(rows) == 0:
            error = {'successful': False, 'error': f"Couldn't find card with ID \"{scryfall_id}\""}
            return json.dumps(error)

        # We use set() to dedupe because order doesn't matter
        finishes = list(set(row[1] for row in rows))

        cards_image_uri = rows[0][4]

        # We don't use set() because order _does_ matter
        faces_image_uris = []
        for row in [row[5] for row in rows]:
            if row not in faces_image_uris:
                faces_image_uris.append(row)

        if cards_image_uri != None:
            image_uris = [cards_image_uri]
        elif faces_image_uris != [None]:
            image_uris = faces_image_uris
        # This happens for cards that don't have an image in scryfall
        else:
            image_uris = None

        # Everything but the finish should be the same for all cards so we just pull out the first one
        card = rows[0]

        name = card[0]
        collector_number = card[2]
        set_code = card[3]

        card = {
            'name': name,
            'finishes': finishes,
            'collector_number': collector_number,
            'set': set_code,
            # TODO: We should just return faces (even for cards without multiple faces)
            'image_uris': image_uris
        }
        cards.append(card)

    return_obj = {
        'data': cards
    }

    return json.dumps(return_obj)


@app.route("/api/all_cards")
def api_all_cards():
    args = request.args
    page = args.get('page')
    query = args.get('query')
    default = args.get('default')

    if page:
        page = int(page)
    else:
        page = 0

    if default:
        default = default == 'true'
    else:
        default = False

    if query:
        if query == 'search':
            # TODO: Check this exists and is valid
            search_text = args.get('text')
            return api_all_cards_search(search_text, page, default)
        else:
            # Return an error
            pass
    else:
        return api_all_cards_search('', page, default)

def get_other_language_id(scryfall_id: str, lang: str) -> tuple[str, None] | tuple[None, dict]:
    res = cur.execute('''SELECT SetID, CollectorNumber FROM Cards
                      WHERE ID = %s''', (scryfall_id,))


    set_id_collector_number = res.fetchone()
    if set_id_collector_number == None:
        error = {'successful': False, 'error': "Couldn't find card with ID \"{scryfall_id}\""}
        return None, error

    set_id, collector_number = set_id_collector_number

    res = cur.execute('''SELECT ID FROM Langs
                      WHERE Lang = %s
                      ''', (lang,))

    lang_id = res.fetchone()
    if lang_id == None:
        error = {'successful': False, 'error': f"Couldn't find lang \"{lang}\""}
        return None, error

    lang_id = lang_id[0]

    res = cur.execute('''SELECT ID FROM Cards
                      WHERE
                        SetID = %s AND
                        CollectorNumber = %s AND
                        LangID = %s
                      ''', (set_id, collector_number, lang_id))

    scryfall_id = res.fetchone()

    if scryfall_id == None:
        # TODO: Improve this error message
        error = {'successful': False, 'error': f"Couldn't find card that card in that language"}
        return None, error

    scryfall_id = str(scryfall_id[0])

    return scryfall_id, None


def get_finish_card_id(finish: str, scryfall_id: str) -> tuple[None, int] | tuple[dict, None]:
    error = None
    res = cur.execute('''SELECT ID FROM Finishes
                         WHERE Finish = %s
                      ''', (finish,))
    finish_id = res.fetchone()

    if finish_id == None:
        error = {'successful': False, 'error': f"No such finish {finish}"}
        return (error, None)

    finish_id = finish_id[0]

    res = cur.execute('''SELECT ID FROM FinishCards
                      WHERE CardID = %s AND FinishID = %s
                      ''', (scryfall_id, finish_id))

    finish_card_id = res.fetchone()

    if finish_card_id == None:
        error = {'successful': False, 'error': f"That card doesn't come in the finish \"{finish}\""}
        return (error, None)
    finish_card_id = finish_card_id[0]

    return error, finish_card_id

@app.route("/api/collection/by_id", methods = ['GET'])
def api_collection_by_id():
    con = get_database_connection()
    cur = con.cursor()

    user_id, error = get_user_id(cur)
    if error:
        return json.dumps(error)

    args = request.args
    collection_id = args.get('collection_id')
    if collection_id == None:
        error = {'successful': False, 'error': "Didn't find expected query parameter \"collection_id\""}
        return json.dumps(error)

    cur.execute('''SELECT
                     Finishes.Finish,
                     Colls.Condition,
                     Colls.Signed,
                     Colls.Altered,
                     Colls.Notes,
                     Colls.Quantity
                   FROM Collections as Colls
                   INNER JOIN FinishCards ON Colls.FinishCardID = FinishCards.ID
                   INNER JOIN Finishes ON Finishes.ID = FinishCards.FinishID
                WHERE
                  Colls.ID = %s AND
                  Colls.UserID = %s
                ''', (collection_id, user_id))
    res = cur.fetchone()

    if res == None:
        error = {'successful': False, 'error': "Couldn't find card in your collection with that ID, data might be old. Try refreshing"}
        return json.dumps(error)

    finish, condition, signed, altered, notes, quantity = res
    card = {
        'finish': finish,
        'condition': condition,
        'signed': signed,
        'altered': altered,
        'notes': notes,
        'quantity': quantity
    }

    return_obj = {'successful': True, 'card': card}
    return json.dumps(return_obj)

@app.route("/api/collection", methods = ['POST', 'GET', 'PATCH'])
def api_collection():
    if request.method == 'GET':
        args = request.args
        page = args.get('page')
        query = args.get('query')

        if page:
            page = int(page)
        else:
            page = 0

        if query:
            if query == 'search':
                # TODO: Check this exists and is valid
                search_text = args.get('text')
                return api_collection_search(search_text, page)
            else:
                error = {'successful': False, 'error': f'Unsupported value for query parameter "query". Expected "search". Got {query}'}
                return json.dumps(error)
        else:
            return api_collection_search('', page)

    # This is where we add cards to the database
    # We need to do as much error checking as possible here
    # to ensure we don't accidently mess up the database
    # or say we're adding a card when in reality we aren't
    elif request.method == 'POST':
        con = get_database_connection()
        cur = con.cursor()

        user_id, error = get_user_id(cur)
        if error:
            return json.dumps(error)

        content_type = request.headers.get('Content-Type')
        if (content_type == 'application/json'):
            request_json = request.json
            if request_json == None or request_json == "":
                error = {'successful': False, 'error': f"Expected content, got empty POST body"}
                return json.dumps(error)

            scryfall_id = request_json.get('scryfall_id')
            quantity = request_json.get('quantity')
            finish = request_json.get('finish')
            condition = request_json.get('condition')
            signed = request_json.get('signed')
            altered = request_json.get('altered')
            notes = request_json.get('notes')

            param_type_map = {
                'scryfall_id': str,
                'quantity': int,
                'finish': str,
                'condition': str,
                'signed': bool,
                'altered': bool,
                'notes': str
            }

            for param_name, param_type in param_type_map.items():
                param_value = request_json.get(param_name)
                if param_value == None:
                    error = {'successful': False, 'error': f'Expected key "{param_name}" not found in POST body.'}
                    return json.dumps(error)

                if type(param_value) != param_type:
                    error = {'successful': False, 'error': f'Expected key "{param_name}" to be a of type {param_type}, got {str(type(param_value).__name__)}'}
                    return json.dumps(error)

            # TODO: Check for unexpected keys

            res = cur.execute("""SELECT Cards.Name, Cards.CollectorNumber, Sets.Code FROM Cards
                              INNER JOIN Sets ON Cards.SetID = Sets.ID
                              WHERE Cards.ID = %s""", (scryfall_id,))
            row = res.fetchone()

            if row == None:
                error = {'successful': False, 'error': f'Couldn\'t find a card with that id "{scryfall_id}"'}
                return json.dumps(error)

            return_card = {
                    'name': row[0],
                    'collector_number': row[1],
                    'set_abbr': row[2]
                    }


            error, finish_card_id = get_finish_card_id(finish, scryfall_id)
            if error != None:
                return json.dumps(error)

            res = cur.execute('''SELECT Quantity FROM Collections
                              WHERE UserID = %s AND
                              FinishCardID = %s AND
                              Condition = %s AND
                              Signed = %s AND
                              Altered = %s AND
                              Notes = %s
                              ''', (user_id, finish_card_id, condition, signed, altered, notes))
            original_quantity = res.fetchone()
            card_in_collection = original_quantity != None

            if card_in_collection:
                original_quantity = original_quantity[0]
                res = cur.execute('''UPDATE collections SET Quantity = quantity + %s
                            WHERE UserID = %s AND
                            FinishCardID = %s AND
                            Condition = %s AND
                            Signed = %s AND
                            Altered = %s AND
                            Notes = %s
                            RETURNING Quantity
                            ''', (quantity, user_id, finish_card_id, condition, signed, altered, notes))
                updated_quantity = res.fetchone()[0]
            else:
                original_quantity = 0
                res = cur.execute('''INSERT INTO Collections(UserID, FinishCardID, Condition, Signed, Altered, Notes, Quantity)
                            VALUES(%s, %s, %s, %s, %s, %s, %s)
                            RETURNING Quantity
                            ''', (user_id, finish_card_id, condition, signed, altered, notes, quantity))
                updated_quantity = res.fetchone()[0]

            # If we get a request to have 0 or negative updated_quantity we delete the row
            # This can happen if the user clicks the - button
            # while having 0 in the collection
            if updated_quantity <= 0:
                cur.execute('''DELETE FROM collections
                        WHERE UserID = %s AND
                        FinishCardID = %s AND
                        Condition = %s AND
                        Signed = %s AND
                        Altered = %s AND
                        Notes = %s
                        ''', (user_id, finish_card_id, condition, signed, altered, notes))
                updated_quantity = 0

            delta = updated_quantity - original_quantity

            return_obj = {'successful': True, 'card': return_card, 'delta': delta, 'new_total': updated_quantity}
            con.commit()
            return json.dumps(return_obj)
        else:
            error = {'successful': False, 'error': f"Expected Content-Type: application/json, found {content_type}"}
            return json.dumps(error)
    elif request.method == "PATCH":
        con = get_database_connection()
        cur = con.cursor()


        user_id, error = get_user_id(cur)
        if error != None:
            return json.dumps(error)

        request_json = request.json
        if request_json == None or request_json == "":
                error = {'successful': False, 'error': f"Expected content, got empty PATCH body"}
                return json.dumps(error)

        target_card_id = request_json.get('target')
        replacement_card = request_json.get('replacement')
        if target_card_id == None:
            error = {'successful': False, 'error': f"Didn't find expected key 'target' in PATCH body"}
            return json.dumps(error)
        if replacement_card == None:
            error = {'successful': False, 'error': f"Didn't find expected key 'replacement' in PATCH body"}
            return json.dumps(error)

        # TODO: Type check target and replacement
        # TODO: Make sure to handle quantity

        res = cur.execute('''SELECT
                                Colls.FinishCardID,
                                FinishCards.CardID,
                                Colls.Quantity,
                                Colls.Condition,
                                Colls.Signed,
                                Colls.Altered,
                                Colls.Notes,
                                Langs.Lang,
                                Cards.Name,
                                Cards.NormalImageURI FROM Collections as Colls
                          INNER JOIN FinishCards ON Colls.FinishCardID = FinishCards.ID
                          INNER JOIN Cards ON FinishCards.CardID = Cards.ID
                          INNER JOIN Langs ON Cards.LangID = Langs.ID
                          WHERE
                            Colls.ID = %s AND
                            Colls.UserID = %s
                          ''', (target_card_id, user_id))
        defaults = res.fetchone()
        if defaults == None:
            error = {'successful': False, 'error': f"Couldn't find target card in database"}
            return json.dumps(error)

        default_finish_card_id, default_scryfall_id, default_quantity, default_condition, default_signed, default_altered, default_notes, default_lang, card_name, normal_image_uri = defaults

        replacement_lang = replacement_card.get('language', default_lang)
        # Changing languages means we need to change scryfall_id as well
        scryfall_id, error = get_other_language_id(default_scryfall_id, replacement_lang)
        if scryfall_id == None:
            return json.dumps(error)

        print(default_lang, default_scryfall_id, replacement_lang, scryfall_id)

        replacement_finish = replacement_card.get('finish', default_finish_card_id)
        error, replacement_finish_card_id = get_finish_card_id(replacement_finish, scryfall_id)
        if error != None:
            return json.dumps(error)

        replacement_quantity = replacement_card.get('quantity', default_quantity)
        replacement_condition = replacement_card.get('condition', default_condition)
        replacement_signed = replacement_card.get('signed', default_signed)
        replacement_altered = replacement_card.get('altered', default_altered)
        replacement_notes = replacement_card.get('notes', default_notes)

        try:
            res = cur.execute(f'''UPDATE Collections
                        SET
                          FinishCardID = %s,
                          Quantity = %s,
                          Condition = %s,
                          Signed = %s,
                          Altered = %s,
                          Notes = %s
                        WHERE
                          ID = %s AND
                          UserID = %s
                        ''', (replacement_finish_card_id, replacement_quantity, replacement_condition, replacement_signed, replacement_altered, replacement_notes) + (target_card_id, user_id))
        except psycopg.errors.UniqueViolation:
            # TODO: This message is really long, but doesn't stay up for very long
            # consider extending how long messages stay up (or make it configurable or based on length)
            error = {'successful': False, 'error': "Updating that card in that way would cause it to be identical to another card in your collection, because it's unclear what to do in that case we err on the side of caution and do nothing. To accomplish this try removing all copies of the original card from your collection and then adding any number you need to the existing entry."}
            return json.dumps(error)

        con.commit()
        new_card = {
            'scryfall_id': scryfall_id,
            'finish': replacement_finish,
            'quantity': replacement_quantity,
            'condition': replacement_condition,
            'signed': replacement_signed,
            'altered': replacement_altered,
            'notes': replacement_notes,
            'name': card_name,
            'language': replacement_lang,
            'image_src': normal_image_uri
        }
        return_obj = {'successful': True, 'replaced_card_id': target_card_id, 'new_card': new_card}
        return json.dumps(return_obj)

@app.route("/collection")
@login_required
def collection():
    with open('./html/collection.html', 'r') as collection_html:
        return render_template_string(collection_html.read())

@app.route("/collection/add")
@login_required
def collection_add():
    with open('./html/collection_add.html', 'r') as collection_add_html:
        return render_template_string(collection_add_html.read())

@app.route("/generate_token", methods=["GET", "POST"])
@login_required
def generate_token():
    if request.method == "GET":
        with open('./html/generate_token.html', 'r') as generate_token_html:
            return render_template_string(generate_token_html.read())
    elif request.method == "POST":
        con = get_database_connection()
        cur = con.cursor()
        hasher = hashlib.new(HASH_FUNCTION)

        content_type = request.headers.get('Content-Type')
        if (content_type != 'application/json'):
            error = {'successful': False, 'error': f"Expected Content-Type: application/json, found {content_type}"}
            return json.dumps(error)

        request_json = request.json
        if request_json == None:
            error = {'successful': False, 'error': "Expected json body, but didn't find one"}
            return json.dumps(error)

        valid_until = request_json.get('valid_until')
        user_id, error = get_user_id(cur)
        if error:
            return json.dumps(error)

        token_bytes = secrets.token_bytes(64)
        token_hex = token_bytes.hex()
        hasher.update(token_bytes)
        hashed_token_bytes = hasher.digest()

        cur.execute('''INSERT INTO APITokens(UserID, TokenHash, ValidUntil)
                    VALUES(%s, %s, %s)
                    ''', (user_id, hashed_token_bytes, valid_until))

        con.commit()
        return json.dumps({'successful': True, 'token': token_hex, 'valid-until': valid_until})

@app.route("/deckbuilder")
@login_required
def deckbuilder():
    return render_template_string('''
<style>
  .column {
    position: relative;
    top: 0;
    left: 0px;
  }
  .card-image {
    width: 150px;
    height: auto;
    position: absolute;
    border-radius: 10px;
  }
</style>
<script>
</script>
<div class=column>
{% for i in range(10000) %}
<img class="card-image" src=https://c1.scryfall.com/file/scryfall-cards/normal/front/b/4/b4ea262c-ea32-4aca-b96b-58f556a8dffc.jpg loading="lazy" style="top: {{ 20 * i }}px"></img>
{% endfor %}
</div>''')

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template_string('''
              {% with messages = get_flashed_messages() %}
              <form method="POST">
              <label for="username">Username:</label>
              <input type="text" name="username" id="username"></input>
              <label for="password">Password:</label>
              <input type="text" name= "password" id="password"></input>
              <input type="submit" value="Submit"></input>
              {% if messages %}
                <ul class=flashes>
                {% for message in messages %}
                  <li>{{ message }}</li>
                {% endfor %}
                </ul>
              {% endif %}
              {% endwith %}''')
    elif request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = users[username]
        if password == user.password:
            user.is_authenticated = True
            login_user(user)

            next = request.args.get('next')
            if not is_safe_url(next):
                return abort(400)

            return redirect(next or url_for('index'))
        else:
            user.is_authenticated = False
            flash("Incorrect username or password")
            return redirect(request.url)
