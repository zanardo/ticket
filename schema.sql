BEGIN;

CREATE TABLE tickets (
	id integer NOT NULL PRIMARY KEY,
	title text NOT NULL,
	status integer NOT NULL DEFAULT ( 0 ),
	priority integer NOT NULL DEFAULT ( 3 ),
	datecreated timestamp NOT NULL DEFAULT ( datetime('now', 'localtime') ),
	datemodified timestamp NOT NULL DEFAULT ( datetime('now', 'localtime') ),
	datedue timestamp,
	dateclosed timestamp,
	user text NOT NULL,
	admin_only integer NOT NULL DEFAULT ( 0 )
);
CREATE INDEX idx_tickets_status ON tickets ( status );
CREATE INDEX idx_tickets_datedue ON tickets ( datedue );

CREATE TABLE comments (
	id integer NOT NULL PRIMARY KEY,
	ticket_id integer NOT NULL,
	datecreated timestamp NOT NULL DEFAULT ( datetime('now', 'localtime') ),
	user text NOT NULL,
	comment text NOT NULL
);
CREATE INDEX idx_comments_ticket_id ON comments ( ticket_id );

CREATE TABLE tags (
	ticket_id integer NOT NULL,
	tag text NOT NULL
);
CREATE INDEX idx_tags_ticket_id ON tags ( ticket_id );

CREATE TABLE tagsdesc (
	tag text NOT NULL,
	description text,
	fgcolor text,
	bgcolor text
);

CREATE TABLE timetrack (
	id integer NOT NULL PRIMARY KEY,
	ticket_id integer NOT NULL,
	datecreated timestamp NOT NULL DEFAULT ( datetime('now', 'localtime') ),
	user text NOT NULL,
	minutes float NOT NULL
);
CREATE INDEX idx_timetrack_ticket_id ON timetrack ( ticket_id );

CREATE TABLE statustrack (
	id integer NOT NULL PRIMARY KEY,
	ticket_id integer NOT NULL,
	datecreated timestamp NOT NULL DEFAULT ( datetime('now', 'localtime') ),
	user text NOT NULL,
	status text NOT NULL
);
CREATE INDEX idx_statustrack_ticket_id ON statustrack ( ticket_id );

CREATE TABLE users (
	username text NOT NULL PRIMARY KEY,
	password text NOT NULL,
	is_admin int,
	email text,
	name text
);

CREATE TABLE sessions (
	session_id text NOT NULL PRIMARY KEY,
	date_login timestamp NOT NULL DEFAULT ( datetime('now', 'localtime') ),
	username text NOT NULL
);

CREATE TABLE files (
	id integer NOT NULL PRIMARY KEY,
	ticket_id integer NOT NULL,
	name text NOT NULL,
	datecreated timestamp NOT NULL DEFAULT ( datetime('now', 'localtime') ),
	user text NOT NULL,
	size integer NOT NULL,
	contents blob NOT NULL
);
CREATE INDEX idx_files_ticket_id ON files ( ticket_id );

CREATE TABLE dependencies (
	ticket_id integer NOT NULL,
	blocks integer NOT NULL,
	PRIMARY KEY(ticket_id, blocks)
);

CREATE VIRTUAL TABLE search USING fts3 ( text );

INSERT INTO users ( username, password, is_admin )
VALUES ( 'admin', 'd033e22ae348aeb5660fc2140aec35850c4da997', 1 );

COMMIT;
