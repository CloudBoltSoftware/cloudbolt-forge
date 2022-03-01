#!/bin/bash -e

# Original script taken from http://stackoverflow.com/questions/34569373/install-mysql-community-server-5-7-via-bash-shell-script-in-centos-7-x64

mysqlRootPass="{{ server.database_root_password }}"

service mysqld stop && yum remove -y mysql-server && rm -rf /var/lib/mysql && rm -rf /var/log/mysqld.log && rm -rf /etc/my.cnf

echo ' -> Installing mysql server (community edition)'
yum install -y https://repo.mysql.com/mysql80-community-release-el7.rpm
rpm --import https://repo.mysql.com/RPM-GPG-KEY-mysql-2022
yum install -y mysql-server

echo '
[mysqld]

socket=/var/lib/mysql/mysql.sock
skip-grant-tables
bind-address=127.0.0.1

[client]

socket=/var/lib/mysql/mysql.sock' >> /etc/my.cnf

/sbin/chkconfig --levels 235 mysqld on
service mysqld start

tempRootDBPass="`grep 'temporary.*root@localhost' /var/log/mysqld.log | tail -n 1 | sed 's/.*root@localhost: //'`"

service mysqld stop
rm -rf /var/lib/mysql/*logfile*
service mysqld start

mysql -u root <<-EOSQL
    UPDATE mysql.user SET authentication_string=null WHERE User='root';
    FLUSH PRIVILEGES;
EOSQL

mysql -u root --connect-expired-password -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH caching_sha2_password BY '${mysqlRootPass}';"

sed -i 's/skip-grant-tables/#skip-grant-tables/g' /etc/my.cnf
sed -i 's/bind-address=127.0.0.1/#bind-address=127.0.0.1/g' /etc/my.cnf

service mysqld restart
mysql -u root --password="$mysqlRootPass" <<-EOSQL
    DELETE FROM mysql.user WHERE User='';
    DROP DATABASE IF EXISTS test; 
    DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%'; 
    DELETE FROM mysql.user where user != 'mysql.sys'; 
    CREATE USER 'root'@'%' IDENTIFIED BY '${mysqlRootPass}';
    GRANT ALL ON *.* TO 'root'@'%' WITH GRANT OPTION;
    FLUSH PRIVILEGES;
EOSQL
echo " -> MySQL server installation completed."