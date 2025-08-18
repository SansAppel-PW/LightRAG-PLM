import psycopg2

# 小海
# session = psycopg2.connect(
#     database="plm_db",
#     user="plm",
#     password="123456",
#     host="10.5.69.41",
#     port="5432",
#
# )

# plm2.0 问答

session = psycopg2.connect(
    database="plmqa_db",
    user="plmqa",
    password="123456",
    host="10.5.69.41",
    port="2347",

)
print(session)
