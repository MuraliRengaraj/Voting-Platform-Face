create database votingFustion;

use votingFustion;

CREATE TABLE admin (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL
);
-- Admin SQL Statements:
INSERT INTO admin (username, password) VALUES ('admin1', '$2b$12$CnPy1xGwm8ZSITDxQqispeBdiWL8sYwDRO4xbqhkqEvJTPdiidE7C'); 
-- usernama = admin1
-- password = admin


CREATE TABLE face_encodings (
    voter_id VARCHAR(255) PRIMARY KEY,
    encoding LONGBLOB NOT NULL
);

CREATE TABLE users (
	voter_id VARCHAR(100) PRIMARY KEY,
    voter_name VARCHAR(255) NOT NULL,
	voter_phone_number VARCHAR(15) NOT NULL,
    voter_father_name VARCHAR(255) NOT NULL,
	voter_Gender VARCHAR(20) NOT NULL,
    voter_dob VARCHAR(20) NOT NULL,
    attempt1 BOOLEAN DEFAULT FALSE,
    attempt2 BOOLEAN DEFAULT FALSE,
    attempt3 BOOLEAN DEFAULT FALSE
);

-- drop table user_authentication;
-- drop table users;
-- drop table face_encodings;

CREATE TABLE user_authentication (
    voter_id VARCHAR(100),
    is_authenticated BOOLEAN NOT NULL,
    authentication_date DATETIME NOT NULL,
    FOREIGN KEY (voter_id) REFERENCES users(voter_id)
);


select * from user_authentication;
select * from users;
select * from face_encodings;

DELETE FROM user_authentication WHERE  voter_id="YZT2";
delete from users where voter_name="abdul";
delete from face_encodings where voter_id="YZT2";

UPDATE users SET attempt1=False, attempt2=False, attempt3=False WHERE voter_name="RAI";
UPDATE users SET attempt1=False, attempt2=False, attempt3=False WHERE voter_name="abdul";



-- IF Error Code: 1175. You are using safe update mode and you tried to update a table ...
SET SQL_SAFE_UPDATES = 0;

UPDATE users SET attempt1=True, attempt2=True, attempt3=False WHERE voter_name="abdul"
