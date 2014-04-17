__author__ = 'hydezhang'

from utils.db_base import *


def initialise_flavor_mapping():
    table_name = "flavors"

    if not check_table_exist(table_name):
        columns = '''id INT NOT NULL AUTO_INCREMENT,
                     src_flavor_name VARCHAR(32) NOT NULL,
                     src_uuid VARCHAR(128) NOT NULL,
                     src_cloud VARCHAR(128) NOT NULL,
                     dst_flavor_name VARCHAR(32) NOT NULL,
                     dst_uuid VARCHAR(128) NOT NULL,
                     dst_cloud VARCHAR(128) NOT NULL,
                     PRIMARY KEY(id, src_uuid)
                  '''
        create_table(table_name, columns, True)
        return


def record_flavor_migrated(flavor_details):
    """function to insert the detail of
    flavor, which has been migrated, into database

    :param flavor_details: a list of dict which stores relevant data of
    migrated flavor
    """
    table_name = "flavors"
    values_to_insert = []
    for f_details in flavor_details:
        value_to_insert = "NULL,'" \
                          + f_details["src_flavor_name"] + "','" \
                          + f_details["src_uuid"] + "','" \
                          + f_details["src_cloud"] + "','" \
                          + f_details["dst_flavor_name"] + "','" \
                          + f_details["dst_uuid"] + "','" \
                          + f_details["dst_cloud"] + "'"

        values_to_insert.append(value_to_insert)

    insert_record(table_name, values_to_insert, True)


def get_migrated_flavor(values):
    """function to return detail of flavor migration
    :param values: flavor id on source cloud and cloud name that
    used to filter data
    :return: flavor migrate detail
    """
    # parameters for "SELECT"
    table_name = "flavors"
    columns = ["*"]
    filters = {"src_flavor_name": values[0],
               "src_uuid": values[1],
               "src_cloud": values[2]}

    data = read_record(table_name, columns, filters, True)

    if not data or len(data) == 0:
        print("no migration record found for flavor {0} in cloud {1}"
              .format(add_quotes(values[0]),
                      add_quotes(values[2])))
        return None
    elif len(data) > 1:
        print("multiple migration records found for " +
              "flavor {0} from in cloud {1}"
              .format(add_quotes(values[0]),
                      add_quotes(values[2])))
        return None

    # should be only one row
    flavor_data = {'src_flavor_name': data[0][1],
                   'src_uuid': data[0][2],
                   'src_cloud': data[0][3],
                   'dst_flavor_name': data[0][4],
                   'dst_uuid': data[0][5],
                   'dst_cloud': data[0][6]}
    return flavor_data


def delete_migration_record(values):
    """function to delete a flavor migration record in database

    :param values: relevant data of flavor migration record
    which is used to filter data
    """
    table_name = "flavors"
    record_filter = {'src_flavor_name': values[0],
                     'src_uuid': values[1],
                     'src_cloud': values[2]}

    delete_record(table_name, record_filter)