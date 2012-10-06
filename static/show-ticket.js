var panels = new Array('note', 'prio', 'tags', 'title', 'minutes', 'contacts');
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
    } else if (name == 'contacts') {
        document.getElementById('formcontacts').focus();
    }

    return false;
}

var cron;
var minutes = 0;
var seconds = 0;
var title = document.title;

function startCron() {
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
    seconds++;
    if (seconds == 60) {
        seconds = 0;
        minutes++
    };
    document.title = '[' + minutes + '\'' + seconds + '"' + '] ' + title;
    document.fminutes.minutes.value = minutes + (seconds / 60);
    cron = setTimeout(doCron, 1000);
}