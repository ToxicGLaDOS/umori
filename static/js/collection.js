import {create_page_nav, add_page, initialize, create_notification} from './paged_cards.js'

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

    plus_button.addEventListener('click', () => {
        plus_minus_listener(card, card_data, 1);
    });

    minus_button.addEventListener('click', () => {
        plus_minus_listener(card, card_data, -1);
    });

    // There must be a better way to get the width
    // of text than actually putting in the dom and getting the value
    // but I can't find it.
    document.body.appendChild(card);

    while (quantity_text.getBoundingClientRect().width > image.getBoundingClientRect().width) {
        var font_size = window.getComputedStyle(quantity_text).getPropertyValue("font-size");
        quantity_text.style.fontSize = parseInt(font_size, 10) - 1;
    }

    if (card_data.finish == 'foil' || card_data.finish == 'etched'){
        var image_container = card.querySelector(".card-image-container");
        var foil_overlay = document.createElement("div");
        foil_overlay.className = 'foil-overlay';
        image_container.appendChild(foil_overlay);
    }

    document.body.removeChild(card);

    return card;
}

async function load_page(page_num, search_query) {
    if (search_query) {
        var response = await fetch(`/api/collection?page=${page_num}&query=search&text=${search_query}`)
            .then(response => response.json());
    }
    else {
        var response = await fetch(`/api/collection?page=${page_num}`)
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

async function main() {
    await initialize(create_card, load_page);
}


document.addEventListener("DOMContentLoaded", main);

