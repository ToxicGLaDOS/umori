var cur_page = 0;
const PAGE_SIZE = 25;
// How many pages forward and back for the page nav show
const PAGE_NAV_SPAN = 3;
var add_page_abort_controller = new AbortController();

// create_card is a function that returns a card which
// will be shown in the grid
async function add_page(cards_data, create_card) {
    // Abort the last call to add_page
    add_page_abort_controller.abort();
    // Make a new abort controller for this specific call to add_page
    var current_abort_controller = new AbortController();
    // Setup the global abort controller so
    // the next call can abort this one if needed
    add_page_abort_controller = current_abort_controller;

    if (cards_data.length == 0) {
        return;
    }

    // Convert ids to format we want
    var post_body = {
        "scryfall_ids": []
    }
    for (var card of cards_data) {
        post_body.scryfall_ids.push(card.scryfall_id)
    }

    // Call scryfall api for all cards in the page at once
    await fetch(`/api/all_cards/many`, {
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

            for (var i = 0; i < cards_data.length; i++) {
                var collection_card = cards_data[i];
                var scryfall_card = cards_response.data[i];

                if (scryfall_card.image_uris){
                    collection_card.image_src = scryfall_card.image_uris[0];
                }
                else {
                    // TODO: Load default replacement image
                    console.log("Couldn't find image_uris image for card:");
                    console.log(scryfall_card);
                }
                collection_card.collector_number = scryfall_card.collector_number;
                collection_card.set = scryfall_card.set;
                collection_card.name = scryfall_card.name;
                collection_card.finishes = scryfall_card.finishes;
            }

            // Create all the card objects in the DOM
            for (var card of cards_data) {
                var grid = document.getElementById("card-display");
                var card_element = create_card(card);
                // This prevents more stuff from being added
                // after the search box is updated
                if (current_abort_controller.signal.aborted) {
                    console.log("Aborted")
                    break;
                }
                grid.appendChild(card_element);
                card_element._card_data = card;
            }
        });
}

function create_notification(text, success) {
    var container = document.getElementById("notification-container");

    if (success) {
        var template = document.getElementById("notification-success-template");
    }
    else {
        var template = document.getElementById("notification-failure-template");
    }

    var notification = template.content.firstElementChild.cloneNode(true);
    notification.innerHTML = text;
    container.appendChild(notification);

    // Remove notifiction on click
    notification.addEventListener('click', (e) => {
        e.target.parentNode.removeChild(e.target);
    });

    setTimeout(() => {
        // Check if we already removed the notification
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification)
        }
    }, 5000);

    return notification;
}

async function create_page_nav(collection_length) {
    var num_pages = Math.ceil(collection_length / PAGE_SIZE);
    var highest_page = num_pages - 1;
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
    for (var i = 1; i < Math.min(PAGE_NAV_SPAN + 1, num_pages - cur_page); i++){
        var new_link = document.createElement("a");
        url.searchParams.set('page', cur_page + i);
        new_link.href = url.toString();
        new_link.innerHTML = `${cur_page + i}`;
        new_link.className = "page-nav-link";
        page_nav.appendChild(new_link);
    }

    if (highest_page - cur_page > PAGE_NAV_SPAN) {
        var elipses = document.createElement("div");
        elipses.innerHTML = "...";
        elipses.style.display = "inline";
        page_nav.appendChild(elipses)

        var last_link = document.createElement("a");
        url.searchParams.set('page', highest_page);
        last_link.href = url.toString();
        last_link.innerHTML = `${highest_page}`
        last_link.className = "page-nav-link"
        page_nav.appendChild(last_link);
    }
}

async function initialize(create_card, load_page) {
    const urlParams = new URLSearchParams(location.search);
    var search_query = '';
    if (urlParams.has('search')) {
        search_query = urlParams.get('search');
        document.getElementById("search").value = search_query;
    }
    if (urlParams.has('page')) {
        cur_page = Number(urlParams.get('page'));
        load_page(urlParams.get('page'), search_query);
    }
    else {
        load_page(0, search_query);
    }

    document.getElementById("search").addEventListener('input', (e) => {
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

        load_page(cur_page, search_text);
    })
}

export {create_page_nav, add_page, initialize, create_notification}
