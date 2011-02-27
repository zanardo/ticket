#!/usr/bin/perl
# Copyright (c) 2006-2011, J. A. Zanardo Jr. <zanardo@gmail.com>
# All rights reserved.
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE AUTHOR AND CONTRIBUTORS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. */

use strict;
use warnings;

use DBI;
use CGI qw(:standard);
use CGI::Carp qw(fatalsToBrowser);
use POSIX qw(strftime);
use MIME::Lite;
use Encode qw(encode);

# Configurações ###################################################
our $from_mail = 'root@localhost';	# E-mail remetente
our $smtp_mail = '127.0.0.1';	# Servidor SMTP
our $database = 'ticket.db'; # Caminho da base SQLite
###################################################################

our $uri = $ENV{'SCRIPT_NAME'};
our $css = "$uri?action=get-css";
our $VERSION = '1.0dev';
our $user = $ENV{'REMOTE_USER'} || 'anônimo';

our $dbh = DBI->connect("dbi:SQLite:dbname=$database","","") or die $!;

our $q = $ENV{'PATH_INFO'} || '';

# Descrição das Prioridades
our %priodesc = (
	'1' => '1. Ação Urgente',
	'2' => '2. Atenção',
	'3' => '3. Prioridade Normal',
	'4' => '4. Baixa Prioridade',
	'5' => '5. Baixíssima Prioridade'
);

# Descrição / cores das Tags
our %tagsdesc = ();
foreach(@{sql('select * from tagsdesc')}) {
	$tagsdesc{$_->{'tag'}} = {
		'description' => $_->{'description'},
		'bgcolor' => $_->{'bgcolor'} || 'yellow',
		'fgcolor' => $_->{'fgcolor'} || 'red'
	};
}

if(defined param('filter')) {
	my $filter = param('filter');
	if($filter eq '') {
		$filter = 'T o:m l:100';
	}
	my $filtere = escapeHTML($filter);
	my $s = $filter;

	# Show ticket.
	if($filter =~ /^#(\d+)$/) {
		print redirect("$uri/$1");
		exit;
	}

	# l:N -> limite de resultados
	my $limit = '';
	while($s =~ s/l:(\d+) *//) {
		$limit = "LIMIT $1";
	}

	# A -> abertos
	# F -> fechados
	# T -> todos
	my $status = 'AND status = 0';
	if($s =~ s/^F *//) { $status = 'AND status = 1' }
	elsif($s =~ s/^T *//) { $status = '' }
	elsif($s =~ s/^A *//) { $status = 'AND status = 0' }

	# t:foo -> tag "foo"
	my $tag = '';
	while($s =~ s/t:([^ ]+) *//) {
		my $t = $dbh->quote($1);
		$tag .= "AND id IN ( SELECT ticket_id FROM tags WHERE tag = $t ) ";
	}

	# o:[mcfp] -> ordem de modificação, criação, fechamento, prioridade
	my $order = 'ORDER BY datemodified DESC';
	while($s =~ s/o:([mcfp]) *//) {
		if($1 eq 'c') { $order = 'ORDER BY datecreated DESC' }
		elsif($1 eq 'm') { $order = 'ORDER BY datemodified DESC' }
		elsif($1 eq 'f') { $order = 'ORDER BY dateclosed DESC' }
		elsif($1 eq 'p') { $order = 'ORDER BY priority ASC, dateclosed ASC' }
	}

	# u:usuario -> usuário de criação, fechamento, comentário, etc
	my $user = '';
	while($s =~ s/u:([^ ]+) *//) {
		my $u = $dbh->quote($1);
		$user = "AND ( ( user = $u ) ";
		$user .= "OR ( id IN ( SELECT ticket_id FROM comments WHERE user = $u ) ) ";
		$user .= "OR ( id IN ( SELECT ticket_id FROM timetrack WHERE user = $u ) ) ";
		$user .= "OR ( id IN ( SELECT ticket_id FROM statustrack WHERE user = $u ) ) ) ";
	}

	# d[cmf]:YYYYMMDD-YYYYMMDD -> faixa de data de criação, modificação, fechamento
	my $datecreated = '';
	while($s =~ s/d([cmf])\:(\d{8})-(\d{8}) *//) {
		my $dt = $1;
		my $from = $2;
		my $to = $3;
		$from =~ s/^(\d{4})(\d{2})(\d{2})$/$1-$2-$3 00:00:00/;
		$to =~ s/^(\d{4})(\d{2})(\d{2})$/$1-$2-$3 23:59:59/;
		$from = $dbh->quote($from);
		$to = $dbh->quote($to);
		my $c = '';
		if($dt eq 'c') { $c = 'datecreated' }
		elsif($dt eq 'm') { $c = 'datemodified' }
		elsif($dt eq 'f') { $c = 'dateclosed' }
		$datecreated = "AND $c BETWEEN $from AND $to";
	}

	# d[cmf]:YYYYMMDD -> data de criação, modificação, fechamento
	while($s =~ s/d([cmf])\:(\d{8}) *//) {
		my $dt = $1;
		my $d = $2;
		$d =~ s/^(\d{4})(\d{2})(\d{2})$/$1-$2-$3/;
		my $from = "$d 00:00:00";
		my $to = "$d 23:59:59";
		$from = $dbh->quote($from);
		$to = $dbh->quote($to);
		my $c = '';
		if($dt eq 'c') { $c = 'datecreated' }
		elsif($dt eq 'm') { $c = 'datemodified' }
		elsif($dt eq 'f') { $c = 'dateclosed' }
		$datecreated = "AND $c BETWEEN $from AND $to";
	}

	# p:X-Y -> prioridade de X a Y
	my $prio = '';
	while($s =~ s/p\:(\d)-(\d) *//) {
		$prio = "AND priority BETWEEN $1 AND $2";
	}

	# p:X -> prioridade X
	while($s =~ s/p\:(\d) *//) {
		$prio = "AND priority = $1";
	}

	# match -> texto que sobrou
	my $match = '';
	if($s =~ /\w/) {
		my $m = $dbh->quote($s);
		$match = "AND id IN ( SELECT docid FROM search WHERE search MATCH $m )";
	}

	my $count = 0;

	print header(-expires => 'now'), 
		start_html(-style => 
			{'src' => $css}, -title => "Tickets: $filtere" );

	emit_header();
	print qq{<span class="title">Tickets</span>}, p;

	my $sql = qq{
		SELECT *
		FROM tickets
		WHERE ( 1 = 1 )
		  $status
		  $match
		  $tag
		  $user
		  $datecreated
		  $prio
		$order
		$limit
	};

	foreach(@{sql($sql)}) {
		$count++;
		show_ticket_small($_);
	}

	print p, "$count ticket(s) filtrado(s)";
	
	emit_footer();

}
elsif(defined param('action') and param('action') eq 'create-new-ticket') {
	my $title = param('title') || '';
	die 'O título deve ser preenchido.' if $title =~ /^[\s\t\r\n]*$/;
	sql('insert into tickets ( title, user, datecreated, datemodified ) values ( ?, ?, datetime(\'now\', \'localtime\'), datetime(\'now\', \'localtime\') )', $title, $user);
	my $id = $dbh->last_insert_id(undef, undef, 'tickets', 'id');
	print redirect("$uri/$id");;
	populate_search($id);
}
elsif(defined param('action') and param('action') eq 'create-new-note') {
	my $text = param('text') || '';
	die if $text =~ /^[\s\t\r\n]*$/;
	my $id = param('id');
	my $contacts = '';
	if(defined param('contacts')) {
		foreach(grep {!/^#/} split("[\r\n]+", param('contacts'))) {
			$contacts .= $_ . ", ";
		}
		$contacts =~ s/, $//;
		if($contacts ne '') {
			$text .= ' [Notificação enviada para: ' . $contacts . ']';
		}
	}
	$dbh->begin_work;
	sql('insert into comments ( ticket_id, user, comment, datecreated ) values ( ?,?,?,datetime(\'now\', \'localtime\') )', $id, $user, $text);
	sql('update tickets set datemodified = datetime(\'now\', \'localtime\') where id = ?', $id);
	$dbh->commit;
	send_email($id, get_title_from_ticket($id), $user, param('contacts'), $text);
	print redirect("$uri/$id");
	populate_search($id);
}
elsif(defined param('action') and param('action') eq 'register-minutes') {
	my $minutes = param('minutes') || 0;
	die if $minutes !~ /^[\d.]+$/;
	die "Minutos devem ser positivos!" unless $minutes > 0;
	$minutes = sprintf("%.2f", $minutes);
	my $id = param('parent');
	$dbh->begin_work;
	sql('insert into timetrack ( ticket_id, user, minutes, datecreated ) values ( ?,?,?,datetime(\'now\', \'localtime\') )', $id, $user, $minutes);
	sql('update tickets set datemodified = datetime(\'now\', \'localtime\') where id = ?', $id);
	$dbh->commit;
	print redirect("$uri/$id");
}
elsif(defined param('action') and param('action') eq 'close-ticket') {
	my $id = param('id') or die 'no id';
	$dbh->begin_work;
	sql('update tickets set status = 1, dateclosed = datetime(\'now\', \'localtime\'), datemodified = datetime(\'now\', \'localtime\') where id = ?', $id);
	sql('insert into statustrack ( ticket_id, user, status, datecreated ) values ( ?,?,\'close\',datetime(\'now\', \'localtime\'))', $id, $user);
	$dbh->commit;
	print redirect("$uri/$id");
	populate_search($id);
}
elsif(defined param('action') and param('action') eq 'reopen-ticket') {
	my $id = param('id') or die 'no id';
	$dbh->begin_work;
	sql('update tickets set status = 0, dateclosed = null, datemodified = datetime(\'now\', \'localtime\') where id = ?', $id);
	sql('insert into statustrack ( ticket_id, user, status, datecreated ) values ( ?,?,\'reopen\',datetime(\'now\', \'localtime\'))', $id, $user);
	$dbh->commit;
	print redirect("$uri/$id");
	populate_search($id);
}
elsif(defined param('action') and param('action') eq 'save-tags-ticket') {
	my $id = param('id') or die 'no id';
	my $tags = param('text') || '';
	$tags =~ s/^ +//g; $tags =~ s/ +$//g;
	my %tags = map { $_, 1 } split /[\s\t\r\n]+/, $tags;
	$dbh->begin_work;
	sql('delete from tags where ticket_id = ?', $id);
	foreach(keys %tags) {
		sql('insert into tags ( ticket_id, tag ) values ( ?,? )', $id, $_);
	}
	$dbh->commit;
	print redirect("$uri/$id");
	populate_search($id);
}
elsif(defined param('action') and param('action') eq 'save-contacts') {
	my $id = param('id') or die 'no id';
	my $contacts = param('contacts') || '';
	my @contacts = split /[\r\n]+/, $contacts;
	$dbh->begin_work;
	sql('delete from contacts where ticket_id = ?', $id);
	foreach(@contacts) {
		sql('insert into contacts ( ticket_id, email ) values ( ?,? )', $id, $_);
	}
	$dbh->commit;
	print redirect("$uri/$id");
}
elsif(defined param('action') and param('action') eq 'change-ticket-prio') {
	my $id = param('id') or die 'no id';
	my $prio = param('prio');
	die 'invalid prio' unless $prio =~ /^[1-5]$/;
	sql('update tickets set priority = ? where id = ?', $prio, $id);
	print redirect("$uri/$id");
}
elsif(defined param('action') and param('action') eq 'save-title-ticket') {
	my $id = param('id') or die 'no id';
	my $text = param('text') || '(sem título)';
	sql('update tickets set title = ? where id = ?', $text, $id);
	print redirect("$uri/$id");
	populate_search($id);
}
elsif(defined param('action') and param('action') eq 'get-css') {
	print header(-type => 'text/css', -expires => '+1d');
	print thecss();
}

# Lista tickets em aberto, ordenados por prioridade.
elsif($q eq '') {
	print redirect("$uri?filter=o:p");
}

# Tela de detalhes de um ticket, onde é possível efetuar-se ações como
# adição de notas, fechamento, etc.
elsif($q =~ /^\/(\d+)$/) {
	my $id = $1;
	my $head = <<'	END';
	  var panels = new Array('note', 'prio', 'tags', 'title', 'minutes', 'contacts');
	  var selectedTab = null;
	  function showPanel(tab, name)
	  {
		if (selectedTab) 
		{
		  selectedTab.style.backgroundColor = '';
		}
		selectedTab = tab;
		selectedTab.style.backgroundColor = '#D3D3D3';
		for(i = 0; i < panels.length; i++)
		{
		  document.getElementById(panels[i]).style.display = (name == panels[i]) ? 'block':'none';
		}
		return false;
	  }

	  var cron;
	  var minutes = 0;
	  var seconds = 0;
	  var title = document.title;
	  function startCron()
	  {
		  cron = setTimeout(doCron, 1000);
		  document.fminutes.bstartcron.style.visibility = 'hidden';
		  document.fminutes.bstopcron.style.visibility = 'visible';
	  }
	  function stopCron()
	  {
		  clearTimeout(cron);
		  document.fminutes.bstartcron.style.visibility = 'visible';
		  document.fminutes.bstopcron.style.visibility = 'hidden';
	  }
	  function doCron()
	  {
		  seconds++;
		  if(seconds == 60) { seconds = 0; minutes++ };
		  document.title = '[' + minutes + '\'' + seconds + '"' + '] ' + title;
		  document.fminutes.minutes.value = minutes + ( seconds / 60 );
		  cron = setTimeout(doCron, 1000);
	  }
	END

	my $r = sql('select * from tickets where id = ?', $id)->[0];
	if(not defined $r) { die "Ticket $id não existe" }
	print header(-expires => 'now');
	print start_html(-style => {'src' => $css}, 
		-title => "#$id $r->{title}", 
		-script => $head
	);
	&emit_header;
	print qq{<span class="title">Detalhe: Ticket #$id</span>},p ;
	show_ticket($r);
	if($r->{'status'} == 0) {
		print q{<table class="actions" border="0"><tr><td>};
		print q{<a class="tab" onclick="return showPanel(this, 'note');">Adicionar Nota</a> | };
		print q{<a class="tab" onclick="return showPanel(this, 'prio');">Prioridade de Ação</a> | };
		print q{<a class="tab" onclick="return showPanel(this, 'tags');">Palavras-Chave</a> | };
		print q{<a class="tab" onclick="return showPanel(this, 'title');">Título</a> | };
		print q{<a class="tab" onclick="return showPanel(this, 'minutes');">Tempo</a> | };
		print q{<a class="tab" onclick="return showPanel(this, 'contacts');">Contatos</a>};
		print q{</td></tr></table>}, br;
	}
	elsif($r->{'status'} == 1) {
		print q{<table class="actions" border="0"><tr><td>};
		print q{<a class="tab" onclick="return showPanel(this, 'tags');">Palavras-Chave</a> | };
		print q{<a class="tab" onclick="return showPanel(this, 'title');">Título</a> | };
		print q{<a class="tab" onclick="return showPanel(this, 'minutes');">Tempo</a>};
		print q{</td></tr></table>};
	}
	show_form_new_note($id);
	show_form_change_prio($id, $r->{'priority'});
	show_form_edit_tags_ticket($id);
	show_form_title_ticket($id, $r->{'title'});
	show_form_minutes_ticket($id, $r->{'status'});
	show_form_contacts_ticket($id);

	emit_footer();
}

elsif($q eq '/new-ticket') {
	print header(-expires => 'now'), start_html(-style => {'src' => $css}, 
		-title => 'Novo Ticket', -onload => 'document.f.title.focus();' );
	emit_header();
	print q{<span class="title">Novo Ticket</span>}, p;
    print q{<a name='new'></a>}, start_form(-name => 'f'),
      textfield( -name => 'title', -size => 90 ),
      hidden(
        -name     => 'action',
        -value    => 'create-new-ticket',
        -override => 1
      ),
      submit( 'submit', 'Criar' ), end_form;

	  print	p, font({-color => '#A5A5A5'}, 
		small('Digite uma descrição sucinta. Você poderá adicionar mais informações detalhadas depois.'));

	  emit_footer();
}
else { die 'invalid url' }

$dbh->disconnect;

#########################################################################################
#########################################################################################
## Funções auxiliares
#########################################################################################
#########################################################################################

sub sanitize_text {
	my $text = shift || return;
	$text =~ s/\r//sg;
	$text =~ s/&/&amp;/gs;
	$text =~ s/</&lt;/gs;
	$text =~ s/>/&gt;/gs;
	$text =~ s/\r?\n/<br>/sg;
	$text =~ s/\t/&nbsp;&nbsp;&nbsp;/sg;
	$text =~ s/(<br>){1,}$//;
	$text =~ s/#([0-9]+)/<a title="Ver Ticket #$1" href='$uri\/$1'>#$1<\/a>/sg;
	return $text;
}

sub show_form_new_note {
	my $id = shift;
	my $cont = '';
	my $contacts = join("\r\n", map {s/^/#/;$_} get_contacts_from_ticket($id));
	print q{<div class="panel" id="note" style="display: none">};
	print start_form(),
		textarea(-name => 'text', -rows=>4, -columns=>70), p
		small("Alertar os seguintes contatos por email (linhas iniciadas por # serão ignoradas):") , p ,
		textarea(-name => 'contacts', -rows=>5, -columns=>50, -default => $contacts),
		hidden(-name => 'action', -value => 'create-new-note', -override => 1),
		hidden('id', $id), p,
		submit('submit', 'Adicionar nota'),
		end_form;
	print q{</div>};
}

sub show_form_contacts_ticket {
	my $id = shift;
	my $contacts = join("\r\n", get_contacts_from_ticket($id));
	print q{<div class="panel" id="contacts" style="display: none">};
	print start_form(),
		textarea(-name => 'contacts', -rows=>5, -columns=>50, -default => $contacts), br,
		hidden(-name => 'action', -value => 'save-contacts', -override => 1),
		hidden('id', $id),
		submit('submit', 'Salvar contatos'),
		end_form;
	print q{</div>};
}

sub show_form_change_prio {
	my $id = shift; my $prio = shift;
	print q{<div class="panel" id="prio" style="display: none">};
	print qq{
		<form method="post" action="" enctype="multipart/form-data">
		<select name="prio" >};
	foreach(sort keys %priodesc) {
		if($_ == $prio) {
			print qq{<option selected="selected" value="$_">$priodesc{$_}</option>};
		}
		else {
			print qq{<option value="$_">$priodesc{$_}</option>};
		}
	}
	print qq{
		</select> <input type="hidden" name="action" 
			value="change-ticket-prio"  />
		<input type="hidden" name="id" value="$id"  />
		<input type="submit" name="submit" value="Mudar prioridade de ação" /></form>
	};
	print q{</div>};
}

sub show_form_edit_tags_ticket {
	my $id = shift;
	print q{<div class="panel" id="tags" style="display: none">};
	my $tags = join ' ', get_tags_from_ticket($id);
	print start_form(-name => 'ftag'),
		textfield(-name => 'text', -size => 70, -value=>$tags),
		hidden(-name => 'action', -value => 'save-tags-ticket', -override => 1),
		hidden('id', $id),
		submit('submit', 'Salvar palavras-chave'), p,
		font({-color => '#A5A5A5'}, 
		small('Palavras-chave podem ser utilizadas para classificar os Tickets. ',
		'Separar as palavras-chave por espaços.')),
		end_form;
	if(scalar keys %tagsdesc > 0) {
		foreach(sort keys %tagsdesc) {
			my $tag = CGI::escape($_);
			my $d = tagsdesc($_);
			print small("<a href='#' onclick='document.ftag.text.value+=\" $tag\"' title='$d->{description}' 
				class='tag' style='background-color:$d->{bgcolor};color:$d->{fgcolor};'>$_</a>"), " ";
		}
	}
	print q{</div>};
}

sub show_form_title_ticket {
	my $id = shift;
	my $title = shift;
	print q{<div class="panel" id="title" style="display: none">};
	print start_form(),
		textfield(-name => 'text', -size=>70, -value=>$title),
		hidden(-name => 'action', -value => 'save-title-ticket', -override => 1),
		hidden('id', $id),
		submit('submit', 'Salvar título'),
		end_form;
	print q{</div>};
}

sub show_form_minutes_ticket {
	my $id = shift;
	my $status = shift;
	print q{<div class="panel" id="minutes" style="display: none">};
	if($status == 0) {
		print start_form(-name => 'fminutes'),
			textfield(-name => 'minutes', -size => 10, -value=>'0'),
			hidden(-name => 'action', -value => 'register-minutes', -override => 1),
			hidden('parent', $id),
			submit('submit', 'Contabilizar minutos'),
			p, button(-name => 'bstartcron', -value => 'Iniciar Cronômetro', -onclick => 'startCron()'),
			button(-name => 'bstopcron', -value => 'Parar Cronômetro', -onclick => 'stopCron()', -style => 'visibility:hidden;'),
			end_form;
	}
	
	foreach(@{sql('select user, sum(minutes) as minutes from timetrack where ticket_id = ? and minutes > 0 group by user order by user', $id)}) {
		my $hours = sprintf('%d', $_->{'minutes'} / 60);
		my $minutes = sprintf('%02d', $_->{'minutes'} % 60);
		print p, small(b($_->{'user'}) . ' contabilizou ' . b($hours.'h'.$minutes.'m') . ' no total') . br;
	}

	print q{</div>};
}

sub populate_search {
	my $id = shift;
	my $text = '';
	my $tag = '';
	my $user = ''; # todos os usuários que alteraram o ticket
	$dbh->begin_work;
	sql('delete from search where docid = ?', $id);
	my $title = sql('select title from tickets where id = ?', $id)->[0]->{'title'};
	foreach(@{sql('select comment, user from comments where ticket_id = ?', $id)}) {
		$text .= $_->{'comment'} . ' ';
		$user .= $_->{'user'} . ' ';
	}
	foreach(@{sql('select tag from tags where ticket_id = ?', $id)}) {
		$tag .= $_->{'tag'} . ' ';
	}
	sql('insert into search (docid, title, text, tag, user) values (?,?,?,?,?)', $id, $title, $text, $tag, $user);
	$dbh->commit;
}

sub get_prio_color {
	my $prio = shift;
	my $color = '';
	if($prio == 1)    { $color = '#FF8D8F' }
	elsif($prio == 2) { $color = '#EDFF9F' }
	elsif($prio == 3) { $color = '' }
	elsif($prio == 4) { $color = '#6DF2B2' }
	elsif($prio == 5) { $color = '#9FEFF2' }
	return $color;
}

sub show_ticket_small {
	my $r = shift;
	my $bgcolor = '';
	my $priocolor = '';
	if($r->{'status'} == 0) { $priocolor = get_prio_color($r->{'priority'}) }
	else { $bgcolor = '#e1e1e1' }
	my $title = $r->{'title'} || '';
	print qq{<table class="ticket" width="100%" border="0" bgcolor="$bgcolor">};
	print qq{<tr><td width="5px" title="$priodesc{$r->{priority}}" bgcolor="$priocolor">&nbsp;</td>}; #"
	print qq{<td width="80px" valign="top">};
	my $lab = "Criado: $r->{datecreated} \nModificado: $r->{datemodified} \nAutor: $r->{user} ";
	if($r->{status} == 1) { $lab .= "\nFechado: $r->{dateclosed}" }
	print qq{<b><a class="ticketlabel" title="$lab" href="$uri/$r->{'id'}">#$r->{'id'}</a></b>}; #"
	print q{</td><td valign="top">};
	print span({-class => 'tktitle'}, $title);
	print "</td><td valign='top' align='right'>";
	print_ticket_tags($r->{'id'});
	print q{</td></tr></table>};
	#populate_search($r->{'id'});
}

sub print_ticket_tags {
	my $id = shift;
	my @tags = get_tags_from_ticket($id);
	foreach(@tags) {
		my $tag = CGI::escape($_);
		my $d = tagsdesc($_);
		print "<a href='$uri?filter=t:$tag o:p' title='$d->{description}' class='tag' style='background-color:$d->{bgcolor};color:$d->{fgcolor};'>$_</a>", " ";
	}
}

sub tagsdesc {
	my $tag = shift;
	if(not exists $tagsdesc{$tag}) {
		return { 'description' => '', 'bgcolor' => 'yellow', 'fgcolor' => 'red' }
	}
	else {
		return { 'description' => $tagsdesc{$tag}->{'description'} || '',
			'bgcolor' => $tagsdesc{$tag}->{'bgcolor'} || 'yellow',
			'fgcolor' => $tagsdesc{$tag}->{'fgcolor'} || 'red' };
	}
}

sub show_ticket {
	my $r = shift;
	my $bgcolor = '';
	my $priocolor = '';
	if($r->{'status'} == 0) { $priocolor = get_prio_color($r->{'priority'}) }
	else { $bgcolor = '#e1e1e1' }
	my $title = $r->{'title'} || '';
	print qq{<table class="ticket" width="100%" border="0" bgcolor="$bgcolor">};
	print qq{<tr><td width="5px" title="$priodesc{$r->{priority}}" bgcolor="$priocolor">&nbsp;</td>}; #"
	print qq{<td width="120px" valign="top">};
	print qq{<b><a class="ticketlabel" href="$uri/$r->{'id'}">Ticket #$r->{'id'}</a></b><br>}; #"
	my $datec = strip_date($r->{'datecreated'});
	print qq{Criado: <span title="$r->{'datecreated'}">$datec</span><br>}; #"
	if($r->{'status'} == 1) {
		my $dated = strip_date($r->{'dateclosed'});
		print qq{Fechado: <span title="$r->{'dateclosed'}">$dated</span><br>}; #"
	}
	print qq{Autor: $r->{'user'}<br>};

	print_ticket_tags($r->{'id'});

	if($r->{'status'} == 0) {
		print p, start_form(),
			hidden(-name => 'action', -value => 'close-ticket', -override => 1),
			hidden('id', $r->{'id'}),
			submit('submit', 'fechar'),
			end_form;
	}
	else {
		print p, start_form(),
			hidden(-name => 'action', -value => 'reopen-ticket', -override => 1),
			hidden('id', $r->{'id'}),
			submit('submit', 'reabrir'),
			end_form;
	}
	print q{</td><td valign="top">};
	print span({-class => 'tktitle'}, $title), p;
	foreach(@{sql('
		select *
		from (
		  select datecreated
		    , user
			, case status when \'close\' then \'fechado\' when \'reopen\' then \'reaberto\' end as comment
			, 1 as negrito
			, 0 as minutes
		  from statustrack
		  where ticket_id = ?
		  union all
		  select datecreated
		    , user
			, comment
			, 0 as negrito
			, 0 as minutes
		  from comments
		  where ticket_id = ?
		  union all
		  select datecreated
		    , user
			, minutes || \' minutos trabalhados\'
			, 1 as negrito
			, minutes
		  from timetrack
		  where ticket_id = ?
		) as t
		order by datecreated
	', $r->{'id'}, $r->{'id'}, $r->{'id'})}) {
		my $date = strip_date($_->{'datecreated'});
		my $negrito1 = ''; my $negrito2 = '';
		if($_->{'negrito'} == 1) { $negrito1 = '<b><i>'; $negrito2 = '</i></b>'; }
		print br, $negrito1, qq{<b title="$_->{'datecreated'}">$date - $_->{'user'}: </b>}; #"
		if($_->{'minutes'} > 0) {
			my $minutes = $_->{'minutes'};
			my $hours = sprintf("%d", $minutes / 60);
			$minutes = sprintf("%02d", $minutes % 60);
			print "${hours}h${minutes}m trabalhados.";
		}  
		else { print sanitize_text($_->{'comment'}) }
		print $negrito2;
	}
	print q{</td></tr></table><p>};
}
 
# Retorna todas as palavras-chave associadas a um ticket.
sub get_tags_from_ticket {
	my $id = shift;
	my @tags = map { $_ = $_->{'tag'} }
	@{ sql( 'select tag from tags where ticket_id = ?', $id ) };
	return sort @tags;
}

sub get_contacts_from_ticket {
	my $id = shift;
	my @contacts = map { $_ = $_->{'email'} }
	@{ sql( 'select email from contacts where ticket_id = ?', $id ) };
	return sort @contacts;
}

sub get_title_from_ticket {
	my $id = shift;
	my $title = @{ sql( 'select title from tickets where id = ?', $id ) }->[0]->{'title'};
	return $title;
}

# Emite o cabeçalho padrão das páginas, com menu no topo e barra de pesquisa.
sub emit_header {
	my $search = '';
	if(defined param('filter')) { $search = param('filter') }
	elsif($q =~ /^\/(\d+)$/) { $search = "#" . $1 }
	print qq{
		<table border="0" align="right">
		<tr>
		<td class="topmenu">
			olá <b>$user</b>! 
			<a href='$uri' accesskey='A' title="alt-shift-a">abertos</a>
			| <a href='$uri?filter=T o:m l:100' title="alt-shift-m" accesskey='M'>modificados</a>
			| <a href='$uri/new-ticket' accesskey='N' title='alt-shift-n'>novo</a>
		</td> <tr></tr> <td align=right>
		<form method="post" action="$uri" enctype="multipart/form-data">
			<input type="text" name="filter" size="25" accesskey='S' value="$search" title="alt-shift-s">
			<input type="submit" name="filter" value="filtrar" />
		</form>
		</td></tr></table>
	};
}

# Emite rodapé com nome do sistema e versão.
sub emit_footer {
	print qq{<p><small><font color="gray"><div align="right">sistema
		<a href="http://zanardo.org/ticket.html">ticket</a> versão $VERSION</small></div></font>};
}

# Recebe "2005-05-05 05:05:05" e converte para "2005-05-05".
sub strip_date {
	my $datetime = shift;
	$datetime =~ s/^(\d{4}-\d{2}-\d{2}) .*$/$1/;
	return $datetime;
}

# Executa uma sentença SQL, opcionalmente com parâmetros, e retorna uma arrayref
# de hashrefs com os resultados.
sub sql {
	my $sql = shift;
	my $sth = $dbh->prepare($sql) or die $dbh->errstr;
	$sth->execute(@_) or die $dbh->errstr;
	return unless $sql =~ /^[\s\n\r\t]*SELECT/i;
	my $result = [ ];
	while(my $r = $sth->fetchrow_hashref) {
		push @$result, $r;
	}
	return $result;
}

sub send_email {
	my $id = shift;
	my $title = shift;
	my $user = shift;
	my $contacts = shift;
	my $note = shift;
	my $date = strftime('%Y-%m-%d %H:%M:%S', localtime);

	my $text = "[$date] ($user): $note\r\n\r\n\r\n\r\n-- Este é um e-mail automático enviado pelo sistema ticket.";

	foreach(grep {!/^#/} split("[\r\n]+", $contacts)) {
		my $mail = MIME::Lite->new(
			From => $from_mail,
			To => $_,
			Subject => encode('MIME-Header', "#$id - $title"),
			Data => $text
		);
		$mail->send('smtp', $smtp_mail) or die $!;
	}
}

sub thecss {
	return <<'	CSS';
	body { margin: 1em 2em 2em 2em; font-family: Verdana, Arial, sans-serif; font-size: 9pt; background-color: #F1F3F4; }
	.tab { color: #0000EE; text-decoration: underline; font-family: Verdana, Arial, sans-serif; font-size: 8pt; }
	a:link { color: #0000EE; }
	a:visited { color: #0000EE; }
	a:active { color: #0000EE; }
	a:hover { color: #FF0000; }
	input, textarea, select, submit { font-family: Verdana, Arial, sans-serif; font-size: 8pt; background-color: #F1F3F4; border: 1px solid #336699; }
	.topmenu { font-family: Arial, sans-serif; font-size: 9pt; }
	.title { font-family: "Gill Sans", "Trebuchet MS", Verdana, sans-serif; font-size: 24pt; font-weight: normal; }
	.tags { border: 1px dotted #336699; font-family: Verdana, Arial, sans-serif; font-size: 8pt; }
	.actions { } 
	.ticket { font-family: Verdana, Arial, sans-serif; font-size: 10px; border: 1px solid #ffffff; }
	.ticketlabel { font-size: 12px; }
	.tag { text-decoration: none; font-weight: bold; }
	.tktitle { font-family: "Verdana"; font-size: 12px; font-weight: bold; }
	CSS
}

# CREATE TABLE comments ( id integer primary key not null, ticket_id integer not null references ticket ( id ), datecreated datetime not null default ( datetime('now', 'localtime') ), user text not null, comment text not null );
# CREATE TABLE contacts ( ticket_id integer not null, email text not null );
# CREATE VIRTUAL TABLE search using fts3 ( title, text, tag, user );
# CREATE TABLE 'search_content'(docid INTEGER PRIMARY KEY, 'c0title', 'c1text', 'c2tag', 'c3user');
# CREATE TABLE 'search_segdir'(level INTEGER,idx INTEGER,start_block INTEGER,leaves_end_block INTEGER,end_block INTEGER,root BLOB,PRIMARY KEY(level, idx));
# CREATE TABLE 'search_segments'(blockid INTEGER PRIMARY KEY, block BLOB);
# CREATE TABLE statustrack ( id integer primary key not null, ticket_id integer not null references ticket ( id ), datecreated datetime not null default ( datetime('now', 'localtime') ), user text not null, status text not null );
# CREATE TABLE tags ( ticket_id integer not null references ticket ( id ), tag text not null );
# CREATE TABLE tagsdesc ( tag text not null primary key, description text, fgcolor text, bgcolor text );
# CREATE TABLE tickets ( id integer primary key not null, title text not null, status integer not null default ( 0 ), priority integer not null default ( 3 ), datecreated datetime not null default ( datetime('now', 'localtime') ), datemodified datetime not null default ( datetime('now', 'localtime') ), dateclosed datetime, user text not null );
# CREATE TABLE timetrack ( id integer primary key not null, ticket_id integer not null references ticket ( id ), datecreated datetime not null default ( datetime('now', 'localtime') ), user text not null, minutes integer not null );
# CREATE INDEX idx_comments_ticket_id on comments ( ticket_id );
# CREATE INDEX idx_contacts_ticket_id on contacts ( ticket_id );
# CREATE INDEX idx_statustrack_ticket_id on statustrack ( ticket_id );
# CREATE INDEX idx_tags_tag on tags ( tag );
# CREATE INDEX idx_tags_ticket_id on tags ( ticket_id );
# CREATE INDEX idx_tickets_datecreated on tickets ( datecreated desc );
# CREATE INDEX idx_tickets_datemodified on tickets ( datemodified desc );
# CREATE INDEX idx_tickets_priority on tickets ( priority desc );
# CREATE INDEX idx_tickets_status on tickets ( status );
# CREATE INDEX idx_timetrack_ticket_id on timetrack ( ticket_id );
