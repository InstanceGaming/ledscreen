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

function filter_status_response(jqXHR, success)
{
    if (jqXHR.status == 403)
    {
        window.location.reload(true);
    }
    else if (jqXHR.status == 200 || jqXHR.status == 202)
    {
        return success();
    }
    else
    {
        console.log(`unexpected response ${jqXHR.status}`);
        iziToast.show({
            title: "Error",
            message: "A problem occurred trying to process this action. Please contact Jacob.",
            drag: false,
            theme: 'dark',
            backgroundColor: '#dd5858',
            icon: 'bi bi-x-lg'
        });
    }
    return false;
}

const POST_RESTART_ENDPOINT = "/api/system/restart";
const POST_POWEROFF_ENDPOINT = "/api/system/poweroff";
const POST_START_PROGRAM = "/api/pluggram/{0}/run";
const POST_STOP_PROGRAM = "/api/pluggrams/stop";
const POST_RUNNING_PROGRAM = "/api/pluggrams/running";
const POST_PROGRAM_OPTIONS = "/api/pluggram/{0}/options";
let presumed_dead = false;

function restart() {
    if (!presumed_dead)
    {
        $.post(POST_RESTART_ENDPOINT, function(data, textStatus, jqXHR){
            filter_status_response(jqXHR, function () {
                if (jqXHR.status == 202)
                {
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
                }
                else
                {
                    iziToast.show({
                        title: 'Restarting?',
                        message: 'The system refused to restart, please try again.',
                        position: 'center',
                        drag: false,
                        icon: 'bi bi-x-lg',
                        backgroundColor: '#dda458',
                        layout: 2,
                        displayMode: 'replace'
                    });
                }
            });
        });
    }
}

$("#restart-btn").click(restart);

function poweroff() {
    if (!presumed_dead)
    {
        $.post(POST_POWEROFF_ENDPOINT, function(data, textStatus, jqXHR){
            filter_status_response(jqXHR, function() {
                if (jqXHR.status == 202)
                {
                    presumed_dead = true;
                    iziToast.show({
                        title: 'Shutting down...',
                        message: 'You can now close this tab.',
                        drag: false,
                        close: false,
                        theme: 'dark',
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
                }
                else
                {
                    iziToast.show({
                        title: 'Shutting down?',
                        message: 'The system refused to shutdown, please try again.',
                        drag: false,
                        theme: 'dark',
                        backgroundColor: '#dd5858',
                        layout: 2,
                        icon: 'bi bi-x-lg',
                        displayMode: 'replace',
                        position: 'center'
                    });
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
const settings_submit_btns = $(".settings-modal-submit");

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
        filter_status_response(jqXHR, function() {
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
            return true;
        });
    });
}

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

function get_running_program_name()
{
    let program_name = null;
    $.get(POST_RUNNING_PROGRAM, function(data, textStatus, jqXHR){
        filter_status_response(jqXHR, function() {
            program_name = data["name"];
        });
    });
    return program_name;
}

let play_stop_map = {};
const play_stop_btns = $(".program-start-stop");
let running_program_name = null;

function set_play_stop_btn(program_name, running, disabled)
{
    const btn = play_stop_map[program_name];
    $(btn).prop("disabled", disabled);
    $(btn).removeClass("btn-warning");

    if (running)
    {
        btn.innerHTML = `<i class="bi-stop-fill" role="img" aria-label="Stop program"></i>`;
        btn.title = "Stop program";
        $(btn).removeClass('btn-success').addClass('btn-danger');
    }
    else
    {
        btn.innerHTML = `<i class="bi-play-fill" role="img" aria-label="Start program"></i>`;
        btn.title = "Start program";
        $(btn).removeClass('btn-danger').addClass('btn-success');
    }
}

function start_stop_clicked(program_name)
{
    const btn = play_stop_map[program_name];
    btn.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>`;

    if (program_name === running_program_name)
    {
        $.post(POST_STOP_PROGRAM, function(data, textStatus, jqXHR){
            filter_status_response(jqXHR, function() {
                console.log(`stopped ${program_name}`);
            });
        });
    }
    else
    {
        if (running_program_name == null)
        {
            const path = POST_START_PROGRAM.format(program_name);
            $.post(path, function(data, textStatus, jqXHR){
                filter_status_response(jqXHR, function() {
                    console.log(`started ${program_name}`);
                });
            });
        }
    }

    update_play_stop_btns();
}

function update_play_stop_btns()
{
    running_program_name = get_running_program_name();

    for (const pb of play_stop_btns)
    {
        const program_name = $(pb).data("program-name");

        if (program_name === running_program_name)
        {
            set_play_stop_btn(program_name, true, false);
        }
        else
        {
            set_play_stop_btn(program_name, false, running_program_name != null);
        }
    }
}

for (const pb of play_stop_btns)
{
    const program_name = $(pb).data("program-name");
    play_stop_map[program_name] = pb;
    $(pb).click(function () {
        start_stop_clicked(program_name);
    });
}

update_play_stop_btns();
