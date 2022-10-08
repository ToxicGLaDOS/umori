from flask import Flask, request, url_for, redirect, abort, render_template_string, flash
from urllib.parse import urlparse, urljoin
from flask_login import LoginManager, login_required, login_user, logout_user
import json, csv

login_manager = LoginManager()

app = Flask(__name__)
login_manager.init_app(app)

app.config['SECRET_KEY'] = 'aed47c6a4cf84f7585ab2243a10c0e96'

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

def api_collection_pages(page: int):
    cards = []
    with open('output.csv', 'r') as f:
        cards_reader = csv.DictReader(f, delimiter='|')
        cards = list(cards_reader)
    if page == None:
        page = 0
    else:
        # TODO: Return error page if page isn't an int
        page = int(page)

    # TODO: Handle case where page is past the end
    start = PAGE_SIZE * page
    end = start + PAGE_SIZE
    ids = [card['Scryfall ID'] for card in cards]
    return json.dumps(ids[start:end])

def api_collection_length():
    print('length')
    with open('output.csv', 'r') as f:
        cards_reader = csv.reader(f, delimiter='|')
        return json.dumps({'length': len(list(cards_reader))})

def api_collection_search(search_text: str, page: int):
    ids = []
    with open('output.csv', 'r') as f:
        cards_reader = csv.DictReader(f, delimiter='|')
        for card in cards_reader:
            name = card['Name'].lower()
            if search_text.lower() in name:
                ids.append(card['Scryfall ID'])

    start = PAGE_SIZE * page
    end = start + PAGE_SIZE
    ids = ids[start:end]

    return json.dumps({'scryfall_ids': ids})

@app.route("/api/collection")
def api_collection():
    args = request.args
    page = args.get('page')
    query = args.get('query')

    if page:
        # TODO: Check page is actually an int
        page = int(page)
    else:
        page = 0

    if query:
        if query == 'length':
            return api_collection_length()
        elif query == 'search':
            # TODO: Check this exists and is valid
            search_text = args.get('text')
            return api_collection_search(search_text, page)
        else:
            # Return an error
            pass
    else:
        return api_collection_pages(page)

@app.route("/collection")
@login_required
def collection():
    with open('./html/collection.html', 'r') as collection_html:
        return render_template_string(collection_html.read())

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
              <input type="text" name="username" id="username"></input>
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
