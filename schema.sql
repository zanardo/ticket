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
