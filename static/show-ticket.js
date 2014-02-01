var panels = new Array('note', 'prio', 'tags', 'title', 'minutes', 'file', 'datedue', 'security', 'dependencies');
var selectedTab = null;

function showPanel(tab, name) {
    if (selectedTab) {
        selectedTab.style.backgroundColor = '';
    }
    selectedTab = tab;
    selectedTab.style.backgroundColor = '#D3D3D3';
    for (i = 0; i < panels.length; i++) {
        document.getElementById(panels[i]).style.display = (name == panels[i]) ? 'block' : 'none';
    }

    // Altera foco para caixas de texto
    if (name == 'note') {
        document.getElementById('formnote').focus();
    } else if (name == 'tags') {
        document.getElementById('formtags').focus();
    } else if (name == 'datedue') {
        document.getElementById('formdatedue').focus()
    } else if (name == 'dependencies') {
        document.getElementById('formdeps').focus()
    }

    // Rola página até o final
    window.scroll(0,document.body.offsetHeight);
    return false;
}

var cron;
var start_date;
var ms_acum = 0.0;
var title = document.title;

function startCron() {
    start_date = new Date().getTime();
    cron = setTimeout(doCron, 1000);
    document.fminutes.bstartcron.style.visibility = 'hidden';
    document.fminutes.bstopcron.style.visibility = 'visible';
}

function stopCron() {
    clearTimeout(cron);
    document.fminutes.bstartcron.style.visibility = 'visible';
    document.fminutes.bstopcron.style.visibility = 'hidden';
}

function doCron() {
    var delta = (new Date()).getTime() - start_date;
    ms_acum += delta;
    start_date = new Date().getTime();
    minutes = Math.floor(ms_acum/1000/60);
    document.title = '[' + minutes + '\'' + '] ' + title;
    document.fminutes.minutes.value = minutes;
    cron = setTimeout(doCron, 1000);
}

document.onkeydown = function(evt) {
    evt = evt || window.event;
    if(selectedTab == null && evt.keyCode == 78 && ! evt.shiftKey &&
            !evt.ctrlKey && !evt.altKey && !evt.metaKey &&
            evt.target instanceof HTMLBodyElement) {
        window.scroll(0,document.body.offsetHeight);
        showPanel(document.getElementById('notetab'), 'note');
        document.getElementById('formnote').focus();
        evt.preventDefault();
    }
}