BEGIN;

CREATE TABLE tickets (
	id integer NOT NULL PRIMARY KEY,
	title text NOT NULL,
	status integer NOT NULL DEFAULT ( 0 ),
	priority integer NOT NULL DEFAULT ( 3 ),
	datecreated text NOT NULL,
	datemodified text NOT NULL,
	dateclosed text,
	user text NOT NULL
);

CREATE TABLE comments (
	id integer NOT NULL PRIMARY KEY,
	ticket_id integer NOT NULL,
	datecreated text NOT NULL,
	user text NOT NULL,
	comment text NOT NULL
);

CREATE TABLE tags (
	ticket_id integer NOT NULL,
	tag text NOT NULL
);

CREATE TABLE tagsdesc (
	tag text NOT NULL,
	description text NOT NULL,
	fgcolor text NOT NULL,
	bgcolor text NOT NULL
);

CREATE TABLE timetrack (
	id integer NOT NULL PRIMARY KEY,
	ticket_id integer NOT NULL,
	datecreated text NOT NULL,
	user text NOT NULL,
	minutes float NOT NULL
);

CREATE TABLE statustrack (
	id integer NOT NULL PRIMARY KEY,
	ticket_id integer NOT NULL,
	datecreated text NOT NULL,
	user text NOT NULL,
	status text NOT NULL
);

CREATE TABLE contacts (
	ticket_id integer NOT NULL,
	email text NOT NULL
);

CREATE TABLE users (
	username text NOT NULL PRIMARY KEY,
	password text NOT NULL,
	is_admin int
);

CREATE TABLE sessions (
	session_id text NOT NULL PRIMARY KEY,
	date_login text NOT NULL DEFAULT ( datetime('now', 'localtime') ),
	username text NOT NULL
);

COMMIT;
