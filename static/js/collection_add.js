import {create_page_nav, add_page, initialize, create_notification} from './paged_cards.js'

// Takes a dict containing elements of output.csv and
// an image_src and returns a div containing a card
function create_card(card_data) {
    var template = document.getElementById("card-template");
    var card = template.content.firstElementChild.cloneNode(true);

    var image = card.querySelector('.card-image')
    image.src = card_data.image_src;

    var title = card.querySelector('.card-quantity')
    title.innerHTML = `${card_data.name} (${card_data.set}:${card_data.collector_number})`;

    // There must be a better way to get the width
    // of text than actually putting in the dom and getting the value
    // but I can't find it.
    document.body.appendChild(card);

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

    document.body.removeChild(card);

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

function open_modal() {
    // Get the modal
    var modal = document.getElementById("myModal");

    // Open the modal
    modal.style.display = "block";

    var add_button = document.getElementById("add-button");

    // Set focus on the add button
    add_button.focus()

    return modal;
}

function close_modal_and_focus_search() {
    var modal = document.getElementById("myModal");
    modal.style.display = "none";

    // Focus search and highlight the text
    var search = document.getElementById('search');
    search.select();
    search.focus();

    var fine_filter = document.getElementById('fine-filter');
    fine_filter.value = "";

    filter_page(fine_filter.value);
}

// Hides or unhides the foil overlay
function set_foil_overlay() {
    var finish_selector = document.getElementById("finish-select");
    var foil_overlay = document.getElementById("modal-card-foil-overlay");
    var value = finish_selector.selectedOptions[0].value;

    if (value == "foil" || value == "etched") {
        foil_overlay.style.visibility = "visible";
    }
    else {
        foil_overlay.style.visibility = "hidden";
    }
}

function init_modal() {
    // Get the modal
    var modal = document.getElementById("myModal");

    // Get the <span> element that closes the modal
    var span = document.getElementsByClassName("modal-close")[0];

    // Get the button that adds the cards to the database
    var add_button = document.getElementById("add-button");

    // Set up the foil over the modal cards when the user chooses that
    var foil_overlay = document.getElementById("modal-card-foil-overlay");
    foil_overlay.style.visibility = "hidden";

    var finish_selector = document.getElementById("finish-select");
    finish_selector.addEventListener("change", set_foil_overlay);

    // When the user clicks on <span> (x), close the modal
    span.onclick = function() {
        modal.style.display = "none";
    }

    // When the user clicks anywhere outside of the modal, close it
    window.onclick = function(event) {
        if (event.target == modal) {
            close_modal_and_focus_search();
        }
    }

    // Close modal on escape press
    modal.addEventListener('keyup', (e) => {
        if (e.key == 'Escape') {
            close_modal_and_focus_search();
        }
    });

    add_button.addEventListener('click', (e) => {
        // Don't accept repeats
        if (e.repeat) {
            return;
        }
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
        var language = language_selector.options[language_selector.selectedIndex].text;
        var signed = signed_input.checked;
        var altered = alter_input.checked;
        var notes = notes_text.value;

        var message_body = {
            'scryfall_id': scryfall_id,
            'quantity': quantity,
            'finish': finish,
            'condition': condition,
            'language': language,
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
                close_modal_and_focus_search();
            });
    });
}

function add_card_to_modal(scryfall_id) {
    var modal_card = document.getElementById("modal-card-img");
    fetch(`/api/by_id?scryfall_id=${scryfall_id}`)
        .then(response => response.json())
        .then(scryfall_card => {
            if (scryfall_card.image_uri) {
                modal_card.src = scryfall_card.image_uri;
            }
            else if (scryfall_card.card_faces) {
                modal_card.src = scryfall_card.card_faces[0].image_uri;
            }
            else {
                console.log("Couldn't find image_uris image for card:");
                console.log(scryfall_card);
            }
        })
}

function finishes_cmp(a, b) {
    var order = ["nonfoil", "foil", "etched", "glossy"];
    var a_index = order.indexOf(a);
    var b_index = order.indexOf(b);

    // If a new finish is printed we'll default it to the end of the list
    if (a_index == -1) {
        a_index = order.length;
    }
    if (b_index == -1) {
        b_index = order.length;
    }

    return order.indexOf(a) - order.indexOf(b);
}

function populate_modal(scryfall_id) {
    var modal = open_modal();
    var modal_content = modal.getElementsByClassName('modal-content')[0];

    fetch(`/api/by_id?scryfall_id=${scryfall_id}`)
        .then(response => response.json())
        .then(json_response => {
            if (!json_response.successful) {
                console.log(json_response);
            }
            var finishes = json_response.finishes;
            finishes.sort(finishes_cmp);
            fetch(`/api/all_cards/languages?scryfall_id=${scryfall_id}`)
                .then(response => response.json())
                .then(langs_response => {
                    var lang_selector = document.getElementById('lang-select');
                    var finish_selector = document.getElementById('finish-select');
                    console.log(langs_response);
                    var groups = langs_response.reduce((groups, obj) => {
                        // Ensures we always have a non_default list
                        groups['non_default'] = groups['non_default'] || [];
                        if (obj.default) {
                            groups['default'] = obj;
                        }
                        else {
                            groups['non_default'].push(obj);
                        }
                        return groups;
                    }, {});

                    var default_lang_obj = groups['default'];
                    console.log(groups);
                    var non_default_lang_objs = groups['non_default'].sort((a, b) => {
                        if (a.lang < b.lang) {
                            return -1;
                        }
                        if (a.lang > b.lang){
                            return 1;
                        }
                        return 0;
                    });

                    var lang_objs = []
                    lang_objs.push(default_lang_obj);
                    lang_objs = lang_objs.concat(non_default_lang_objs);

                    lang_selector._lang_data = lang_objs;

                    // Remove all language options
                    while (lang_selector.lastChild) {
                        lang_selector.removeChild(lang_selector.lastChild);
                    }

                    // Generate new language options
                    for (var lang_obj of lang_selector._lang_data) {
                        var option = new Option(lang_obj.lang, lang_obj.scryfall_id);
                        lang_selector.appendChild(option);
                    }

                    // Remove all finsh options
                    while (finish_selector.lastChild) {
                        finish_selector.removeChild(finish_selector.lastChild);
                    }

                    // Generate new finish options
                    for (var finish of finishes) {
                        var option = new Option(finish, finish);
                        finish_selector.appendChild(option);
                    }

                    set_foil_overlay();

                    // Add default lang card to modal
                    add_card_to_modal(lang_selector.value);
                })
        });
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

async function main() {
    init_modal();

    var lang_selector = document.getElementById('lang-select');
    // Setup listener to change card when new lang is selected
    lang_selector.addEventListener('change', (e) => {
        var scryfall_id = e.srcElement.value
        add_card_to_modal(scryfall_id);
    });

    var search = document.getElementById('search');
    var fine_filter = document.getElementById('fine-filter');
    var form = document.getElementById('search-form');

    bind_full_press(search, search_event_listener);
    bind_full_press(fine_filter, search_event_listener);

    fine_filter.addEventListener('input', (e) => {
        var filter_text = e.currentTarget.value;
        filter_page(filter_text);
    })

    await initialize(create_card, load_page);
}


document.addEventListener("DOMContentLoaded", main)

