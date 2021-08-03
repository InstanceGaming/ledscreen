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