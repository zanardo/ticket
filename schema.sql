BEGIN;

CREATE TABLE users (
	username text NOT NULL PRIMARY KEY,
	password text NOT NULL,
	email text NOT NULL,
	is_admin integer NOT NULL,
	is_blocked integer NOT NULL
);

CREATE TABLE sessions (
	id text NOT NULL PRIMARY KEY,
	dtcreated text NOT NULL,
	username text NOT NULL REFERENCES users ( username )
);

CREATE TABLE tickets (
	id integer NOT NULL PRIMARY KEY,
	title text NOT NULL,
	status text NOT NULL,
	dtcreated text NOT NULL,
	dtmodified text NOT NULL,
	dtclosed text,
	usercreated text NOT NULL REFERENCES users ( username ),
	usermodified text NOT NULL REFERENCES users ( username ),
	userclosed text REFERENCES users ( username )
);

CREATE TABLE comments (
	id integer NOT NULL PRIMARY KEY,
	ticket_id integer NOT NULL REFERENCES tickets ( id ),
	dtcreated text NOT NULL,
	usercreated text NOT NULL REFERENCES users ( username ),
	comment text NOT NULL
);

CREATE TABLE tags (
	id integer NOT NULL PRIMARY KEY,
	ticket_id integer NOT NULL REFERENCES tickets ( id ),
	tag text NOT NULL,
	tagvalue text NOT NULL
);

CREATE TABLE timetrack (
	id integer NOT NULL PRIMARY KEY,
	ticket_id integer NOT NULL REFERENCES tickets ( id ),
	dtcreated text NOT NULL,
	usercreated text NOT NULL REFERENCES users ( username ),
	minutes float NOT NULL
);

CREATE TABLE files (
	id integer NOT NULL PRIMARY KEY,
	ticket_id integer NOT NULL REFERENCES tickets ( id ),
	dtcreated text NOT NULL,
	usercreated text NOT NULL REFERENCES users ( username ),
	filename text NOT NULL,
	filestoredname text NOT NULL
);

ROLLBACK;
