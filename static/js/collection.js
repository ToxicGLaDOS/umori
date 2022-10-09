var card_width = 150;
var cur_page = 0;
const PAGE_SIZE = 25;
// How many pages forward and back for the page nav show
const PAGE_NAV_SPAN = 3;

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
                }
                else if (card.card_faces) {
                    image.src = card.card_faces[0].image_uris.normal;
                }
                else {
                    console.log("Couldn't find image_uris image for card:");
                    console.log(card);
                }
                image.loading = "lazy";
                image.className = "card-image";
                // This prevents more stuff from being added
                // after the search box is updated
                if (abort_signal.aborted) {
                    console.log("Aborted")
                    break;
                }
                console.log("Adding card")
                grid.appendChild(image);
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

async function create_page_nav() {
    var collection_length_response = await fetch(`/api/collection?query=length`).then(response => response.json());
    var collection_length = collection_length_response.length;
    var num_pages = Math.floor(collection_length / PAGE_SIZE);
    var page_nav = document.getElementById("page-nav");

    if (cur_page > PAGE_NAV_SPAN) {
        var last_link = document.createElement("a");
        last_link.href = `?page=0`;
        last_link.innerHTML = "0";
        last_link.className = "page-nav-link";
        page_nav.appendChild(last_link);

        var elipses = document.createElement("div");
        elipses.innerHTML = "..."
        elipses.style.display = "inline"
        page_nav.appendChild(elipses)
    }

    // Create the nav links for pages less than cur_page
    for (var i = Math.min(PAGE_NAV_SPAN, cur_page); i > 0; i--) {
        var new_link = document.createElement("a");
        new_link.href = `?page=${cur_page - i}`;
        new_link.innerHTML = `${cur_page - i}`
        new_link.className = "page-nav-link"
        page_nav.appendChild(new_link);
    }


    var cur_page_link = document.createElement("a");
    cur_page_link.innerHTML = cur_page;
    cur_page_link.className = "page-nav-link";
    page_nav.appendChild(cur_page_link);

    // Create the nav links for pages more than cur_page
    for (var i = 1; i < Math.min(PAGE_NAV_SPAN, num_pages - cur_page) + 1; i++){
        var new_link = document.createElement("a");
        new_link.href = `?page=${cur_page + i}`;
        new_link.innerHTML = `${cur_page + i}`;
        new_link.className = "page-nav-link";
        page_nav.appendChild(new_link);
    }

    if (num_pages - cur_page > PAGE_NAV_SPAN) {
        var elipses = document.createElement("div");
        elipses.innerHTML = "...";
        elipses.style.display = "inline";
        page_nav.appendChild(elipses)

        var last_link = document.createElement("a");
        last_link.href = `?page=${num_pages}`;
        last_link.innerHTML = `${num_pages}`
        last_link.className = "page-nav-link"
        page_nav.appendChild(last_link);
    }
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

    create_page_nav();

    var abort_controller = new AbortController();

    document.getElementById("collection-search").addEventListener('input', (e) => {
        // This whole event listener is a race condition waiting to happen
        // I think I've fixed it, but it's pretty hard to prove.
        var search_text = e.currentTarget.value;
        var grid = document.getElementById("collection-grid");
        get_search(search_text, 0)
            .then(scryfall_ids => {
                abort_controller.abort();
                abort_controller = new AbortController();
                while (grid.lastChild) {
                    grid.removeChild(grid.lastChild);
                }
                add_page(scryfall_ids, abort_controller.signal);
            });
    })
}


document.addEventListener("DOMContentLoaded", main)

