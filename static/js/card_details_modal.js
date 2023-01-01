var close_modal_callback = null

function set_modal_card(scryfall_id) {
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

function populate_modal(scryfall_id, card_data = null) {
    var modal = open_modal();
    // We hold onto card_data so that we can send it
    // along for PATCH requests
    modal._card_data = card_data;

    var quantity_input = document.getElementById('quantity-input');
    var finish_select = document.getElementById('finish-select');
    var condition_select = document.getElementById('condition-select');
    var signed_input = document.getElementById('signed-input');
    var alter_input = document.getElementById('alter-input');
    var notes_input = document.getElementById('notes');

    if (card_data != null) {
        for (var i=0; i < condition_select.options.length; i++) {
            var condition_option = condition_select.options[i]
            if (condition_option.value == card_data.condition) {
                condition_option.selected = true;
            }
        }

        quantity_input.value = card_data.quantity;
        signed_input.checked = card_data.signed;
        alter_input.checked = card_data.altered;
        notes_input.value = card_data.notes;
    }

    fetch(`/api/by_id?scryfall_id=${scryfall_id}`)
        .then(response => response.json())
        .then(json_response => {
            if (!json_response.successful) {
                console.log(json_response);
            }
            console.log(json_response);
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
                        var selected = lang_obj.lang == json_response.lang;
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
                    if (card_data != null) {
                        for (var i=0; i < finish_select.options.length; i++) {
                            var finish_option = finish_select.options[i]
                            if (finish_option.value == card_data.finish) {
                                finish_option.selected = true;
                            }
                        }
                    }

                    set_foil_overlay();

                    // Add default lang card to modal
                    set_modal_card(lang_selector.value);
                })
        });
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
}

export {init_modal, populate_modal, set_modal_card, close_modal}
