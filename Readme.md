# microservice-booking  

Веб-приложение поиска и бронирования парковочных мест на основе микросервисной архитектуры.  

## Основной функционал  

### ⚙️ Микросервисная архитектура  
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?logo=fastapi)](https://fastapi.tiangolo.com/) [![Apache Kafka](https://img.shields.io/badge/Apache_Kafka-231F20?logo=apache-kafka)](https://kafka.apache.org/) [![Pydantic](https://img.shields.io/badge/Pydantic-92000B?logo=python)](https://docs.pydantic.dev/)
- Асинхронный backend на FastAPI  
- Обмен сообщениями через Apache Kafka  
- Валидация данных с помощью Pydantic

### 🔐 Безопасность  
[![JWT](https://img.shields.io/badge/JSON_Web_Token-1a1a1a?logo=json-web-token)](https://jwt.io/)
- Аутентификация по JWT  
- Хеширование паролей (bcrypt)  
- Ролевая модель (админ/пользователь)  

### 📊 Аналитика  
- Топ популярных парковок  
- Среднее время бронирования мест  
- Расчет дневной выручки  

### 🗃️ Работа с данными  
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-1a1a1a?logo=sqlalchemy)](https://docs.sqlalchemy.org/en/20/) [![MS SQL Server](https://img.shields.io/badge/MS_SQL_Server-CC2927?logo=microsoft-sql-server)](https://www.microsoft.com/sql-server/) 
- ORM-запросы через SQLAlchemy 2.0 с AsyncSession
- Аналитические SQL-запросы  

### 🌐 Клиентская часть   
[![Jinja2](https://img.shields.io/badge/Jinja2-B41717?style=flat-square&logo=jinja&logoColor=white)](https://jinja.palletsprojects.com/) ![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=flat-square&logo=html5&logoColor=white) ![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=flat-square&logo=css3&logoColor=white) ![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat-square&logo=javascript&logoColor=black)
- Динамическая генерация страниц через Jinja2  
- Отзывчивый интерфейс на HTML5/CSS3  
- AJAX-запросы и валидация форм на JavaScript

## 🚀 Запуск  

### Требования  
Python 3.8-3.12  

### Установка  
```bash
git clone https://github.com/Refret28/microservice-booking.git
cd microservice-booking
pip install -r requirements.txt
```

### Конфигурация

Перед запуском необходимо заполнить конфигурационные файлы собственными значениями. Вам нужно отредактировать следующие файлы:

- microservice-booking/app/config.ini
- microservice-booking/app/payments/config.ini

Также следует отредактировать `kafka_start.bat`, указав корректные пути к вашей установке Kafka. 
Ознакомиться с полной устновкой **Apach Kafka** и **Zookeeper** можно в данной статье: [Apache Kafka для чайников](https://habr.com/ru/articles/496182/)