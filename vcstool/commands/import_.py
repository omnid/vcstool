from __future__ import print_function

import argparse
import os
import sys
import yaml

from vcstool.clients import vcstool_clients
from vcstool.executor import ansi, execute_jobs, output_results

from .command import Command, existing_dir


class ImportCommand(Command):

    command = 'import'
    help = 'Import the list of repositories'

    def __init__(self, args, url, version=None):
        super(ImportCommand, self).__init__(args)
        self.url = url
        self.version = version


def get_parser():
    parser = argparse.ArgumentParser(description='Import the list of repositories', prog='vcs import')
    group = parser.add_argument_group('Common parameters')
    group.add_argument('--debug', action='store_true', default=False, help='Show debug messages')
    group = parser.add_argument_group('"import" command parameters')
    group.add_argument('path', nargs='?', type=existing_dir, default=os.curdir, help='Base path to clone repositories to')
    group.add_argument('--input', type=argparse.FileType('r'), default=sys.stdin)
    return parser


def get_repositories(yaml_file):
    try:
        root = yaml.load(yaml_file)
    except yaml.YAMLError as e:
        raise RuntimeError('Input data is not valid yaml format: %s' % e)

    try:
        repositories = root['repositories']
        return get_repos_in_vcstool_format(repositories)
    except AttributeError as e:
        raise RuntimeError('Input data is not valid format: %s' % e)
    except TypeError as e:
        # try rosinstall file format
        try:
            return get_repos_in_rosinstall_format(root)
        except:
            raise RuntimeError('Input data is not valid format: %s' % e)


def get_repos_in_vcstool_format(repositories):
    repos = {}
    for path in repositories:
        repo = {}
        attributes = repositories[path]
        try:
            repo['type'] = attributes['type']
            repo['url'] = attributes['url']
            if 'version' in attributes:
                repo['version'] = attributes['version']
        except AttributeError as e:
            print(ansi('yellowf') + ("Repository '%s' does not provide the necessary information: %s" % (path, e)) + ansi('reset'), file=sys.stderr)
            continue
        repos[path] = repo
    return repos


def get_repos_in_rosinstall_format(root):
    repos = {}
    for i, item in enumerate(root):
        if len(item.keys()) != 1:
            raise RuntimeError('Input data is not valid format')
        repo = {'type': item.keys()[0]}
        attributes = item.values()[0]
        try:
            path = attributes['local-name']
        except AttributeError as e:
            print(ansi('yellowf') + ('Repository #%d does not provide the necessary information: %s' % (i, e)) + ansi('reset'), file=sys.stderr)
            continue
        try:
            repo['url'] = attributes['uri']
            if 'version' in attributes:
                repo['version'] = attributes['version']
        except AttributeError as e:
            print(ansi('yellowf') + ("Repository '%s' does not provide the necessary information: %s" % (path, e)) + ansi('reset'), file=sys.stderr)
            continue
        repos[path] = repo
    return repos


def generate_jobs(repos, args):
    jobs = []
    for path, repo in repos.iteritems():
        clients = [c for c in vcstool_clients if c.type == repo['type']]
        if not clients:
            print(ansi('redf') + ("Repository type '%s' is not supported" % repo['repo']) + ansi('reset'), file=sys.stderr)
            job = {
                'cmd': '',
                'cwd': path,
                'output': "Repository type '%s' is not supported" % repo['repo'],
                'returncode': NotImplemented
            }
            jobs.append(job)
            continue

        client = clients[0](path)
        command = ImportCommand(args, repo['url'], repo['version'] if 'version' in repo else None)
        job = {'client': client, 'command': command}
        jobs.append(job)
    return jobs


def main(args=None):
    parser = get_parser()
    args = parser.parse_args(args)
    args.paths = [args.path]
    try:
        repos = get_repositories(args.input)
    except RuntimeError as e:
        print(ansi('redf') + str(e) + ansi('reset'), file=sys.stderr)
        return 1
    jobs = generate_jobs(repos, args)
    results = execute_jobs(jobs, show_progress=True)
    output_results(results)
    return 0


if __name__ == '__main__':
    sys.exit(main())
