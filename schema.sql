CREATE TABLE tickets (
	id integer primary key not null,
	title text not null,
	status integer not null default ( 0 ),
	priority integer not null default ( 3 ),
	datecreated datetime not null default ( datetime('now', 'localtime') ),
	datemodified datetime not null default ( datetime('now', 'localtime') ),
	dateclosed datetime,
	user text not null
);

CREATE TABLE comments ( 
	id integer primary key not null,
	ticket_id integer not null references ticket ( id ),
	datecreated datetime not null default ( datetime('now', 'localtime') ),
	user text not null,
	comment text not null
);

CREATE TABLE statustrack ( id integer primary key not null,
	ticket_id integer not null references ticket ( id ),
	datecreated datetime not null default ( datetime('now', 'localtime') ),
	user text not null,
	status text not null
);

CREATE TABLE tags (
	ticket_id integer not null references ticket ( id ),
	tag text not null
);

CREATE TABLE timetrack (
	id integer primary key not null,
	ticket_id integer not null references ticket ( id ),
	datecreated datetime not null default ( datetime('now', 'localtime') ),
	user text not null,
	minutes integer not null
);

CREATE TABLE tagsdesc (
	tag text not null primary key,
	description text,
	fgcolor text,
	bgcolor text
);
