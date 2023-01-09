import {create_page_nav, add_page, initialize, create_notification} from './paged_cards.js'
import {init_modal, populate_modal, set_modal_card, close_modal} from './card_details_modal.js'

function plus_minus_listener(card, card_data, amount){
    var quantity_text = card.querySelector(".card-quantity");
    var message_body = {
        'scryfall_id': card_data['scryfall_id'],
        'quantity': amount,
        'finish': card_data['finish'],
        'condition': card_data['condition'],
        'language': card_data['language'],
        'signed': card_data['signed'],
        'altered': card_data['altered'],
        'notes': card_data['notes']
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
                if (amount > 0){
                    create_notification(`Adding card failed. Error was ${json_response.error}`);
                }
                else {
                    create_notification(`Removing card failed. Error was ${json_response.error}`);
                }
            }
            else {
                var card = json_response.card;
                var delta = json_response.delta;
                var new_total = json_response.new_total;
                if (delta > 0){
                    create_notification(`Successfully added ${delta}x ${card.name}`, true);
                }
                else {
                    create_notification(`Successfully removed ${delta*-1}x ${card.name}`, false);
                }
                quantity_text.innerHTML = `${card.name} (${new_total})`;
            }
        });
}

// Takes a dict containing elements of output.csv and
// an image_src and returns a div containing a card
function create_card(card_data) {
    var template = document.getElementById("card-template");
    var card = template.content.firstElementChild.cloneNode(true);

    var image = card.querySelector(".card-image");
    image.src = card_data.image_src;

    var quantity_text = card.querySelector(".card-quantity");
    quantity_text.innerHTML = `${card_data.name} (${card_data.quantity})`;

    var plus_button = card.querySelector(".plus-button");
    var minus_button = card.querySelector(".minus-button");
    var edit_button = card.querySelector(".edit-button");

    plus_button.addEventListener('click', () => {
        plus_minus_listener(card, card._card_data, 1);
    });

    minus_button.addEventListener('click', () => {
        plus_minus_listener(card, card._card_data, -1);
    });

    edit_button.addEventListener('click', () => {
        console.log(card._card_data);
        populate_modal(card._card_data.scryfall_id, card._card_data.collection_id);
    });

    const tester = document.createElement("div");
    tester.id = "string-size-test";

    document.body.appendChild(tester);

    // There must be a better way to get the width
    // of text than actually putting in the dom and getting the value
    // but I can't find it.
    tester.appendChild(card);

    while (quantity_text.getBoundingClientRect().width > image.getBoundingClientRect().width) {
        var font_size = window.getComputedStyle(quantity_text).getPropertyValue("font-size");
        quantity_text.style.fontSize = parseInt(font_size, 10) - 1;
    }

    if (card_data.finish == 'foil' || card_data.finish == 'etched'){
        var image_container = card.querySelector(".card-image-container");
        var foil_overlay = image_container.querySelector(".foil-overlay");
        foil_overlay.style.visibility = 'visible';
    }

    document.body.removeChild(tester);

    return card;
}

function commit_card_changes() {
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
        // We expect populate_modal() to have saved _collection_id for us
        var collection_id = document.getElementById("myModal")._collection_id;
        var finish = finish_selector.value;
        var condition = condition_selector.value;
        var language = language_selector.options[language_selector.selectedIndex].text;
        var signed = signed_input.checked;
        var altered = alter_input.checked;
        var notes = notes_text.value;
        const username = new URL(window.location.href).pathname.split('/')[1];
        var message_body = {
            'username': username,
            'target': collection_id,
            'replacement': {
                'quantity': quantity,
                'finish': finish,
                'condition': condition,
                'language': language,
                'signed': signed,
                'altered': altered,
                'notes': notes
            }
        };

        fetch(`/api/collection`, {
            method: 'PATCH',
            headers: {
                'Content-Type':'application/json'
            },
            body: JSON.stringify(message_body)
        })
        .then(response => response.json())
        .then(json_response => {
            if (!json_response.successful) {
                create_notification(json_response.error, false);
                close_modal();
                return;
            }
            const target_collection_id = json_response.replaced_card_id;
            const new_finish = json_response.new_card.finish;
            const new_scryfall_id = json_response.new_card.scryfall_id;
            const new_quantity = json_response.new_card.quantity;
            const card_name = json_response.new_card.name;
            for (var child of document.querySelector("#card-display").children){
                if (child._card_data.collection_id == target_collection_id){
                    const card_title = child.querySelector(".card-quantity");
                    const img = child.querySelector("img");
                    const foil_overlay = child.querySelector(".foil-overlay");

                    card_title.innerHTML = `${card_name} (${new_quantity})`

                    fetch(`/api/by_id?scryfall_id=${new_scryfall_id}`)
                        .then(response => response.json())
                        .then(scryfall_card => {
                            if (scryfall_card.image_uri) {
                                img.src = scryfall_card.image_uri;
                            }
                            else if (scryfall_card.card_faces) {
                                img.src = scryfall_card.card_faces[0].image_uri;
                            }
                            else {
                                console.log("Couldn't find image_uris image for card:");
                                console.log(scryfall_card);
                            }
                    })
                    if (new_finish == 'foil' || new_finish == 'etched') {
                        foil_overlay.style.visibility = 'visible';
                    }
                    else {
                        foil_overlay.style.visibility = 'hidden';
                    }
                    // TODO: This is a recipe for disaster.
                    // If we change what values we keep track of in _card_data
                    // then this might fall behind (because it's expecting main.py
                    // to return the right values for us to assign here).
                    //
                    // I think a better solution is to not save data to DOM objects,
                    // but rather to keep a list of objects and make sure the DOM
                    // objects always stay in sync, probably by making them actual
                    // Objects with methods and stuff.
                    //
                    // This seems to work for now, but it's really fragile.
                    Object.assign(child._card_data, json_response.new_card);
                }
            }
            create_notification(`Updated ${card_name}`, true);
            close_modal();
        })
}

async function load_page(page_num, search_query) {
    const username = new URL(window.location.href).pathname.split('/')[1];
    if (search_query) {
        var response = await fetch(`/api/collection?page=${page_num}&query=search&text=${search_query}&username=${username}`)
            .then(response => response.json());
    }
    else {
        var response = await fetch(`/api/collection?page=${page_num}&username=${username}`)
            .then(response => response.json());
    }
    if (!response.successful) {
        console.log(response);
        create_notification(response.error, false);
        return;
    }
    var length = response.length;
    create_page_nav(length);
    var grid = document.getElementById("card-display");
    while (grid.lastChild) {
        grid.removeChild(grid.lastChild);
    }
    add_page(response.cards, create_card);
}

async function main() {
    await initialize(create_card, load_page);
    init_modal();
    var save_button = document.getElementById("commit-button");
    save_button.addEventListener('click', (e) => {
        // Don't accept repeats
        if (e.repeat) {
            return;
        }
        commit_card_changes()
    })

}


document.addEventListener("DOMContentLoaded", main);

