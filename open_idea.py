#!/usr/bin/env python

import os
import subprocess
import sys

if __name__ == '__main__':

    def run(c):
        print('running: %s' % c)
        return subprocess.check_call(c, shell=True)


    def check(condition, message):
        if not condition:
            panic(message)


    def panic(message):
        print("ERROR:", message)
        sys.exit(1)

    check(len(sys.argv) <= 1, 'at most one parameter allowed - directory name')

    if len(sys.argv) == 1:
        dir_name = os.path.abspath('.')
    else:
        dir_name = os.path.abspath(sys.argv[1])

    check(os.path.isdir(dir_name), 'directory %s does not exist' % dir_name)

    gradle_build = os.path.join(dir_name, 'build.gradle')
    mvn_pom = os.path.join(dir_name, 'pom.xml')
    mvn_exists = os.path.exists(mvn_pom)
    gradle_exists = os.path.exists(gradle_build)

    check(gradle_exists or mvn_exists,
          'there must be a build.gradle or a pom.xml in the root of the folder %s.' % dir_name)

    if gradle_exists:
        run('idea  %s/build.gradle' % dir_name)
    else:
        run('xdg-open %s/pom.xml' % dir_name)

