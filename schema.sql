--
-- PostgreSQL database dump
--

SET statement_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = off;
SET check_function_bodies = false;
SET client_min_messages = warning;
SET escape_string_warning = off;

--
-- Name: plpgsql; Type: PROCEDURAL LANGUAGE; Schema: -; Owner: postgres
--

CREATE OR REPLACE PROCEDURAL LANGUAGE plpgsql;


ALTER PROCEDURAL LANGUAGE plpgsql OWNER TO postgres;

SET search_path = public, pg_catalog;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: comments; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE comments (
    id integer NOT NULL,
    ticket_id integer NOT NULL,
    datecreated timestamp(0) without time zone DEFAULT now() NOT NULL,
    "user" character varying(50),
    comment text NOT NULL
);


ALTER TABLE public.comments OWNER TO postgres;

--
-- Name: comments_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE comments_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.comments_id_seq OWNER TO postgres;

--
-- Name: comments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE comments_id_seq OWNED BY comments.id;


--
-- Name: contacts; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE contacts (
    ticket_id integer NOT NULL,
    email text NOT NULL
);


ALTER TABLE public.contacts OWNER TO postgres;

--
-- Name: statustrack; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE statustrack (
    id integer NOT NULL,
    ticket_id integer NOT NULL,
    datecreated timestamp(0) without time zone DEFAULT now() NOT NULL,
    "user" character varying(50),
    status character varying(50) NOT NULL
);


ALTER TABLE public.statustrack OWNER TO postgres;

--
-- Name: statustrack_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE statustrack_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.statustrack_id_seq OWNER TO postgres;

--
-- Name: statustrack_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE statustrack_id_seq OWNED BY statustrack.id;


--
-- Name: tags; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE tags (
    ticket_id integer NOT NULL,
    tag character varying(50) NOT NULL
);


ALTER TABLE public.tags OWNER TO postgres;

--
-- Name: tagsdesc; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE tagsdesc (
    tag character varying(50) NOT NULL,
    description text,
    fgcolor character varying(50),
    bgcolor character varying(50)
);


ALTER TABLE public.tagsdesc OWNER TO postgres;

--
-- Name: tickets; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE tickets (
    id integer NOT NULL,
    title text NOT NULL,
    status smallint DEFAULT 0 NOT NULL,
    priority smallint DEFAULT 3 NOT NULL,
    datecreated timestamp(0) without time zone DEFAULT now() NOT NULL,
    datemodified timestamp(0) without time zone DEFAULT now() NOT NULL,
    dateclosed timestamp(0) without time zone,
    "user" character varying(50)
);


ALTER TABLE public.tickets OWNER TO postgres;

--
-- Name: tickets_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE tickets_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.tickets_id_seq OWNER TO postgres;

--
-- Name: tickets_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE tickets_id_seq OWNED BY tickets.id;


--
-- Name: timetrack; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE timetrack (
    id integer NOT NULL,
    ticket_id integer NOT NULL,
    datecreated timestamp(0) without time zone DEFAULT now() NOT NULL,
    "user" character varying(50),
    minutes numeric(15,2) NOT NULL
);


ALTER TABLE public.timetrack OWNER TO postgres;

--
-- Name: timetrack_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE timetrack_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.timetrack_id_seq OWNER TO postgres;

--
-- Name: timetrack_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE timetrack_id_seq OWNED BY timetrack.id;


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE comments ALTER COLUMN id SET DEFAULT nextval('comments_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE statustrack ALTER COLUMN id SET DEFAULT nextval('statustrack_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE tickets ALTER COLUMN id SET DEFAULT nextval('tickets_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE timetrack ALTER COLUMN id SET DEFAULT nextval('timetrack_id_seq'::regclass);


--
-- Name: comments_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY comments
    ADD CONSTRAINT comments_pkey PRIMARY KEY (id);


--
-- Name: statustrack_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY statustrack
    ADD CONSTRAINT statustrack_pkey PRIMARY KEY (id);


--
-- Name: tagsdesc_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY tagsdesc
    ADD CONSTRAINT tagsdesc_pkey PRIMARY KEY (tag);


--
-- Name: tickets_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY tickets
    ADD CONSTRAINT tickets_pkey PRIMARY KEY (id);


--
-- Name: timetrack_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY timetrack
    ADD CONSTRAINT timetrack_pkey PRIMARY KEY (id);


--
-- Name: idx_comments_fulltext; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX idx_comments_fulltext ON comments USING gin (to_tsvector('portuguese'::regconfig, ((comment || ' '::text) || ("user")::text)));


--
-- Name: idx_comments_ticket_id; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX idx_comments_ticket_id ON comments USING btree (ticket_id);


--
-- Name: idx_statustrack_ticket_id; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX idx_statustrack_ticket_id ON statustrack USING btree (ticket_id);


--
-- Name: idx_tags_tag; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX idx_tags_tag ON tags USING btree (tag);


--
-- Name: idx_tags_ticket_id; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX idx_tags_ticket_id ON tags USING btree (ticket_id);


--
-- Name: idx_tickets_dateclosed; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX idx_tickets_dateclosed ON tickets USING btree (dateclosed DESC);


--
-- Name: idx_tickets_datecreated; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX idx_tickets_datecreated ON tickets USING btree (datecreated DESC);


--
-- Name: idx_tickets_datemodified; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX idx_tickets_datemodified ON tickets USING btree (datemodified DESC);


--
-- Name: idx_tickets_fulltext; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX idx_tickets_fulltext ON tickets USING gin (to_tsvector('portuguese'::regconfig, ((title || ' '::text) || ("user")::text)));


--
-- Name: idx_tickets_priority; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX idx_tickets_priority ON tickets USING btree (priority DESC);


--
-- Name: idx_tickets_status; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX idx_tickets_status ON tickets USING btree (status);


--
-- Name: idx_timetrack_ticket_id; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX idx_timetrack_ticket_id ON timetrack USING btree (ticket_id);


--
-- Name: comments_ticket_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY comments
    ADD CONSTRAINT comments_ticket_id_fkey FOREIGN KEY (ticket_id) REFERENCES tickets(id);


--
-- Name: contacts_ticket_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY contacts
    ADD CONSTRAINT contacts_ticket_id_fkey FOREIGN KEY (ticket_id) REFERENCES tickets(id);


--
-- Name: statustrack_ticket_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY statustrack
    ADD CONSTRAINT statustrack_ticket_id_fkey FOREIGN KEY (ticket_id) REFERENCES tickets(id);


--
-- Name: tags_ticket_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY tags
    ADD CONSTRAINT tags_ticket_id_fkey FOREIGN KEY (ticket_id) REFERENCES tickets(id);


--
-- Name: timetrack_ticket_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY timetrack
    ADD CONSTRAINT timetrack_ticket_id_fkey FOREIGN KEY (ticket_id) REFERENCES tickets(id);


--
-- Name: public; Type: ACL; Schema: -; Owner: postgres
--

REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM postgres;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO PUBLIC;


--
-- PostgreSQL database dump complete
--

