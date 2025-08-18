import psycopg2

session = psycopg2.connect(
    # database="plm2.0",
    # user="postgres",
    # password="123456",
    database="plm_db",
    user="plm",
    password="123456",
    host="10.5.69.41",
    port="2345",

)

print(session)
