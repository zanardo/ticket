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
	ticket_id integer NOT NULL REFERENCES tickets ( id ),
	datecreated text NOT NULL,
	user text NOT NULL,
	comment text NOT NULL
);

CREATE TABLE tags (
	ticket_id integer NOT NULL REFERENCES tickets ( id ),
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
	ticket_id integer NOT NULL REFERENCES tickets ( id ),
	datecreated text NOT NULL,
	user text NOT NULL,
	minutes float NOT NULL
);

CREATE TABLE statustrack (
	id integer NOT NULL PRIMARY KEY,
	ticket_id integer NOT NULL REFERENCES tickets ( id ),
	datecreated text NOT NULL,
	user text NOT NULL,
	status text NOT NULL
);

CREATE TABLE contacts (
	ticket_id integer NOT NULL REFERENCES tickets ( id ),
	email text NOT NULL
);

COMMIT;
