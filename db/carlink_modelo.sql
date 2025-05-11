-- MySQL dump 10.13  Distrib 8.0.38, for Win64 (x86_64)
--
-- Host: 127.0.0.1    Database: carlink
-- ------------------------------------------------------
-- Server version	8.0.39

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `modelo`
--

DROP TABLE IF EXISTS `modelo`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `modelo` (
  `id_modelo` int NOT NULL AUTO_INCREMENT,
  `nome` varchar(50) DEFAULT NULL,
  `fk_id_marca` int DEFAULT NULL,
  PRIMARY KEY (`id_modelo`),
  KEY `fk_id_marca` (`fk_id_marca`),
  CONSTRAINT `modelo_ibfk_1` FOREIGN KEY (`fk_id_marca`) REFERENCES `marca` (`id_marca`)
) ENGINE=InnoDB AUTO_INCREMENT=89 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `modelo`
--

LOCK TABLES `modelo` WRITE;
/*!40000 ALTER TABLE `modelo` DISABLE KEYS */;
INSERT INTO `modelo` VALUES (1,'MDX',1),(2,'RDX',1),(3,'TLX',1),(4,'Giulia',2),(5,'Stelvio',2),(6,'A3',3),(7,'A4',3),(8,'Q5',3),(9,'Série 3',4),(10,'X5',4),(11,'X3',4),(12,'Encore',5),(13,'Enclave',5),(14,'Han',6),(15,'Dolphin',6),(16,'Song Plus',6),(17,'Escalade',7),(18,'XT5',7),(19,'Onix',8),(20,'Cruze',8),(21,'S10',8),(22,'300',9),(23,'Pacifica',9),(24,'C4 Cactus',10),(25,'C3',10),(26,'Charger',11),(27,'Durango',11),(28,'Mobi',12),(29,'Argo',12),(30,'Toro',12),(31,'Fiesta',13),(32,'Ranger',13),(33,'Mustang',13),(34,'Sierra',14),(35,'Yukon',14),(36,'Civic',15),(37,'HR-V',15),(38,'CR-V',15),(39,'HB20',16),(40,'Creta',16),(41,'Tucson',16),(42,'Q50',17),(43,'QX60',17),(44,'F-Pace',18),(45,'XE',18),(46,'Renegade',19),(47,'Compass',19),(48,'Wrangler',19),(49,'Sportage',20),(50,'Seltos',20),(51,'Carnival',20),(52,'Range Rover Evoque',21),(53,'Discovery Sport',21),(54,'RX',22),(55,'ES',22),(56,'CX-5',23),(57,'3',23),(58,'Classe C',24),(59,'GLC',24),(60,'Cooper',25),(61,'Countryman',25),(62,'Outlander',26),(63,'L200',26),(64,'Kicks',27),(65,'Sentra',27),(66,'208',28),(67,'2008',28),(68,'Cayenne',29),(69,'Macan',29),(70,'1500',30),(71,'2500',30),(72,'Kwid',31),(73,'Duster',31),(74,'Sandero',31),(75,'Forester',32),(76,'Outback',32),(77,'Jimny',33),(78,'Vitara',33),(79,'Model 3',34),(80,'Model Y',34),(81,'Corolla',35),(82,'Hilux',35),(83,'RAV4',35),(84,'Gol',36),(85,'T-Cross',36),(86,'Saveiro',36),(87,'XC60',37),(88,'XC90',37);
/*!40000 ALTER TABLE `modelo` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-05-09 12:17:17
