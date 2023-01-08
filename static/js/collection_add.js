import {create_page_nav, add_page, initialize, create_notification} from './paged_cards.js'
import {init_modal, populate_modal, set_modal_card, close_modal} from './card_details_modal.js'

// Takes a dict containing elements of output.csv and
// an image_src and returns a div containing a card
function create_card(card_data) {
    var template = document.getElementById("card-template");
    var card = template.content.firstElementChild.cloneNode(true);
    card.addEventListener('click', open_card_in_modal);

    var image = card.querySelector('.card-image')
    image.src = card_data.image_src;

    var title = card.querySelector('.card-quantity')
    title.innerHTML = `${card_data.name} (${card_data.set}:${card_data.collector_number})`;

    const tester = document.createElement("div");
    tester.id = "string-size-test";

    document.body.appendChild(tester);

    // There must be a better way to get the width
    // of text than actually putting in the dom and getting the value
    // but I can't find it.
    tester.appendChild(card);

    while (title.getBoundingClientRect().width > image.getBoundingClientRect().width) {
        var font_size = window.getComputedStyle(title).getPropertyValue("font-size");
        title.style.fontSize = parseInt(font_size, 10) - 1;
    }

    // nonfoil and glossy are the 2 nonfoil options
    // foil and etched are both foils
    if (!(card_data.finishes.includes('nonfoil') || card_data.finishes.includes('glossy'))){
        var image_container = card.querySelector('.card-image-container')
        var foil_overlay = document.createElement("div");
        foil_overlay.className = 'foil-overlay';
        image_container.appendChild(foil_overlay);
    }

    document.body.removeChild(tester);
    return card;
}

async function load_page(page_num, search_query) {
    if (search_query) {
        var response = await fetch(`/api/all_cards?page=${page_num}&query=search&text=${search_query}&default=true`)
            .then(response => response.json());
    }
    else {
        var response = await fetch(`/api/all_cards?page=${page_num}&default=true`)
            .then(response => response.json());
    }
    var length = response.length;

    create_page_nav(length);
    var grid = document.getElementById("card-display");
    while (grid.lastChild) {
        grid.removeChild(grid.lastChild);
    }

    add_page(response.cards, create_card);
}

function open_card_in_modal(e) {
    const selected_id = e.currentTarget._card_data.scryfall_id
    populate_modal(selected_id);
}

// This is the event listener for when you want to open the modal
function search_event_listener(e) {
    if (e.key === 'Enter' && !e.repeat) {
        var visible_cards = [];

        for (var card of document.getElementById('card-display').childNodes){
            if (card.style.display != 'none') {
                visible_cards.push(card);
            }
        }

        if (visible_cards.length == 0) {
            console.log("No cards remaining.");
            return;
        }
        var selected_card = visible_cards[0];
        var selected_id = selected_card._card_data.scryfall_id;

        populate_modal(selected_id);
    }
}

// This function binds a keydown listener which in turn binds
// a keyup function to detect a full key press on a single element
// Multiple calls to this on the same element might break stuff
function bind_full_press(element, keyup_function) {
    element.addEventListener('keydown', (e) => {
        if (e.repeat) {
            return;
        }
        e.target.addEventListener('keyup', keyup_function, {once: true});
    });

    // We remove the keyup on focusout because it will be stuck on the
    // object if we don't
    element.addEventListener('focusout', (e) => {
        element.removeEventListener('keyup', keyup_function, {once: true});
    });
}

function filter_page(filter_text) {
    const set_regex = /^.*\(((.+):(.+))\)$/
    for (var card of document.getElementById('card-display').childNodes){
        var card_title = card.querySelector('.card-quantity').innerHTML;
        var matches = set_regex.exec(card_title);

        // The set:cn part of the name
        var set_colon_collector_number = matches[1];
        var set = matches[2];
        var collector_number = matches[3];

        if (set.startsWith(filter_text) || collector_number.startsWith(filter_text) || set_colon_collector_number.startsWith(filter_text)) {
            card.style.display = null;
        }
        else {
            card.style.display = 'none';
        }
    }
}

function focus_fine_filter() {
    // Focus search and highlight the text
    var search = document.getElementById('search');
    search.select();
    search.focus();

    var fine_filter = document.getElementById('fine-filter');
    fine_filter.value = "";

    filter_page(fine_filter.value);
}

function add_card_to_database() {
    var quantity_input = document.getElementById("quantity-input");
    var finish_selector = document.getElementById("finish-select");
    var condition_selector = document.getElementById("condition-select");
    var language_selector = document.getElementById("lang-select");
    var signed_input = document.getElementById("signed-input");
    var alter_input = document.getElementById("alter-input");
    var notes_text = document.getElementById("notes");

    // We ensure that we've found all the elements
    // so we don't send a bad request to the server
    if (quantity_input == null ||
        finish_selector == null ||
        condition_selector == null ||
        language_selector == null ||
        signed_input == null ||
        alter_input == null ||
        notes_text == null) {
        alert("Couldn't find one or more elements refusing to continue. Check log for details.");
        console.log("Quantity input:");
        console.log(quantity_input);
        console.log("Finish selector:");
        console.log(finish_selector);
        console.log("Condition selector:");
        console.log(condition_selector);
        console.log("Language selector:");
        console.log(language_selector);
        console.log("Signed input:");
        console.log(signed_input);
        console.log("Alter input:");
        console.log(alter_input);
        console.log("Notes text:");
        console.log(notes_text);
        return;
    }

    var quantity = quantity_input.valueAsNumber;
    if (isNaN(quantity)) {
        alert("Quantity is NaN, refusing to continue.");
        return;
    }
    var finish = finish_selector.value;
    var condition = condition_selector.value;
    var scryfall_id = language_selector.value;
    var signed = signed_input.checked;
    var altered = alter_input.checked;
    var notes = notes_text.value;

    var message_body = {
        'scryfall_id': scryfall_id,
        'quantity': quantity,
        'finish': finish,
        'condition': condition,
        'signed': signed,
        'altered': altered,
        'notes': notes
    };

    // Make the POST request to add the card
    fetch(`/api/collection`, {
        method: 'POST',
        headers: {
            'Content-Type':'application/json'
        },
        body: JSON.stringify(message_body)
    })
        .then(response => response.json())
        .then(json_response => {
            if (!json_response.successful) {
                create_notification(`Adding card failed. Error was ${json_response.error}`);
            }
            else {
                var card = json_response.card;
                console.log(json_response);
                create_notification(`Successfully added ${quantity}x ${card.name}`, true);
            }
            close_modal();
        });
}

async function main() {
    init_modal(focus_fine_filter);
    // Get the button that adds the cards to the database
    var add_button = document.getElementById("commit-button");
    add_button.addEventListener('click', (e) => {
        // Don't accept repeats
        if (e.repeat) {
            return;
        }
        add_card_to_database()
    })

    var search = document.getElementById('search');
    var fine_filter = document.getElementById('fine-filter');

    bind_full_press(search, search_event_listener);
    bind_full_press(fine_filter, search_event_listener);

    fine_filter.addEventListener('input', (e) => {
        var filter_text = e.currentTarget.value;
        filter_page(filter_text);
    })

    await initialize(create_card, load_page);
}


document.addEventListener("DOMContentLoaded", main)

