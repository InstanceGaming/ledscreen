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

function restart() {
    console.log("Restart...");
    $.post(POST_RESTART_ENDPOINT, function(data, textStatus, jqXHR){
        console.log("Restart posted " + jqXHR.status);
    });
}

$("#restart-btn").click(restart);

function poweroff() {
    console.log("Poweroff...");
    $.post(POST_POWEROFF_ENDPOINT, function(data, textStatus, jqXHR){
        console.log("Poweroff posted " + jqXHR.status);
    });
}

$("#poweroff-btn").click(poweroff);