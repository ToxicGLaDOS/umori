/**
 * Get client side timezone.
 * From: https://stackoverflow.com/questions/1091372/getting-the-clients-time-zone-and-offset-in-javascript
 *
 * @returns {(+|-)HH:mm} - Where `HH` is 2 digits hours and `mm` 2 digits minutes.
 * @example
 * // From Indian/Reunion with UTC+4
 * // '+04:00'
 * getTimeZone()
 */
const getTimeZone = () => {
    const timezoneOffset = new Date().getTimezoneOffset()
    const offset = Math.abs(timezoneOffset)
    const offsetOperator = timezoneOffset < 0 ? '+' : '-'
    const offsetHours = Math.floor(offset / 60).toString().padStart(2, '0')
    const offsetMinutes = Math.floor(offset % 60).toString().padStart(2, '0')

    return `${offsetOperator}${offsetHours}:${offsetMinutes}`
}

function get_current_datestamp() {
    const now = new Date().toISOString();
    // Remove the milliseconds part
    const timestamp = now.slice(0, now.lastIndexOf("."));

    return timestamp;
}

function main() {
    const generate_token_button = document.getElementById("generate-token-button");
    const token_text = document.getElementById("token-text");
    const valid_until = document.getElementById("valid-until");
    valid_until.min = get_current_datestamp();

    generate_token_button.addEventListener('click', () => {
        var valid_until_timestamp = valid_until.value;
        if (valid_until_timestamp != '') {
            valid_until_timestamp += getTimeZone();
        }
        else {
            valid_until_timestamp = null;
        }

        fetch('', {
            method: 'POST',
            headers: {
                    'Content-Type':'application/json'
            },
            body: JSON.stringify({
                "valid_until": valid_until_timestamp,
            })
        })
            .then(response => response.json())
            .then(json_response => {
                token_text.innerHTML = JSON.stringify(json_response);
            });
    });
}
document.addEventListener("DOMContentLoaded", main);
