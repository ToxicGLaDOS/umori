from flask import Flask, request, url_for, redirect, abort, render_template_string, flash
from urllib.parse import urlparse, urljoin
from flask_login import LoginManager, login_required, login_user, logout_user
import json, sqlite3, psycopg
import hashlib, binascii
import flask_login
import secrets
import config, init_database
from datetime import datetime
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

login_manager = LoginManager()

app = Flask(__name__)
login_manager.init_app(app)

HASH_FUNCTION = 'SHA3-512'
app.config['SECRET_KEY'] = config.get('SECRET_KEY')

def get_database_connection():
    con = psycopg.connect(user = config.get('DB_USER'), password = config.get('DB_PASSWORD'), host = config.get('DB_HOST'), port = config.get('DB_PORT'))
    return con

ph = PasswordHasher()
password_hash = ph.hash('foo')

init_database.create_tables()

with get_database_connection() as con:
    cur = con.cursor()
    rows = cur.execute("SELECT COUNT(*) FROM Cards")
    row = rows.fetchone()
    if row != None and row[0] == 0:
        init_database.import_from_scryfall()


class User:
    def __init__(self, id, username):
        self.id = id
        self.username = username
        self.is_authenticated = True
        self.is_active = True
        self.is_anonymous = False

    def get_id(self):
        return self.id

# Matches the function name that you want to go to
login_manager.login_view = "login"

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
    with get_database_connection() as con:
        cur = con.cursor()

        res = cur.execute('''SELECT Username FROM Users
                          WHERE ID = %s
                          ''', (user_id,))

        row = res.fetchone()
        if row == None:
            return None

        username = row[0]

        user = User(user_id, username)
        return user

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
        user_id = flask_login.current_user.get_id()
        if user_id == None:
            error = {'successful': False, 'error': f"No Authorization header or session"}
            return None, error

    return user_id, None

def get_user_id_by_username(username: str, cur: psycopg.Cursor):
    res = cur.execute('''SELECT ID FROM Users
                      WHERE Username = %s''', (username, ))

    row = res.fetchone()
    if row == None:
        raise NotFoundException(f"Couldn't find user with username {username}")

    return row[0]

class NotFoundException(Exception):
    pass

class Card:
    def __init__(self, cur: psycopg.Cursor, scryfall_id: str):
        self.scryfall_id = scryfall_id
        # The ORDER BY is a quick and dirty way to make sure that we get the front image first.
        # This works because the URI follows the format
        # https://cards.scryfall.io/normal/<front or back>/...
        # So we just sort it so front is first
        # TODO: Make this less jank (might require adding which face is which when converting the JSON)
        res = cur.execute('''
                      SELECT Cards.Name, Finishes.Finish, Cards.CollectorNumber, Sets.Code, Cards.NormalImageURI, Faces.NormalImageURI, Langs.Lang FROM Cards
                      INNER JOIN FinishCards ON FinishCards.CardID = Cards.ID
                      INNER JOIN Finishes ON FinishCards.FinishID = Finishes.ID
                      LEFT  JOIN Faces ON Faces.CardID = Cards.ID
                      INNER JOIN Sets ON Sets.ID = Cards.SetID
                      INNER JOIN Langs ON Langs.ID = Cards.LangID
                      WHERE Cards.ID = %s
                      ORDER BY Faces.NormalImageURI DESC
                      ''', (scryfall_id,))

        rows = res.fetchall()
        if len(rows) == 0:
            raise NotFoundException("Couldn't find card with ID \"{scryfall_id}\"")

        # We use set() to dedupe because order doesn't matter
        self.finishes = list(set(row[1] for row in rows))

        cards_image_uri = rows[0][4]

        # We don't use set() because order _does_ matter
        faces_image_uris = []
        for row in [row[5] for row in rows]:
            if row not in faces_image_uris:
                faces_image_uris.append(row)

        self.image_uris = None
        if cards_image_uri != None:
            self.image_uris = [cards_image_uri]
        elif faces_image_uris != [None]:
            self.image_uris = faces_image_uris

        # Everything but the finish should be the same for all cards
        # so we just pull out the first one
        card = rows[0]

        self.name = card[0]
        self.collector_number = card[2]
        self.set_code = card[3]
        self.lang = card[6]

        # Type declarations
        self.scryfall_id: str
        self.name: str
        self.finishes: list
        self.collector_number: str
        self.set_code: str
        self.lang: str
        self.image_uris: list | None

    def get_dict(self):
        return_card = {
            'name': self.name,
            'finishes': self.finishes,
            'collector_number': self.collector_number,
            'set': self.set_code,
            'image_uris': self.image_uris,
            'lang': self.lang
        }
        return return_card

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

    # If valid_until is None then the token never expires
    if valid_until != None and valid_until < datetime.now().astimezone():
        error = {'successful': False, 'error': 'That token has expired'}
        return None, error

    return user_id, None

def api_collection_search(cur: psycopg.Cursor, search_text: str, page: int, user_id):
    cards = []

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

    return json.dumps({'successful': True, 'cards': cards, 'length': length})

@app.route("/api/all_cards/languages")
def api_all_cards_languages():
    with get_database_connection() as con:
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
    with get_database_connection() as con:
        cur = con.cursor()

        args = request.args
        scryfall_id = args.get('scryfall_id')

        if scryfall_id == None:
            error = {'successful': False, 'error': 'Expected query param "scryfall_id"'}
            return json.dumps(error)
        try:
            card = Card(cur, scryfall_id)
        except NotFoundException as e:
            return json.dumps({'successful': False, 'error': str(e)})

        return json.dumps(card.get_dict())


def api_all_cards_search(search_text: str, page: int, default: bool):
    with get_database_connection() as con:
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
    with get_database_connection() as con:
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
            try:
                card = Card(cur, scryfall_id)
            except NotFoundException as e:
                return json.dumps({'successful': False, 'error': str(e)})

            cards.append(card.get_dict())

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

def get_other_language_id(cur: psycopg.Cursor, scryfall_id: str, lang: str) -> tuple[str, None] | tuple[None, dict]:
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


def get_finish_card_id(cur: psycopg.Cursor, finish: str, scryfall_id: str) -> tuple[None, int] | tuple[dict, None]:
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
    with get_database_connection() as con:
        cur = con.cursor()

        authed_user_id, error = get_user_id(cur)
        if error:
            return json.dumps(error)

        args = request.args
        collection_id = args.get('collection_id')
        username = args.get('username')

        if username == None:
            error = {'successful': False, 'error': "Didn't find expected query parameter \"username\""}
            return json.dumps(error)
        if collection_id == None:
            error = {'successful': False, 'error': "Didn't find expected query parameter \"collection_id\""}
            return json.dumps(error)

        try:
            user_id = get_user_id_by_username(username, cur)
        except NotFoundException as e:
            return json.dumps({'successful': False, 'error': str(e)})

        if authed_user_id != user_id:
            error = {'successful': False, 'error': "You are not authorized to access this collection."}
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
                    ''', (collection_id, authed_user_id))
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
    with get_database_connection() as con:
        cur = con.cursor()

        if request.method == 'GET':
            args = request.args
            page = args.get('page')
            query = args.get('query')

            username = args.get('username')
            authed_user_id, error = get_user_id(cur)
            if error:
                return json.dumps(error)

            if username == None:
                error = {'successful': False, 'error': "Didn't find expected query parameter \"username\""}
                return json.dumps(error)

            try:
                user_id = get_user_id_by_username(username, cur)
            except NotFoundException as e:
                return json.dumps({'successful': False, 'error': str(e)})

            if authed_user_id != user_id:
                error = {'successful': False, 'error': "You are not authorized to access this collection."}
                return json.dumps(error)

            if page:
                page = int(page)
            else:
                page = 0

            if query:
                if query == 'search':
                    # TODO: Check this exists and is valid
                    search_text = args.get('text')
                    return api_collection_search(cur, search_text, page, user_id)
                else:
                    error = {'successful': False, 'error': f'Unsupported value for query parameter "query". Expected "search". Got {query}'}
                    return json.dumps(error)
            else:
                return api_collection_search(cur, '', page, user_id)

        # This is where we add cards to the database
        # We need to do as much error checking as possible here
        # to ensure we don't accidently mess up the database
        # or say we're adding a card when in reality we aren't
        elif request.method == 'POST':
            authed_user_id, error = get_user_id(cur)
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
                username = request_json.get('username')
                if username == None:
                    error = {'successful': False, 'error': "Didn't find expected key \"username\""}
                    return json.dumps(error)

                user_id = get_user_id_by_username(username, cur)
                if authed_user_id != user_id:
                    error = {'successful': False, 'error': "You are not authorized to access this collection."}
                    return json.dumps(error)

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


                error, finish_card_id = get_finish_card_id(cur, finish, scryfall_id)
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
            authed_user_id, error = get_user_id(cur)
            if error != None:
                return json.dumps(error)

            request_json = request.json
            if request_json == None or request_json == "":
                    error = {'successful': False, 'error': f"Expected content, got empty PATCH body"}
                    return json.dumps(error)

            username = request_json.get('username')
            if username == None:
                error = {'successful': False, 'error': "Didn't find expected key \"username\""}
                return json.dumps(error)

            user_id = get_user_id_by_username(username, cur)
            if authed_user_id != user_id:
                error = {'successful': False, 'error': "You are not authorized to access this collection."}
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
            scryfall_id, error = get_other_language_id(cur, default_scryfall_id, replacement_lang)
            if scryfall_id == None:
                return json.dumps(error)

            print(default_lang, default_scryfall_id, replacement_lang, scryfall_id)

            replacement_finish = replacement_card.get('finish', default_finish_card_id)
            error, replacement_finish_card_id = get_finish_card_id(cur, replacement_finish, scryfall_id)
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

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        with open('./html/signup.html', 'r') as signup_html:
            return render_template_string(signup_html.read())
    elif request.method == "POST":
        with get_database_connection() as con:
            cur = con.cursor()

            username = request.form.get('username')
            password = request.form.get('password')
            print(username, password)

            if username == None or username == "":
                flash("Must enter a username")
                return redirect(request.url)

            if password == None or password == "":
                flash("Must enter a password")
                return redirect(request.url)

            password_hash = ph.hash(password)
            try:
                res = cur.execute('''INSERT INTO Users(Username, PasswordHash)
                                  VALUES(%s, %s)
                                  RETURNING ID
                                  ''', (username, password_hash))
            except psycopg.errors.UniqueViolation:
                flash("That username is already taken")
                return redirect(request.url)

            user_id = res.fetchone()[0]
            con.commit()

            user = User(user_id, username)
            user.is_authenticated = True
            login_user(user)
            return redirect(f'{username}/collection')
    else:
        return f"Unhandled REST method {request.method}"

@app.route("/<username>/collection")
@login_required
def collection(username):
    with open('./html/collection.html', 'r') as collection_html:
        return render_template_string(collection_html.read(), username=username)

@app.route("/<username>/collection/add")
@login_required
def collection_add(username):
    with open('./html/collection_add.html', 'r') as collection_add_html:
        return render_template_string(collection_add_html.read(), username=username)

@app.route("/generate_token", methods=["GET", "POST"])
@login_required
def generate_token():
    if request.method == "GET":
        with open('./html/generate_token.html', 'r') as generate_token_html:
            return render_template_string(generate_token_html.read())
    elif request.method == "POST":
        with get_database_connection() as con:
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
    else:
        return f"Unhandled REST method {request.method}"

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
    next = request.args.get('next')
    if not is_safe_url(next):
        return abort(400)

    return redirect(next or url_for('index'))

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        with open('./html/login.html', 'r') as login:
            return render_template_string(login.read())

    elif request.method == 'POST':
        with get_database_connection() as con:
            cur = con.cursor()

            username = request.form.get('username')
            password = request.form.get('password')
            if username == None or username == "":
                flash("Must enter a username")
                return redirect(request.url)

            if password == None or password == "":
                flash("Must enter a password")
                return redirect(request.url)


            res = cur.execute('''SELECT ID, PasswordHash FROM Users
                              WHERE Username = %s
                              ''', (username, ))

            row = res.fetchone()
            if row == None:
                flash("No user with that username exists")
                return redirect(request.url)


            id, password_hash = row
            try:
                ph.verify(password_hash, password)
            except VerifyMismatchError:
                flash("Incorrect password")
                return redirect(request.url)

            if ph.check_needs_rehash(password_hash):
                cur.execute('''UPDATE Users
                            SET PasswordHash = %s
                            WHERE ID = %s
                            ''', (ph.hash(password), id))
                con.commit()

            user = User(id, username)
            user.is_authenticated = True
            login_user(user)

            next = request.args.get('next')
            if not is_safe_url(next):
                return abort(400)

            return redirect(next or url_for('index'))
