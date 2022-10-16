import {create_page_nav, add_page, initialize} from './paged_cards.js'

// Takes a dict containing elements of output.csv and
// an image_src and returns a div containing a card
function create_card(card) {
    var card_div = document.createElement("div");
    card_div.className = 'card-div';
    var image = document.createElement("img");
    image.src = card.image_src;
    image.loading = "lazy";
    image.className = "card-image";
    var quantity_text = document.createElement("div");
    quantity_text.innerHTML = `${card.name} (${card.quantity})`;
    quantity_text.className = 'card-quantity';

    card_div.appendChild(quantity_text);
    card_div.appendChild(image);

    // There must be a better way to get the width
    // of text than actually putting in the dom and getting the value
    // but I can't find it.
    document.body.appendChild(card_div);

    while (quantity_text.getBoundingClientRect().width > image.getBoundingClientRect().width) {
        var font_size = window.getComputedStyle(quantity_text).getPropertyValue("font-size");
        quantity_text.style.fontSize = parseInt(font_size, 10) - 1;
    }

    document.body.removeChild(card_div);

    return card_div;
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
    var grid = document.getElementById("collection-grid");
    while (grid.lastChild) {
        grid.removeChild(grid.lastChild);
    }
    add_page(response.cards, create_card);
}

async function main() {
    await initialize(create_card, load_page);
}


document.addEventListener("DOMContentLoaded", main)

