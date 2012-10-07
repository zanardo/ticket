BEGIN;

CREATE TABLE tickets (
	id integer NOT NULL PRIMARY KEY,
	title text NOT NULL,
	status integer NOT NULL DEFAULT ( 0 ),
	priority integer NOT NULL DEFAULT ( 3 ),
	datecreated timestamp NOT NULL DEFAULT ( datetime('now', 'localtime') ),
	datemodified timestamp NOT NULL DEFAULT ( datetime('now', 'localtime') ),
	dateclosed timestamp,
	user text NOT NULL
);
CREATE INDEX idx_tickets_status ON tickets ( status );

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
	description text NOT NULL,
	fgcolor text NOT NULL,
	bgcolor text NOT NULL
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

CREATE TABLE contacts (
	ticket_id integer NOT NULL,
	email text NOT NULL
);
CREATE INDEX idx_contacts_ticket_id ON contacts ( ticket_id );

CREATE TABLE users (
	username text NOT NULL PRIMARY KEY,
	password text NOT NULL,
	is_admin int
);

CREATE TABLE sessions (
	session_id text NOT NULL PRIMARY KEY,
	date_login timestamp NOT NULL DEFAULT ( datetime('now', 'localtime') ),
	username text NOT NULL
);

CREATE TABLE config (
	key text NOT NULL PRIMARY KEY,
	value text NOT NULL
);

CREATE VIRTUAL TABLE search USING fts3 ( text );

INSERT INTO users ( username, password, is_admin )
VALUES ( 'admin', 'd033e22ae348aeb5660fc2140aec35850c4da997', 1 );

INSERT INTO config ( key, value ) VALUES ( 'mail.smtp', '' );
INSERT INTO config ( key, value ) VALUES ( 'mail.from', '' );

COMMIT;
