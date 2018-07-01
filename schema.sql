begin;

create table users (
	username text not null primary key,
	password text not null,
	is_admin int default (0),
	email text,
	name text
);

create table tickets (
	id integer not null primary key,
	title text not null,
	status integer not null default (0) check (status between 0 and 1),
	priority integer not null default (3) check (priority between 1 and 5),
	datecreated timestamp not null default (datetime('now', 'localtime')),
	datemodified timestamp not null default (datetime('now', 'localtime')),
	datedue timestamp,
	dateclosed timestamp,
	username text not null references users (username),
	admin_only integer not null default (0)
);
create index idx_tickets_status on tickets (status);

create table comments (
	id integer not null primary key,
	ticket_id integer not null references tickets (id),
	datecreated timestamp not null default (datetime('now', 'localtime')),
	username text not null references users (username),
	comment text not null
);
create index idx_comments_ticket_id on comments (ticket_id);

create table tags (
	ticket_id integer not null references tickets (id),
	tag text not null
);
create index idx_tags_ticket_id on tags (ticket_id);

create table tagsdesc (
	tag text not null primary key,
	description text,
	fgcolor text,
	bgcolor text
);

create table timetrack (
	id integer not null primary key,
	ticket_id integer not null references tickets (id),
	datecreated timestamp not null default (datetime('now', 'localtime')),
	username text not null references users (username),
	minutes real not null
);
create index idx_timetrack_ticket_id on timetrack (ticket_id);

create table statustrack (
	id integer not null primary key,
	ticket_id integer not null references tickets (id),
	datecreated timestamp not null default (datetime('now', 'localtime')),
	username text not null references users (username),
	status text not null
);
create index idx_statustrack_ticket_id on statustrack (ticket_id);

create table sessions (
	session_id text not null primary key,
	date_login timestamp not null default (datetime('now', 'localtime')),
	username text not null references users (username)
);

create table files (
	id integer not null primary key,
	ticket_id integer not null references tickets (id),
	name text not null,
	datecreated timestamp not null default (datetime('now', 'localtime')),
	username text not null references users (username),
	size integer not null check (size >= 0),
	contents blob not null
);
create index idx_files_ticket_id on files (ticket_id);

create table dependencies (
	ticket_id integer not null references tickets (id),
	blocks integer not null references tickets (id),
	primary key(ticket_id, blocks)
);

insert into users (username, password, is_admin)
values ('admin', 'd033e22ae348aeb5660fc2140aec35850c4da997', 1);

commit;
