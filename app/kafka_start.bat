rd /s /q "D:/kafka_2.13-3.8.1/logs-txt"
rd /s /q "D:/kafka_2.13-3.8.1/zookeeper-data"
start D:/kafka_2.13-3.8.1/bin/windows/zookeeper-server-start.bat D:/kafka_2.13-3.8.1/config/zookeeper.properties
timeout 5
start D:/kafka_2.13-3.8.1/bin/windows/kafka-server-start.bat D:/kafka_2.13-3.8.1/config/server.properties
"D:/kafka_2.13-3.8.1/bin/windows/kafka-topics.bat" --create --topic payment_topic --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
