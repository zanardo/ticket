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
CREATE INDEX tickets_dateclosed on tickets ( dateclosed desc );
CREATE INDEX tickets_datecreated on tickets ( datecreated desc );
CREATE INDEX tickets_datemodified on tickets ( datemodified desc );
CREATE INDEX tickets_priority on tickets ( priority );
CREATE INDEX tickets_status on tickets ( status );
CREATE INDEX tickets_user on tickets ( user );

CREATE TABLE comments ( 
	id integer primary key not null,
	ticket_id integer not null references ticket ( id ),
	datecreated datetime not null default ( datetime('now', 'localtime') ),
	user text not null,
	comment text not null
);
CREATE INDEX comments_ticket_id on comments ( ticket_id );

CREATE TABLE statustrack ( id integer primary key not null,
	ticket_id integer not null references ticket ( id ),
	datecreated datetime not null default ( datetime('now', 'localtime') ),
	user text not null,
	status text not null
);
CREATE INDEX statustrack_ticket_id on statustrack ( ticket_id );

CREATE TABLE tags (
	ticket_id integer not null references ticket ( id ),
	tag text not null
);
CREATE INDEX tags_ticket_id on tags ( ticket_id );

CREATE TABLE timetrack (
	id integer primary key not null,
	ticket_id integer not null references ticket ( id ),
	datecreated datetime not null default ( datetime('now', 'localtime') ),
	user text not null,
	minutes integer not null
);
CREATE INDEX timetrack_ticket_id on timetrack ( ticket_id );

CREATE TABLE tagsdesc (
	tag text not null primary key,
	description text,
	fgcolor text,
	bgcolor text
);
