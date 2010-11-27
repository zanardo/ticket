-- MySQL dump 10.11
--
-- Host: localhost    Database: ticket
-- ------------------------------------------------------
-- Server version	5.0.84

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `comments`
--

DROP TABLE IF EXISTS `comments`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `comments` (
  `id` bigint(20) unsigned NOT NULL auto_increment,
  `ticket_id` int(11) NOT NULL,
  `datecreated` datetime NOT NULL,
  `user` varchar(50) NOT NULL,
  `comment` text NOT NULL,
  PRIMARY KEY  (`id`),
  UNIQUE KEY `id` (`id`),
  KEY `comments_ticket_id` (`ticket_id`)
) ENGINE=InnoDB AUTO_INCREMENT=17 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `search`
--

DROP TABLE IF EXISTS `search`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `search` (
  `docid` int(11) NOT NULL,
  `title` text,
  `tag` text,
  `user` text,
  `text` text,
  PRIMARY KEY  (`docid`),
  FULLTEXT KEY `content` (`title`,`tag`,`user`,`text`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `statustrack`
--

DROP TABLE IF EXISTS `statustrack`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `statustrack` (
  `id` bigint(20) unsigned NOT NULL auto_increment,
  `ticket_id` int(11) NOT NULL,
  `datecreated` datetime NOT NULL,
  `user` varchar(50) NOT NULL,
  `status` text NOT NULL,
  PRIMARY KEY  (`id`),
  UNIQUE KEY `id` (`id`),
  KEY `statustrack_ticket_id` (`ticket_id`)
) ENGINE=InnoDB AUTO_INCREMENT=23 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tags`
--

DROP TABLE IF EXISTS `tags`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `tags` (
  `ticket_id` int(11) NOT NULL,
  `tag` varchar(50) NOT NULL,
  KEY `tags_ticket_id` (`ticket_id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tagsdesc`
--

DROP TABLE IF EXISTS `tagsdesc`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `tagsdesc` (
  `tag` varchar(50) NOT NULL,
  `description` text,
  `fgcolor` varchar(50) default NULL,
  `bgcolor` varchar(50) default NULL,
  PRIMARY KEY  (`tag`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tickets`
--

DROP TABLE IF EXISTS `tickets`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `tickets` (
  `id` bigint(20) unsigned NOT NULL auto_increment,
  `title` text NOT NULL,
  `status` int(11) NOT NULL default '0',
  `priority` int(11) NOT NULL default '3',
  `datecreated` datetime NOT NULL,
  `datemodified` datetime NOT NULL,
  `dateclosed` datetime default NULL,
  `user` varchar(50) NOT NULL,
  PRIMARY KEY  (`id`),
  UNIQUE KEY `id` (`id`),
  KEY `tickets_dateclosed` (`dateclosed`),
  KEY `tickets_datecreated` (`datecreated`),
  KEY `tickets_datemodified` (`datemodified`),
  KEY `tickets_priority` (`priority`),
  KEY `tickets_status` (`status`),
  KEY `tickets_user` (`user`)
) ENGINE=InnoDB AUTO_INCREMENT=37 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `timetrack`
--

DROP TABLE IF EXISTS `timetrack`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `timetrack` (
  `id` bigint(20) unsigned NOT NULL auto_increment,
  `ticket_id` int(11) NOT NULL,
  `datecreated` datetime NOT NULL,
  `user` varchar(50) NOT NULL,
  `minutes` int(11) NOT NULL,
  PRIMARY KEY  (`id`),
  UNIQUE KEY `id` (`id`),
  KEY `timetrack_ticket_id` (`ticket_id`)
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2010-11-26 22:14:51
