import mysql.connector
from config import DB

def connect_db():
    return mysql.connector.connect(
        host=DB["host"],
        user=DB["user"],
        password=DB["password"],
        database=DB["database"],
    )

def query_recruitments(cursor):
    cursor.execute("""
        SELECT DISTINCT Project_ID, Country, code, Comments, min_age, max_age, Gender
        FROM project_recruitment_request 
        JOIN countries ON countries.id = country
        WHERE is_stopped = 0
    """)
    return cursor.fetchall()

def query_specs(cursor, sql_list):
    cursor.execute(f"""
        SELECT Project_ID, Country, Code, Days_in_Field, Initial_Launch_Date,cpi, invoice_currency
        FROM project_specs 
        JOIN project on project.id = project_id
        JOIN countries ON countries.id = country
        WHERE CONCAT(CAST(project_id AS CHAR), ' ', CAST(country AS CHAR)) IN ({sql_list})
    """)
    return cursor.fetchall()

def query_completes(cursor, project_id_list):
    # project_id_list já deve estar formatada sem aspas (inteiros)
    cursor.execute(f"""
        SELECT Project_ID, Code, COUNT(*) AS Completes
        FROM (
            SELECT panelist_id, Project_ID
            FROM panelist_project 
            WHERE project_id IN ({project_id_list}) AND status = 1
        ) AS t 
        JOIN panelist ON panelist.id = t.panelist_id 
        JOIN countries ON countries.id = country
        GROUP BY 1,2
    """)
    return cursor.fetchall()

def query_spend_last4months(cursor):
    cursor.execute("""
        SELECT DATE(date) AS date, recruit_source, code AS country, SUM(spend) AS spend
        FROM adspend_daily 
        JOIN countries ON countries.id = country
        WHERE date BETWEEN DATE_SUB(CURDATE(), INTERVAL 4 MONTH) AND CURDATE() - INTERVAL 1 DAY
        GROUP BY 1,2,3
    """)
    return cursor.fetchall()


def query_panelists_last4months(cursor):
    cursor.execute("""
        SELECT DATE(joindate) AS date, recruit_source, code AS country, COUNT(panelist.id) AS Panelists
        FROM panelist 
        JOIN countries ON countries.id = country
        WHERE joindate >= DATE_SUB(CURDATE(), INTERVAL 4 MONTH)
        GROUP BY 1,2,3
    """)
    return cursor.fetchall()

def query_conversion_rate(cursor):
    cursor.execute("""
        select 	panelist.ID, Country, Code, Gender, timestampdiff(year, dob, date_start) Age, count(*) Starts, sum(case when status = 1 then 1 else 0 end) Completes
        from panelist_project 
        join panelist on panelist.id = panelist_project.panelist_id
        join countries on countries.id = panelist.country
        where date(joindate) = date(date_start) and date_start > date_sub(current_date, interval 2 month)
        group by 1,2,3,4
    """)
    return cursor.fetchall()

def query_latam(cursor, panelist_id_list):
    placeholders = ', '.join(['%s'] * len(panelist_id_list))
    query = f"""
        SELECT Panelist_ID ID, cast(regionid as int) "Region ID"
        FROM ows_production.latam_panelist
        WHERE panelist_id IN ({placeholders})
    """
    cursor.execute(query, panelist_id_list)
    return cursor.fetchall()
