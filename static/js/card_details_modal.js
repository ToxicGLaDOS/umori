var close_modal_callback = null

function set_modal_card(scryfall_id) {
    var modal_card = document.getElementById("modal-card-img");
    fetch(`/api/by_id?scryfall_id=${scryfall_id}`)
        .then(response => response.json())
        .then(scryfall_card => {
            console.log(scryfall_card);
            if (scryfall_card.image_uris) {
                modal_card.src = scryfall_card.image_uris[0];
            }
            else {
                console.log("Couldn't find image_uris for card:");
                console.log(scryfall_card);
            }
        })
}

function close_modal() {
    var modal = document.getElementById("myModal");
    modal.style.display = "none";

    if (close_modal_callback != null) {
        close_modal_callback();
    }

    // Reset _card_data so we don't have old data hanging around
    modal._card_data = null;
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

function open_modal() {
    // Get the modal
    var modal = document.getElementById("myModal");

    // Open the modal
    modal.style.display = "block";

    var add_button = document.getElementById("commit-button");

    // Set focus on the add button
    add_button.focus()

    return modal;
}

async function populate_modal(scryfall_id, collection_id = null) {
    var modal = open_modal();
    // We hold onto collection_id so that we can send it
    // along for PATCH requests
    modal._collection_id = collection_id;

    var quantity_input = document.getElementById('quantity-input');
    var finish_select = document.getElementById('finish-select');
    var condition_select = document.getElementById('condition-select');
    var signed_input = document.getElementById('signed-input');
    var alter_input = document.getElementById('alter-input');
    var notes_input = document.getElementById('notes');
    var fetechs = [
        fetch(`/api/by_id?scryfall_id=${scryfall_id}`),
        fetch(`/api/all_cards/languages?scryfall_id=${scryfall_id}`)
    ]
    if (collection_id != null) {
        fetechs.push(fetch(`/api/collection/by_id?collection_id=${collection_id}`))
    }
    const responses = await Promise.all(fetechs);
    const [by_id_response, langs_response, collection_response] = await Promise.all(responses.map(r => r.json()));

    if (collection_id != null) {
        for (var i=0; i < condition_select.options.length; i++) {
            var condition_option = condition_select.options[i]
            if (condition_option.value == collection_response.card.condition) {
                condition_option.selected = true;
            }
        }

        quantity_input.value = collection_response.card.quantity;
        signed_input.checked = collection_response.card.signed;
        alter_input.checked = collection_response.card.altered;
        notes_input.value = collection_response.card.notes;
    }

    if (!by_id_response.successful) {
        // TODO: Create notification
        console.log(by_id_response);
    }
    var finishes = by_id_response.finishes;
    finishes.sort(finishes_cmp);

    var lang_selector = document.getElementById('lang-select');
    var finish_selector = document.getElementById('finish-select');
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

    // Remove all language options
    while (lang_selector.lastChild) {
        lang_selector.removeChild(lang_selector.lastChild);
    }

    // Generate new language options
    for (var lang_obj of lang_objs) {
        var selected = lang_obj.scryfall_id == scryfall_id;
        var option = new Option(lang_obj.lang, lang_obj.scryfall_id, false, selected);
        lang_selector.appendChild(option);
    }

    // Remove all finish options
    while (finish_selector.lastChild) {
        finish_selector.removeChild(finish_selector.lastChild);
    }

    // Generate new finish options
    for (var finish_name of finishes) {
        var option = new Option(finish_name, finish_name);
        finish_selector.appendChild(option);
    }

    // Set default finish
    if (collection_id != null) {
        for (var i=0; i < finish_select.options.length; i++) {
            var finish_option = finish_select.options[i]
            if (finish_option.value == collection_response.card.finish) {
                finish_option.selected = true;
            }
        }
    }

    set_foil_overlay();

    // Add default lang card to modal
    set_modal_card(lang_selector.value);
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

function init_modal(close_callback) {
    close_modal_callback = close_callback
    // Get the modal
    var modal = document.getElementById("myModal");

    // Get the <span> element that closes the modal
    var span = document.getElementsByClassName("modal-close")[0];

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
            close_modal();
        }
    }

    // Close modal on escape press
    modal.addEventListener('keyup', (e) => {
        if (e.key == 'Escape') {
            close_modal();
        }
    });

    var lang_selector = document.getElementById('lang-select');
    // Setup listener to change card when new lang is selected
    lang_selector.addEventListener('change', (e) => {
        var scryfall_id = e.target.value
        set_modal_card(scryfall_id);
    });
}

export {init_modal, populate_modal, set_modal_card, close_modal}
