/*
const socket = io("/admin");
let existing_stat_titles = [];

$("#add-student-btn").click(function(event) {
    socket.emit("my event", {data: "hello?"});
    console.log("sent");
    return false;
});

socket.on("update_stats", function(stats){
    const stats_container = $("#stats-container");

    for (const title in stats)
    {
        if (existing_stat_titles.indexOf(title) < 0)
        {
            const value = stats[title];
            const card_html = `<div class="col-3 my-2">
                               <div class="stat-box text-center">
                               <div class="stat-headline">${value}</div>
                               <div class="stat-description mb-4">${title}</div>
                               </div>
                               </div>`;
            stats_container.append(card_html);
            existing_stat_titles.push(title);
        }
    }
});
*/

String.prototype.format = String.prototype.format ||
function () {
    "use strict";
    var str = this.toString();
    if (arguments.length) {
        var t = typeof arguments[0];
        var key;
        var args = ("string" === t || "number" === t) ?
            Array.prototype.slice.call(arguments)
            : arguments[0];

        for (key in args) {
            str = str.replace(new RegExp("\\{" + key + "\\}", "gi"), args[key]);
        }
    }

    return str;
};

$(document).ajaxError(function( event, jqxhr, settings, thrownError ) {
    console.log("--- XHR ERROR: " + thrownError + " ---");
    console.log(jqxhr);
    console.log(settings);
    console.log("--- END XHR ERROR ---");
    alert(`
    An XHR error occurred.
    Check your network connection and try again.
    If the error persists, contact Jacob.\n
    Response code: ${jqxhr.status} ${jqxhr.statusText}
    Endpoint: ${settings.type} ${settings.url}`);
});

const POST_RESTART_ENDPOINT = "/api/system/restart";
const POST_POWEROFF_ENDPOINT = "/api/system/poweroff";
const POST_PROGRAM_OPTIONS = "/api/pluggram/{0}/options";
let presumed_dead = false;

function restart() {
    if (!presumed_dead)
    {
        console.log("Restart...");
        $.post(POST_RESTART_ENDPOINT, function(data, textStatus, jqXHR){
            console.log("Restart posted " + jqXHR.status);
            presumed_dead = true;
            iziToast.show({
                title: 'Restarting...',
                message: 'This page will automatically reload in 30 seconds.',
                position: 'center',
                drag: false,
                close: false,
                icon: 'bi bi-arrow-repeat',
                backgroundColor: '#dda458',
                timeout: 30000,
                layout: 2,
                displayMode: 'replace',
                onClosing: function () {
                    window.location.reload(true);
                }
            });
        });
    }
}

$("#restart-btn").click(restart);

function poweroff() {
    if (!presumed_dead)
    {
        console.log("Poweroff...");
        $.post(POST_POWEROFF_ENDPOINT, function(data, textStatus, jqXHR){
            console.log("Poweroff posted " + jqXHR.status);
            presumed_dead = true;
            iziToast.show({
                title: 'Shutting down...',
                message: 'You can now close this tab.',
                drag: false,
                backgroundColor: '#dd5858',
                layout: 2,
                icon: 'bi bi-power',
                displayMode: 'replace',
                position: 'center',
                timeout: null,
                onClosing: function () {
                    close();
                }
            });
        });
    }
}

$("#poweroff-btn").click(poweroff);

function add_params_to_url(url, params)
{
    const url_obj = new URL(url);
    url_obj.search = new URLSearchParams(params);
    return url_obj.toString();
}

let settings_forms = {};

function save_program_settings(program_name)
{
    const modal_form = settings_forms[program_name];
    const inputs = $(modal_form).find("input");
    let value_map = {};

    for (const input of inputs)
    {
        const input_type = input.type;
        const option_key = $(input).data("program-option").replace("-", "_");
        const option_value = input.value;

        if (input_type == "number")
        {
            value_map[option_key] = option_value * 1;
        }
        else if (input_type == "color")
        {
            value_map[option_key] = parseInt(option_value.substring(1), 16);
        }
        else if (input_type == "checkbox")
        {
            if (option_value === "on")
            {
                value_map[option_key] = true;
            }
            else
            {
                value_map[option_key] = false;
            }
        }
        else
        {
            value_map[option_key] = option_value;
        }
    }

    const path = POST_PROGRAM_OPTIONS.format(program_name);
    $.post(path, value_map, function(data, textStatus, jqXHR){
        console.log("Pluggram settings update posted " + jqXHR.status);
        display_name = data["display_name"];
        saved = data["saved"];
        iziToast.show({
            title: `Updated ${display_name}`,
            message: saved ? 'New values stored successfully.' : 'No fields needed updating.',
            drag: false,
            theme: 'dark',
            backgroundColor: '#0d6efd',
            icon: 'bi bi-pen'
        });
    });
}

const settings_submit_btns = $(".settings-modal-submit");

for (const btn of settings_submit_btns)
{
    const parent_modal = btn.closest(".modal");
    const program_name = $(parent_modal).data("program-name");
    const modal_form = $(parent_modal).find("form")[0];
    settings_forms[program_name] = modal_form;

    $(btn).click(function() {
        save_program_settings(program_name);
    });
}

console.log(settings_forms);
