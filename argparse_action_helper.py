#!/usr/bin/python
# *************************************************
# Copyright (c) 2016  ARM Ltd (or its subsidiaries)
# *************************************************

import argparse
import os


class StoreInputDir(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        prospective_dir = values
        if not os.path.isdir(prospective_dir):
            raise argparse.ArgumentTypeError('dir: "{0}" is not a valid path'.format(prospective_dir))
        elif not os.access(prospective_dir, os.R_OK):
            raise argparse.ArgumentTypeError('dir: "{0}" is not a readable dir'.format(prospective_dir))
        setattr(namespace, self.dest, os.path.abspath(prospective_dir))


class StoreOutputDir(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        prospective_dir = values
        if not os.path.isdir(prospective_dir):
            try:
                os.makedirs(prospective_dir)
            except os.error as e:
                raise argparse.ArgumentTypeError('dir: {0} cannot be created: {1}'.format(prospective_dir, str(e)))
        setattr(namespace, self.dest, os.path.abspath(prospective_dir))


class StoreValidFile(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        prospective_file = values
        if not os.path.isfile(prospective_file):
            raise argparse.ArgumentTypeError('file: "{0}" not found'.format(prospective_file))
        if not os.access(prospective_file, os.R_OK):
            raise argparse.ArgumentTypeError('file: "{0}" is not a readable file'.format(prospective_file))
        setattr(namespace, self.dest, os.path.abspath(prospective_file))


class AppendValidFile(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        prospective_file = values
        if not os.path.isfile(prospective_file):
            raise argparse.ArgumentTypeError('file: "{0}" not found'.format(prospective_file))
        if not os.access(prospective_file, os.R_OK):
            raise argparse.ArgumentTypeError('file: "{0}" is not a readable file'.format(prospective_file))
        if not getattr(namespace, self.dest):
            setattr(namespace, self.dest, [])
        getattr(namespace, self.dest).append(os.path.abspath(prospective_file))
