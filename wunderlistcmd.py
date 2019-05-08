#!/usr/bin/env python3
""" Provides an easy Wunderlist lists and tasks manipulator """

import argparse
import sys
import configparser
import pathlib
import os
import logging
import json
from datetime import datetime, date
import wunderpy2

def get_args():
    """ Returns parsed arguments """

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command')

    list_parser = subparsers.add_parser('list', aliases=['ls'])
    list_parser.set_defaults(command='list')
    list_subparsers = list_parser.add_subparsers(dest='kind')
    list_lists_parser = list_subparsers.add_parser('lists', aliases=['ls'])
    list_lists_parser.set_defaults(kind='lists')
    list_tasks_parser = list_subparsers.add_parser('tasks', aliases=['ts'])
    list_tasks_parser.set_defaults(kind='tasks')
    list_tasks_parser.add_argument('in_list')
    list_tasks_parser.add_argument('-c', '--completed',\
            action='store_const', const=True)
    list_tasks_parser.add_argument('-p', '--period', nargs=2)

    create_parser = subparsers.add_parser('create', aliases=['cr'])
    create_parser.set_defaults(command='create')
    create_subparsers = create_parser.add_subparsers(dest='kind')
    create_task_parser = create_subparsers.add_parser('task', aliases=['ts'])
    create_task_parser.set_defaults(kind='task')
    create_task_parser.add_argument('in_list')
    create_task_parser.add_argument('title')
    create_task_parser.add_argument('--due_date', '-d')
    create_list_parser = create_subparsers.add_parser('list', aliases=['ls'])
    create_list_parser.set_defaults(kind='list')
    create_list_parser.add_argument('title')

    show_parser = subparsers.add_parser('show', aliases=['sh'])
    show_parser.set_defaults(command='show')
    show_subparsers = show_parser.add_subparsers(dest='kind')
    show_task_parser = show_subparsers.add_parser('task', aliases=['ts'])
    show_task_parser.set_defaults(kind='task')
    show_task_parser.add_argument('task_id')

    done_parser = subparsers.add_parser('done', aliases=['dn'])
    done_parser.set_defaults(command='done')
    done_parser.set_defaults(kind='task')
    done_parser.add_argument('task_id')

    delete_parser = subparsers.add_parser('delete')
    delete_parser.set_defaults(kind='task')
    delete_parser.add_argument('task_id')

    update_parser = subparsers.add_parser('update', aliases=['upd'])
    update_parser.set_defaults(command='update')
    update_parser.set_defaults(kind='task')
    update_parser.add_argument('task_id')
    update_parser.add_argument('--title', '-t')
    update_parser.add_argument('--due_date', '-d')

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(-1)

    return args


def compare_dates(tsk_date, beg_date, end_date):
    """ Returns True if tsk_date is between beg_date and end_date """

    return bool(beg_date <= tsk_date <= end_date)


def get_date_obj(raw_date_str):
    """ Returns a date object created from the given raw_date_str """

    date_sep_lst = [char for char in raw_date_str if not char.isdigit()]
    try:
        date_str = raw_date_str.replace(date_sep_lst[0], '-')
    except IndexError:
        pass
    if len(date_sep_lst) == 2:
        date_str = raw_date_str
    elif len(date_sep_lst) == 1:
        date_str = str(datetime.today().year) + '-' + raw_date_str
    elif not date_sep_lst:
        date_str = str(datetime.today().year) + '-' + \
                str(datetime.today().month) + '-' +  raw_date_str
    date_format = '%Y-%m-%d'
    date_y = datetime.strptime(date_str, date_format).year
    date_m = datetime.strptime(date_str, date_format).month
    date_d = datetime.strptime(date_str, date_format).day

    return date(date_y, date_m, date_d)


def get_date_str(raw_date_str):
    """ Returns a date in string format """

    date_obj = get_date_obj(raw_date_str)
    year = date_obj.year
    month = date_obj.month
    day = date_obj.day

    return '{}-{}-{}'.format(year, month, day)

def get_proper_color(args, date_obj):
    """ Returns the color string based on the given date
    (implemented only for to do tasks so far) """

    if not args.completed:
        if date_obj < date.today():
            color = COLORS['red']
        elif date_obj == date.today():
            color = COLORS['orange']
        elif date_obj.isocalendar()[1] == date.today().isocalendar()[1]:
            color = COLORS['yellow']
        else:
            color = COLORS['endcolor']
    else:
        color = COLORS['endcolor']

    return color


class WunderlistClient():
    """ Client for Wunderlist Class """

    logger = logging.getLogger()

    def __init__(self):
        self.api = wunderpy2.WunderApi()
        self._load_config()
        self.client = self.api.get_client(self.access_token, self.client_id)
        args = get_args()
        self._process_args(args)


    def _process_args(self, args):
        """ Calls the proper function based on given args """

        fname = args.command + '_' + args.kind
        self.func = getattr(self, fname, None)
        if self.func:
            self.func(args)
        else:
            print('{} function does not exist'.format(fname))


    def _load_config(self, cfile=str(pathlib.Path.home()) + '/.wunderlistcmd'):
        """ Loads the configuration from ~/.wunderlistcmd """

        if not os.path.isfile(cfile):
            self.logger.error("error: can't read %s file", cfile)
            sys.exit(-1)

        config = configparser.ConfigParser()
        config.read(cfile)
        try:
            self.access_token = config['general']['access_token']
        except KeyError:
            errmsg = "error: can't find access_token at 'general' section"
            self.logger.error(errmsg)
            sys.exit(-1)
        try:
            self.client_id = config['general']['client_id']
        except KeyError:
            self.logger.error("error: can't find client_id at 'general' section")
            sys.exit(-1)


    def _get_lists(self):
        """ Returns the lists from the server """

        return self.client.get_lists()


    def _get_list_id_from_title(self, title):
        """ Returns the list id based on the given title list """

        list_id = [l['id'] for l in self._get_lists() if l['title'].lower()
                   == title.lower()]
        return list_id[0]


    def _get_tasks(self, args):
        """ Returns the tasks from a given list  """

        try:
            list_id = int(args.in_list)
        except ValueError:
            list_id = self._get_list_id_from_title(args.in_list)
        return self.client.get_tasks(list_id, completed=args.completed)


    def list_tasks(self, args):
        """ Prints a formatted table of tasks based on given criteria """

        tasks = []

        for task in self._get_tasks(args):

            if args.completed:
                # gets task's completion date
                date_title = 'completed_at'
                task_date = get_date_obj(task[date_title][0:10])
            else:
                # gets task's due date
                date_title = 'due_date'
                try:
                    task_date = get_date_obj(task[date_title])
                except KeyError:
                    task_date = ''

            if args.period:
                # filters tasks whose date are between the given dates from user
                try:
                    if compare_dates(task_date,\
                            get_date_obj(args.period[0]),\
                            get_date_obj(args.period[1])):
                        tasks.append((task['id'], task_date, task['title']))
                except TypeError:
                    pass
            elif args.completed:
                # if the user wants the completed tasks without informing a
                # period, filter only tasks with dates between current week
                task_week_no = task_date.isocalendar()[1]
                if task_date.year == date.today().year and \
                        task_week_no == date.today().isocalendar()[1]:
                    tasks.append((task['id'], task_date, task['title']))
            else:
                # if the user wants all tasks to do
                tasks.append((task['id'], task_date, task['title']))

        if args.completed:
            tasks = sorted(tasks, key=lambda x: (x[1], x[2]))
        else:
            tasks = sorted(tasks, key=lambda x: (x[1] == "", x[1], x[2]))

        len_date = 10
        if len(date_title) > len_date:
            len_date = len(date_title)

        # prints the title
        print('{}{} | {} | {}{}'.format(COLORS['bold'], 'id'.center(10),\
                date_title.center(len_date), 'title', COLORS['endcolor']))

        color = COLORS['endcolor']
        for task in tasks:
            try:
                color = get_proper_color(args, task[1])
            except TypeError:
                pass
            try:
                task_date = task[1].strftime("%Y-%m-%d")
            except AttributeError:
                task_date = ''
            print('{}{} | {} | {}{}'.format(color, task[0],\
                    task_date.center(len_date), task[2], COLORS['endcolor']))
            color = COLORS['endcolor']


    def list_lists(self, args):
        """ Prints all lists and their ids """

        for i in self._get_lists():
            print('{} | {}'.format(i['id'], i['title']))


    def create_list(self, args):
        """ Creates a list """

        self.client.create_list(args.title)


    def create_task(self, args):
        """ Creates a task """

        try:
            list_id = int(args.in_list)
        except ValueError:
            list_id = self._get_list_id_from_title(args.in_list)

        try:
            due_date = get_date_str(args.due_date)
            self.client.create_task(list_id, args.title, due_date=due_date)
        except TypeError:
            self.client.create_task(list_id, args.title)


    def show_task(self, args):
        """ Prints a task's details """

        print(json.dumps(self.client.get_task(args.task_id), indent=1))


    def update_task(self, args):
        """ Updates a task attributes """

        revision = self.client.get_task(args.task_id)['revision']
        if args.title:
            self.client.update_task(args.task_id, revision, title=args.title)
        if args.due_date:
            due_date = get_date_str(args.due_date)
            self.client.update_task(args.task_id, revision, due_date=due_date)

    def done_task(self, args):
        """ Sets a task as done """

        revision = self.client.get_task(args.task_id)['revision']
        self.client.update_task(args.task_id, revision, completed=True)

    def delete_task(self, args):
        """ Deletes a task from a given list """

        revision = self.client.get_task(args.task_id)['revision']
        self.client.delete_task(args.task_id, revision)

if __name__ == '__main__':
    COLORS = {'endcolor': '\033[0m', 'bold': '\033[1m', 'red': '\033[31m',\
            'orange': '\033[91m', 'yellow': '\033[33m'}
    CLIENT = WunderlistClient()
