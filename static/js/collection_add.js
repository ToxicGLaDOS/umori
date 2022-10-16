import {create_page_nav, add_page, initialize} from './paged_cards.js'

// Takes a dict containing elements of output.csv and
// an image_src and returns a div containing a card
function create_card(card) {
    var card_div = document.createElement("div");
    card_div.className = 'card-div';
    card_div.tabIndex = 0;
    var image = document.createElement("img");
    image.src = card.image_src;
    image.loading = "lazy";
    image.className = "card-image";
    var title = document.createElement("div");
    title.innerHTML = `${card.name} (${card.set}:${card.collector_number})`;
    title.className = 'card-quantity';

    card_div.appendChild(title);
    card_div.appendChild(image);

    // There must be a better way to get the width
    // of text than actually putting in the dom and getting the value
    // but I can't find it.
    document.body.appendChild(card_div);

    while (title.getBoundingClientRect().width > image.getBoundingClientRect().width) {
        var font_size = window.getComputedStyle(title).getPropertyValue("font-size");
        title.style.fontSize = parseInt(font_size, 10) - 1;
    }

    document.body.removeChild(card_div);

    return card_div;
}

async function load_page(page_num, search_query) {
    if (search_query) {
        var response = await fetch(`/api/all_cards?page=${page_num}&query=search&text=${search_query}`)
            .then(response => response.json());
    }
    else {
        var response = await fetch(`/api/all_cards?page=${page_num}`)
            .then(response => response.json());
    }
    var length = response.length;

    create_page_nav(length);
    var grid = document.getElementById("collection-grid");
    while (grid.lastChild) {
        grid.removeChild(grid.lastChild);
    }
    add_page(response.cards, create_card);
}

function create_notification(text) {
    var container = document.getElementById("notification-container");
    var template = document.getElementById("notification-template");

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
}

function open_modal() {
    // Get the modal
    var modal = document.getElementById("myModal");

    // Open the modal
    modal.style.display = "block";

    return modal;
}

function init_modal() {
    // Get the modal
    var modal = document.getElementById("myModal");

    // Get the <span> element that closes the modal
    var span = document.getElementsByClassName("modal-close")[0];

    // Get the button that adds the cards to the database
    var add_button = document.getElementById("add-button");

    // When the user clicks on <span> (x), close the modal
    span.onclick = function() {
        modal.style.display = "none";
    }

    // When the user clicks anywhere outside of the modal, close it
    window.onclick = function(event) {
        if (event.target == modal) {
            modal.style.display = "none";
        }
    }

    add_button.addEventListener('click', (e) => {
        var quantity_input = document.getElementById("quantity-input");
        var finish_selector = document.getElementById("finish-select");
        var language_selector = document.getElementById("lang-select");
        var signed_input = document.getElementById("signed-input");
        var alter_input = document.getElementById("alter-input");
        var notes_text = document.getElementById("notes");

        if (quantity_input == null ||
            finish_selector == null ||
            language_selector == null ||
            signed_input == null ||
            alter_input == null ||
            notes_text == null) {
            alert("Couldn't one or more elements refusing to continue. Check log for details.");
            console.log("Quantity input:");
            console.log(quantity_input);
            console.log("Finish selector:");
            console.log(finish_selector);
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
        var scryfall_id = language_selector.value;
        var language = language_selector.options[language_selector.selectedIndex].text;
        var signed = signed_input.checked;
        var altered = alter_input.checked;
        var notes = notes_text.value;

        var message_body = {
            'scryfall_id': scryfall_id,
            'quantity': quantity,
            'finish': finish,
            'language': language,
            'signed': signed,
            'altered': altered,
            'notes': notes
        };

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
                    alert("Adding card failed. See log for details.")
                    console.log(json_response);
                    return;
                }
                console.log(json_response);
                var card = json_response.card;
                create_notification(`Successfully added ${quantity}x ${card.name}`);
            });
    });
}

function add_card_to_modal(scryfall_id) {
    var modal_card = document.getElementById("modal-card");
    fetch(`/api/by_id?scryfall_id=${scryfall_id}`)
        .then(response => response.json())
        .then(scryfall_card => {
            if (scryfall_card.image_uris) {
                modal_card.src = scryfall_card.image_uris.normal;
            }
            else if (scryfall_card.card_faces) {
                modal_card.src = scryfall_card.card_faces[0].image_uris.normal;
            }
            else {
                console.log("Couldn't find image_uris image for card:");
                console.log(scryfall_card);
            }
        })
}

async function main() {
    init_modal();

    var fine_filter = document.getElementById('fine-filter');
    fine_filter.addEventListener('keyup', (e) => {
        if (e.key === 'Enter') {
            var visible_cards = [];

            for (var card of document.getElementById('collection-grid').childNodes){
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

            var modal = open_modal();
            var modal_content = modal.getElementsByClassName('modal-content')[0];

            // Populate the modal
            fetch(`/api/by_id?scryfall_id=${selected_id}`)
                .then(response => response.json())
                .then(json_response => {
                    var finishes = json_response.finishes;
                    fetch(`/api/all_cards/languages?scryfall_id=${selected_id}`)
                        .then(response => response.json())
                        .then(langs_response => {
                            var lang_selector = document.getElementById('lang-select');
                            var finish_selector = document.getElementById('finish-select');
                            lang_selector._lang_data = langs_response;
                            // Remove all language options
                            while (lang_selector.lastChild) {
                                lang_selector.removeChild(lang_selector.lastChild);
                            }

                            // Generate new language options
                            for (var lang_obj of langs_response) {
                                var option = new Option(lang_obj.lang, lang_obj.scryfall_id);
                                lang_selector.appendChild(option);
                            }

                            // Remove all finsh options
                            while (finish_selector.lastChild) {
                                finish_selector.removeChild(finish_selector.lastChild);
                            }

                            // Generate new language options
                            for (var finish of finishes) {
                                var option = new Option(finish, finish);
                                finish_selector.appendChild(option);
                            }

                            // Add default lang card to modal
                            add_card_to_modal(lang_selector.value);

                            // Setup listener to change card when new lang is selected
                            lang_selector.addEventListener('change', (e) => {
                                var scryfall_id = e.srcElement.value
                                add_card_to_modal(scryfall_id);
                            });
                        })
                });
        }
    });
    fine_filter.addEventListener('input', (e) => {
        var filter_text = e.currentTarget.value;
        const set_regex = /^.*\(((.+):(.+))\)$/
        for (var card of document.getElementById('collection-grid').childNodes){
            var card_title = card.querySelector('.card-quantity').innerHTML;
            var matches = set_regex.exec(card_title);

            // The set:cn part of the name
            var set_colon_collector_number = matches[1];
            var set = matches[2];
            var collector_number = matches[3];

            if (set.includes(filter_text) || collector_number.includes(filter_text) || set_colon_collector_number.includes(filter_text)) {
                card.style.display = null;
            }
            else {
                card.style.display = 'none';
            }

            
        }
    })

    await initialize(create_card, load_page);
}


document.addEventListener("DOMContentLoaded", main)

