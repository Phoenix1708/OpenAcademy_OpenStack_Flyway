import threading
from oslo.config import cfg

__author__ = 'hydezhang'

import MySQLdb
import base64
from DBUtils.PooledDB import PooledDB
import logging

LOG = logging.getLogger(__name__)

db_pool = None


def create_db_pool(db_name=None):
    credentials = get_db_credentials()

    db_name = str(cfg.CONF.DATABASE.db_name) if db_name is None else db_name
    credentials.update({'db': db_name})
    global db_pool
    mutex = threading.Lock()
    mutex.acquire()
    if db_pool is None:
        db_pool = PooledDB(MySQLdb, 100, **credentials)
    mutex.release()


def get_db_credentials():
    password = cfg.CONF.DATABASE.mysql_password
    password = base64.b64decode(password)
    credentials = {'host': str(cfg.CONF.DATABASE.host),
                   'user': str(cfg.CONF.DATABASE.user),
                   'passwd': str(password)}
    return credentials


def connect(with_db, db_name=None):
    # preparing database credentials
    """

    :param with_db: flag to indicate whether to connect to
    a particular database or not
    """

    if with_db:
        db = db_pool.connection()
    else:
        credentials = get_db_credentials()
        db = MySQLdb.connect(**credentials)

    return db


def connect_openstack_db(host, db_name):
    credentials = {'host': host,
                   'user': 'root',
                   'passwd': 'password',
                   'db': db_name}
    db = MySQLdb.connect(**credentials)
    return db

#TODO: print table name in exception message for all functions
#TODO: that handle exceptions
def read_openstack_record(host, db_name, table_name, columns, where_dict,
                          close):
    # establish connection
    db = connect_openstack_db(host, db_name)
    cursor = get_cursor(db)

    filter_str = build_where_string(where_dict)
    # build columns list
    columns_str = ', '.join(columns)

    if len(where_dict.keys()) > 0:
        query = "SELECT {0} FROM {1} WHERE {2}".format(columns_str,
                                                       table_name,
                                                       filter_str)
    else:
        query = "SELECT {0} FROM {1} ".format(columns_str, table_name)

    data = None
    try:
        cursor.execute(query)
        data = cursor.fetchall()
    except MySQLdb.Error, e:
        LOG.error("MySQL error: {}".format(e))
        db.rollback()

    if close:
        db.close()

    return data


def update_openstack_record(host, db_name, table_name, set_dict, where_dict,
                            close):
    db = connect_openstack_db(host, db_name)
    cursor = get_cursor(db)

    # building "SET" string
    set_str = ''
    for key in set_dict.keys():
        if key != set_dict.keys()[0]:
            set_str += ', '
        set_str += str(key) + " = '" + str(set_dict[key]) + "'"

    filter_str = build_where_string(where_dict)

    query = "UPDATE {0} SET {1} WHERE {2}" \
        .format(table_name, set_str, filter_str)

    try:
        cursor.execute(query)
        db.commit()
    except MySQLdb.Error, e:
        LOG.error("MySql error: {}".format(e))
        db.rollback()

    if close:
        db.close()


def insert_openstack_record(host, db_name, table_name, values, close):
    # establish connection
    db = connect_openstack_db(host, db_name)
    cursor = get_cursor(db)

    for item in values:
        # preparing sql statement
        columns = item.keys()
        columns_str = columns[0]
        values_str = add_quotes(item[columns[0]])
        for i in xrange(1, len(columns)):
            columns_str += ', ' + columns[i]
            values_str += ', ' + add_quotes(item[columns[i]])

        query = "INSERT INTO {0} ({1}) VALUES ({2})"\
            .format(table_name, columns_str, values_str)

        try:
            cursor.execute(query)
            db.commit()
        except MySQLdb.Error, e:
            LOG.error("MySql error - INSERT: {}".format(e))
            db.rollback()

    if close:
        db.close()


def delete_openstack_record(host, db_name, table_name, where_dict, close):
    # establish connection
    db = connect_openstack_db(host, db_name)
    cursor = get_cursor(db)

    where_string = build_where_string(where_dict)
    query = "DELETE FROM {0} WHERE {1}".format(table_name, where_string)
    try:
        cursor.execute(query)
        db.commit()
    except MySQLdb.Error, e:
        LOG.error("MySQL error - DELETE SOME: {}".format(e))
        db.rollback()

    if close:
        db.close()


def get_cursor(db):
    return db.cursor()


def check_db_existed(db_name):
    db = connect(False)
    cursor = get_cursor(db)
    table_name = add_quotes(db_name)
    query_check = "SHOW DATABASES LIKE {}".format(table_name)
    result = cursor.execute(query_check)
    return True if result else False


def delete_database(db_name):
    db = connect(False)
    cursor = get_cursor(db)

    result = check_db_existed(db_name)

    if not result:
        LOG.info("Database {} does not exist".format(db_name))
        cursor.close()
        db.close()
        return

    query_delete = 'DROP DATABASE {} '.format(db_name)
    try:
        cursor.execute(query_delete)
        db.commit()
        db.close()
    except MySQLdb.Error, e:
        print("MySQL error - Database deleting: {}".format(e))
        db.rollback()


def create_database(db_name):
    db = connect(False)
    cursor = get_cursor(db)

    result = check_db_existed(db_name)

    if result:
        LOG.info("Database {} already exists".format(db_name))
        cursor.close()
        db.close()
        return

    query_create = 'CREATE DATABASE IF NOT EXISTS {} '.format(db_name)
    try:
        cursor.execute(query_create)
        db.commit()
        db.close()
    except MySQLdb.Error, e:
        print("MySQL error - Database creation: {}".format(e))
        db.rollback()


def create_table(table_name, columns, close):
    """
    function to create database table
    :param table_name: name of the table to be created
    :param columns: columns of the table
    :param close: flag to indicate whether to close db connection
    """
    # establish connection
    db = connect(True)
    cursor = get_cursor(db)

    query = "CREATE TABLE IF NOT EXISTS {0} ({1}) ".format(table_name, columns)

    try:
        cursor.execute(query)
        db.commit()
    except MySQLdb.Error, e:
        LOG.error("MySql error - Table creation: {}".format(e))
        db.rollback()

    if close:
        db.close()


def insert_record(table_name, values, close):
    """
    function to do table insert
    :param table_name: name of the table to be effected
    :param values: list of dictionaries of column and value pair
    :param close: flag to indicate whether to close db connection
    """
    # establish connection
    db = connect(True)
    cursor = get_cursor(db)

    for item in values:
        # preparing sql statement
        columns = item.keys()
        columns_str = columns[0]
        values_str = add_quotes(item[columns[0]])
        for i in xrange(1, len(columns)):
            columns_str += ', ' + columns[i]
            values_str += ', ' + add_quotes(item[columns[i]])

        query = "INSERT INTO {0} ({1}) VALUES ({2})"\
            .format(table_name, columns_str, values_str)

        try:
            cursor.execute(query)
            db.commit()
        except MySQLdb.Error, e:
            LOG.error("MySql error - INSERT: {}".format(e))
            db.rollback()

    if close:
        db.close()


def update_table(table_name, set_dict, where_dict, close):
    # establish connection
    """function to do update record in table

    :param table_name: name of the table to be effected
    :param set_dict: set dictionary
    :param where_dict: where dictionary
    :param close: flag to indicate whether to close db connection
    """
    db = connect(True)
    cursor = get_cursor(db)

    # building "SET" string
    first_key = set_dict.keys()[0]
    first_value = set_dict[first_key]
    set_str = str(first_key) + " = " + add_quotes(first_value)
    for key in set_dict.keys():
        set_str += ', ' + str(key) + " = " + add_quotes(str(set_dict[key]))

    filter_str = build_where_string(where_dict)

    query = "UPDATE {0} SET {1} WHERE {2}" \
        .format(table_name, set_str, filter_str)

    try:
        cursor.execute(query)
        db.commit()
    except MySQLdb.Error, e:
        LOG.error("MySql error - UPDATE: {}".format(e))
        db.rollback()

    if close:
        db.close()


def build_where_string(where_dict):
    # build "WHERE" string
    # TODO: needs to allow more complicated filter string e.g with OR, != etc.
    filter_str = ''
    for key in where_dict.keys():
        if key != where_dict.keys()[0]:
            filter_str += ' AND '
        filter_str += str(key) + " = '" + str(where_dict[key]) + "'"

    return filter_str


def read_record(table_name, columns, where_dict, close):
    """
    function that implements SELECT statement
    :param table_name: name of the table to read data from
    :param close: flag to indicate whether to close db connection
    :param columns: columns from which the data is selected
    :param where_dict: where dictionary
    """
    # establish connection
    db = connect(True)
    cursor = get_cursor(db)

    filter_str = build_where_string(where_dict) if where_dict else None
    # build columns list
    columns_str = ', '.join(columns)

    if filter_str:
        query = "SELECT {0} FROM {1} WHERE {2}".format(columns_str, table_name,
                                                       filter_str)
    else:
        query = "SELECT {0} FROM {1} ".format(columns_str, table_name)

    data = None
    try:
        cursor.execute(query)
        data = cursor.fetchall()
    except MySQLdb.Error, e:
        LOG.error("MySQL error - SELECT: {}".format(e))
        db.rollback()

    if data and len(data) == 0:
        print("no migration record found for {0} where {1}"
              .format(table_name, filter_str))

    if close:
        db.close()

    return data


def delete_all_data(table_name):
    """
    function that delete all data from a table
    """
    # establish connection
    db = connect(True)
    cursor = get_cursor(db)

    query = "DELETE FROM {0}".format(table_name)
    try:
        cursor.execute(query)
        db.commit()
    except MySQLdb.Error, e:
        LOG.error("MySQL error - DELETE ALL: {}".format(e))
        db.rollback()

    db.close()


def delete_record(table_name, where_dict):
    """
    function that delete all data from a table
    """
    # establish connection
    db = connect(True)
    cursor = get_cursor(db)
    where_string = build_where_string(where_dict)

    if where_dict and len(where_dict.keys()) > 0:
        query = "DELETE FROM {0} WHERE {1}".format(table_name, where_string)
    else:
        query = "DELETE FROM {}".format(table_name)

    try:
        cursor.execute(query)
        db.commit()
    except MySQLdb.Error, e:
        LOG.error("MySQL error - DELETE SOME: {}".format(e))
        db.rollback()

    db.close()


def check_table_exist(table_name):
    """
    function that checks whether a table exists
    """
    # establish connection
    db = connect(True)
    cursor = get_cursor(db)

    table_name = "'" + table_name + "'"
    query = "SHOW TABLES LIKE {}".format(table_name)
    result = cursor.execute(query)

    db.close()
    if result:
        return True

    return False


def check_record_exist(table_name, where_dict):
    db = connect(True)
    cursor = get_cursor(db)

    filter_str = build_where_string(where_dict)
    query = "SELECT * FROM {0} WHERE {1}".format(table_name, filter_str)

    result = cursor.execute(query)

    db.close()
    if result:
        return True

    return False


def add_quotes(string):
    return "'" + str(string) + "'"