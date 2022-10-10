var card_width = 150;
var cur_page = 0;
const PAGE_SIZE = 25;
// How many pages forward and back for the page nav show
const PAGE_NAV_SPAN = 3;

async function add_page(cards, abort_signal = new AbortController().signal) {
    // Convert ids to format scryfall wants
    post_body = {
        "identifiers": []
    }
    for (var card of cards) {
        post_body.identifiers.push({
            "id": card.scryfall_id
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

            for (var i = 0; i < cards.length; i++) {
                var collection_card = cards[i];
                var scryfall_card = cards_response.data[i];

                if (scryfall_card.image_uris) {
                    collection_card.image_src = scryfall_card.image_uris.normal;
                }
                else if (scryfall_card.card_faces) {
                    collection_card.image_src = scryfall_card.card_faces[0].image_uris.normal;
                }
                else {
                    console.log("Couldn't find image_uris image for card:");
                    console.log(scryfall_card);
                }

                collection_card.name = scryfall_card.name;
            }
            console.log(cards)


            // Create all the card objects in the DOM
            for (var card of cards) {

                var grid = document.getElementById("collection-grid");
                var card_div = document.createElement("div");
                card_div.className = 'card-div';
                var image = document.createElement("img");
                image.src = card.image_src;
                var quantity_text = document.createElement("div");
                quantity_text.innerHTML = `${card.name} (${card.quantity})`;
                quantity_text.className = 'card-quantity';

                image.loading = "lazy";
                image.className = "card-image";
                // This prevents more stuff from being added
                // after the search box is updated
                if (abort_signal.aborted) {
                    console.log("Aborted")
                    break;
                }
                card_div.appendChild(quantity_text);
                card_div.appendChild(image);
                grid.appendChild(card_div);

                while (quantity_text.getBoundingClientRect().width > image.getBoundingClientRect().width) {
                    var font_size = window.getComputedStyle(quantity_text).getPropertyValue("font-size");
                    quantity_text.style.fontSize = parseInt(font_size, 10) - 1;
                }
            }
        });
}

async function load_page(page_num, search_query) {
    if (search_query) {
        response = await fetch(`/api/collection?page=${page_num}&query=search&text=${search_query}`).then(response => response.json());
    }
    else {
        response = await fetch(`/api/collection?page=${page_num}`).then(response => response.json());
    }
    add_page(response.cards);
}

async function get_search(search_text, page_num) {
    var cards = await fetch(`/api/collection?query=search&text=${search_text}&page=${page_num}`).then(response => response.json());
    return cards;
}

async function create_page_nav(collection_length) {
    var num_pages = Math.floor(collection_length / PAGE_SIZE);
    var page_nav = document.getElementById("page-nav");

    // Delete all children of page_nav
    while (page_nav.lastChild) {
        page_nav.removeChild(page_nav.lastChild);
    }

    var url = new URL(location.href);

    if (cur_page > PAGE_NAV_SPAN) {
        var last_link = document.createElement("a");
        url.searchParams.set('page', 0);
        last_link.href = url.toString();
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
        url.searchParams.set('page', cur_page - i);
        new_link.href = url.toString();
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
        url.searchParams.set('page', cur_page + i);
        new_link.href = url.toString();
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
        url.searchParams.set('page', num_pages);
        last_link.href = url.toString();
        last_link.innerHTML = `${num_pages}`
        last_link.className = "page-nav-link"
        page_nav.appendChild(last_link);
    }
}

async function main() {
    const urlParams = new URLSearchParams(location.search);
    var search_query = '';
    if (urlParams.has('search')) {
        search_query = urlParams.get('search');
        document.getElementById("collection-search").value = search_query;
        var collection_length_response = await fetch(`/api/collection?query=length&search=${search_query}`).then(response => response.json());
    }
    else {
        var collection_length_response = await fetch(`/api/collection?query=length`).then(response => response.json());
    }
    if (urlParams.has('page')) {
        cur_page = Number(urlParams.get('page'));
        load_page(urlParams.get('page'), search_query);
    }
    else {
        load_page(0, search_query);
    }

    create_page_nav(collection_length_response.length);

    var abort_controller = new AbortController();

    document.getElementById("collection-search").addEventListener('input', (e) => {
        // This whole event listener is a race condition waiting to happen
        // I think I've fixed it, but it's pretty hard to prove.
        var search_text = e.currentTarget.value;
        var url = new URL(location.href);
        url.searchParams.delete('page');
        cur_page = 0;
        if (search_text != '') {
            url.searchParams.set('search', search_text);
        }
        else {
            url.searchParams.delete('search');
        }
        history.replaceState({}, 'Collection', url.href);

        fetch(`/api/collection?query=length&search=${search_text}`)
            .then(response => response.json())
            .then(collection_length_response => {
                create_page_nav(collection_length_response.length);

                var grid = document.getElementById("collection-grid");
                get_search(search_text, 0)
                    .then(response => {
                        abort_controller.abort();
                        abort_controller = new AbortController();
                        while (grid.lastChild) {
                            grid.removeChild(grid.lastChild);
                        }
                        add_page(response.cards, abort_controller.signal);
                    });
            });
    })
}


document.addEventListener("DOMContentLoaded", main)

