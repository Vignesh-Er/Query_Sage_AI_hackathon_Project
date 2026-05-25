import pytest
from app.orm_detector import detect_orm

def test_django_orm_detection():
    sql = "SELECT T1.id, T1.name FROM auth_user T1 WHERE T1.is_active = true LIMIT 21"
    assert detect_orm(sql) == "django"

def test_sqlalchemy_orm_detection():
    sql = "SELECT anon_1.id FROM (SELECT users.id FROM users) AS anon_1 WHERE anon_1.id = :param_1"
    assert detect_orm(sql) == "sqlalchemy"

def test_prisma_orm_detection():
    sql = "SELECT json_agg(t1.__prisma_data__) FROM (SELECT * FROM users) AS t1"
    assert detect_orm(sql) == "prisma"

def test_sequelize_orm_detection():
    sql = "SELECT User.id, Posts.title FROM User LEFT JOIN Posts ON User.id = Posts->UserId"
    assert detect_orm(sql) == "sequelize"

def test_hibernate_orm_detection():
    sql = "SELECT user0_.id, user0_.name FROM users user0_ WHERE user0_.active = true"
    assert detect_orm(sql) == "hibernate"

def test_plain_sql_returns_none():
    sql = "SELECT id, name FROM users WHERE active = true AND email = 'test@example.com'"
    assert detect_orm(sql) is None
