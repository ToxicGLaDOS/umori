var card_width = 150;
var cur_page = 0;
const PAGE_SIZE = 25;

async function add_page(scryfall_ids, abort_signal = new AbortController().signal) {
    // Convert ids to format scryfall wants
    post_body = {
        "identifiers": []
    }
    for (var id of scryfall_ids) {
        post_body.identifiers.push({
            "id": id
        })
    }

    // Call scryfall api for all cards in the page at once
    await fetch(`https://api.scryfall.com/cards/collection`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(post_body)
    })
        .then(response => response.json())
        .then(cards_response => {
            // TODO: Check the "not_found" member of cards_response
            // to ensure we got everything
            // TODO: Test what happens if you get only one result
            // the "object" member, might help there
            // Create all the card objects in the DOM
            for (var card of cards_response.data) {
                var grid = document.getElementById("collection-grid");
                var image = document.createElement("img");
                if (card.image_uris) {
                    image.src = card.image_uris.normal;
                    image.loading = "lazy";
                    image.className = "card-image";
                    // This prevents more stuff from being added
                    // after the search box is updated
                    if (abort_signal.aborted) {
                        break;
                    }
                    grid.appendChild(image);
                }
                else {
                    console.log("Couldn't find image_uris image for card:");
                    console.log(card);
                }
            }
        });
}

async function load_page(page_num) {
    scryfall_ids = await fetch(`/api/collection?page=${page_num}`).then(response => response.json());
    var grid = document.getElementById("collection-grid");
    while (grid.lastChild) {
        grid.removeChild(grid.lastChild);
    }
    add_page(scryfall_ids);
}

async function get_search(search_text, page_num) {
    var scryfall_ids_json = await fetch(`/api/collection?query=search&text=${search_text}&page=${page_num}`).then(response => response.json());
    var scryfall_ids = scryfall_ids_json.scryfall_ids;
    return scryfall_ids;
}

async function main() {
    const urlParams = new URLSearchParams(location.search);
    if (urlParams.has('page')) {
        cur_page = Number(urlParams.get('page'));
        load_page(urlParams.get('page'));
    }
    else {
        load_page(0);
    }
    var collection_length_response = await fetch(`/api/collection?query=length`).then(response => response.json());
    var collection_length = collection_length_response.length;
    var page_nav = document.getElementById("page-nav");
    // TODO: Don't show pages past the last page
    for (var i = 0; i < 3; i++){
        var new_link = document.createElement("a");
        new_link.href = `?page=${cur_page + i}`;
        new_link.innerHTML = `${cur_page + i}`
        new_link.className = "page-nav-link"
        page_nav.appendChild(new_link);
    }

    var last_link = document.createElement("a");
    last_link.href = `?page=${Math.floor(collection_length / PAGE_SIZE)}`;
    last_link.innerHTML = `${Math.floor(collection_length / PAGE_SIZE)}`
    last_link.className = "page-nav-link"
    page_nav.appendChild(last_link);

    var abort_controller = new AbortController();

    document.getElementById("collection-search").addEventListener('input', (e) => {
        // abort the old controller then create a new one
        abort_controller.abort();
        abort_controller = new AbortController();
        var search_text = e.currentTarget.value;
        get_search(search_text, 0)
            .then(scryfall_ids => {
                var grid = document.getElementById("collection-grid");
                while (grid.lastChild) {
                    grid.removeChild(grid.lastChild);
                }
                add_page(scryfall_ids, abort_controller.signal);
            });
    })
}


document.addEventListener("DOMContentLoaded", main)

