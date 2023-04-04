# -*- coding: utf-8 -*-

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import datetime
import errno
import getpass
import inspect
import logging
import os
import shlex
import stat
import subprocess
import sys
import traceback

import dnf
import pexpect
from six import moves


def check_cmd(prog):
    loggerinst = logging.getLogger(__name__)
    """Return prog of absolute if prog is in $PATH ."""
    for path in os.environ['PATH'].split(os.pathsep):
        path = path.strip('"')
        candidate = os.path.join(path, prog)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    loggerinst.critical(f"{prog} executable command not found.")


def isbinary(filepath):
    """Return true if filepath is a standard binary file"""
    loggerinst = logging.getLogger(__name__)
    if not os.path.exists(filepath):
        loggerinst.info('file path {} doesnot exits'.format(filepath))
        return False
    # 文件可能被损坏，捕捉异常
    try:
        FileStates = os.stat(filepath)
        FileMode = FileStates[stat.ST_MODE]
        if not stat.S_ISREG(FileMode) or stat.S_ISLNK(
                FileMode):  # 如果文件既不是普通文件也不是链接文件
            return False
        with open(filepath, 'rb') as f:
            header = (bytearray(f.read(4))[1:4]).decode(encoding="utf-8")
            if header in ["ELF"]:
                # print (header)
                return True
    except UnicodeDecodeError as e:
        pass
    return False


def dnf_list(config, arch):
    """List the package name from the config"""
    loggerinst = logging.getLogger(__name__)
    base = dnf.Base()

    if os.path.exists(config):
        conf = base.conf
        conf.read(config)
    else:
        loggerinst.critical(f"No such file {config}, please check.")

    base.read_all_repos()
    try:
        base.fill_sack()
    except (dnf.exceptions.RepoError, dnf.exceptions.ConfigError) as e:
        loggerinst.critical(e)
    query = base.sack.query()
    a = query.available()
    pkgs = a.filter(arch=arch)
    pkgs_list = list()
    for pkg in pkgs:
        pkgs_list.append(pkg.name)
    if pkgs_list:
        return pkgs_list
    return []


def dnf_provides(config, substr, arch):
    loggerinst = logging.getLogger(__name__)
    loggerinst.debug(f"Querying which package provides {substr}.")
    base = dnf.Base()

    if os.path.exists(config):
        conf = base.conf
        conf.read(config)
    else:
        loggerinst.critical(f"No such file {config}, please check.")

    base.read_all_repos()
    try:
        base.fill_sack()
    except (dnf.exceptions.RepoError, dnf.exceptions.ConfigError) as e:
        loggerinst.critical(e)
    query = base.sack.query()
    a = query.available()
    pkgs = a.filter(file__glob=substr, arch=arch,)
    pkgs_list=list()
    if pkgs:
        for pkg in pkgs:
            pkgs_list.append(pkg.name)
        loggerinst.debug(
            f"{substr} is provides by {pkgs_list}")
    else:
        pkgs_list=[]
        loggerinst.debug(
            f"Not found package provide {substr}")
    return pkgs_list


class Color(object):
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    DARKCYAN = '\033[36m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


# Absolute path of a directory holding data for this tool
DATA_DIR = "/usr/share/abicheck"
# Directory for temporary data to be stored during runtime
TMP_DIR = "/var/lib/abicheck"


def format_msg_with_datetime(msg, level):
    """Return a string with msg formatted according to the level"""
    temp_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"[{temp_date}] {level.upper()} - {msg}"


def get_executable_name():
    """Get name of the executable file passed to the python interpreter."""
    return os.path.basename(inspect.stack()[-1][1])


def require_root():
    if os.geteuid() != 0:
        print("The tool needs to be run under the root user.")
        print("\nNo changes were made to the system.")
        sys.exit(1)


def get_file_content(filename, as_list=False):
    """Return content of a file either as a list of lines or as a multiline
    string.
    """
    lines = []
    if not os.path.exists(filename):
        if not as_list:
            return ""
        return lines
    file_to_read = open(filename, "r")
    try:
        lines = file_to_read.readlines()
    finally:
        file_to_read.close()
    if as_list:
        # remove newline character from each line
        return [x.strip() for x in lines]

    return "".join(lines)


def store_content_to_file(filename, content):
    """Write the content into the file.

    Accept string or list of strings (in that case every string will be written
    on separate line). In case the ending blankline is missing, the newline
    character is automatically appended to the file.
    """
    if isinstance(content, list):
        content = "\n".join(content)
    if len(content) > 0 and content[-1] != "\n":
        # append the missing newline to comply with standard about text files
        content += "\n"
    file_to_write = open(filename, "w")
    try:
        file_to_write.write(content)
    finally:
        file_to_write.close()


def run_cmd(cmd, print_cmd=True):
    '''
    run command in subprocess and return exit code, output, error.
    '''
    loggerinst = logging.getLogger(__name__)
    if print_cmd:
        loggerinst.debug("Calling command '%s'" % cmd)
    loggerinst.file("Calling command '%s'" % cmd)

    os.putenv('LANG', 'C')
    os.putenv('LC_ALL', 'C')
    os.environ['LANG'] = 'C'
    os.environ['LC_ALL'] = 'C'
    cmd = cmd.encode('UTF-8')
    proc = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    (stdout, stderr) = proc.communicate()
    returncode = proc.returncode
    return (returncode, stdout, stderr)


def run_subprocess(cmd="", print_cmd=True, print_output=True):
    """Call the passed command and optionally log the called command (print_cmd=True) and its
    output (print_output=True). Switching off printing the command can be useful in case it contains
    a password in plain text.
    """
    loggerinst = logging.getLogger(__name__)
    if print_cmd:
        loggerinst.debug("Calling command '%s'" % cmd)
    loggerinst.file("Calling command '%s'" % cmd)

    # Python 2.6 has a bug in shlex that interprets certain characters in a string as
    # a NULL character. This is a workaround that encodes the string to avoid the issue.
    if sys.version_info[0] == 2 and sys.version_info[1] == 6:
        cmd = cmd.encode("ascii")
    cmd = shlex.split(cmd, False)
    process = subprocess.Popen(cmd,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT,
                               bufsize=1,
                               env={'LC_ALL': 'C'})
    output = ''
    for line in iter(process.stdout.readline, b''):
        output += line.decode()
        if print_output:
            loggerinst.info(line.decode().rstrip('\n'))

    # Call communicate() to wait for the process to terminate so that we can get the return code by poll().
    # It's just for py2.6, py2.7+/3 doesn't need this.
    process.communicate()

    return_code = process.poll()
    return output, return_code


def run_cmd_in_pty(cmd="", print_cmd=True, print_output=True, columns=120):
    """Similar to run_subprocess(), but the command is executed in a pseudo-terminal.

    The pseudo-terminal can be useful when a command prints out a different output with or without an active terminal
    session. E.g. yumdownloader does not print the name of the downloaded rpm if not executed from a terminal.
    Switching off printing the command can be useful in case it contains a password in plain text.

    :param cmd: The command to execute, including the options, e.g. "ls -al"
    :type cmd: string
    :param print_cmd: Log the command (to both logfile and stdout)
    :type print_cmd: bool
    :param print_output: Log the combined stdout and stderr of the executed command (to both logfile and stdout)
    :type print_output: bool
    :param columns: Number of columns of the pseudo-terminal (characters on a line). This may influence the output.
    :type columns: int
    :return: The output (combined stdout and stderr) and the return code of the executed command
    :rtype: tuple
    """
    loggerinst = logging.getLogger(__name__)

    process = pexpect.spawn(cmd, env={'LC_ALL': 'C'}, timeout=None)
    if print_cmd:
        # This debug print somehow needs to be called after(!) the pexpect.spawn(), otherwise the setwinsize()
        # wouldn't have any effect. Weird.
        loggerinst.debug("Calling command '%s'" % cmd)

    process.setwinsize(0, columns)
    process.expect(pexpect.EOF)
    output = process.before.decode()
    if print_output:
        loggerinst.info(output.rstrip('\n'))

    process.close(
    )  # Per the pexpect API, this is necessary in order to get the return code
    return_code = process.exitstatus

    return output, return_code


def let_user_choose_item(num_of_options, item_to_choose):
    """Ask user to enter a number corresponding to the item they choose."""
    loggerinst = logging.getLogger(__name__)
    while True:  # Loop until user enters a valid number
        opt_num = prompt_user("Enter number of the chosen %s: " %
                              item_to_choose)
        try:
            opt_num = int(opt_num)
        except ValueError:
            loggerinst.warning("Enter a valid number.")
        # Ensure the entered number is in the proper range
        if 0 < opt_num <= num_of_options:
            break
        else:
            loggerinst.warning("The entered number is not in range"
                               " 1 - %s." % num_of_options)
    return opt_num - 1  # Get zero-based list index


def mkdir_p(path):
    """Create all missing directories for the path and raise no exception
    if the path exists.
    """
    try:
        os.makedirs(path)
    except OSError as err:
        if err.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def prompt_user(question, password=False):
    loggerinst = logging.getLogger(__name__)
    color_question = Color.BOLD + question + Color.END
    if password:
        response = getpass.getpass(color_question)
    else:
        response = moves.input(color_question)
    loggerinst.info("\n")
    return response


def log_traceback(debug):
    """Log a traceback either to both a file and stdout, or just file, based
    on the debug parameter.
    """
    loggerinst = logging.getLogger(__name__)
    traceback_str = get_traceback_str()
    if debug:
        # Print the traceback to the user when debug option used
        loggerinst.debug(traceback_str)
    else:
        # Print the traceback to the log file in any way
        loggerinst.file(traceback_str)


def get_traceback_str():
    """Get a traceback of an exception as a string."""
    exc_type, exc_value, exc_traceback = sys.exc_info()
    return "".join(
        traceback.format_exception(exc_type, exc_value, exc_traceback))


class DictWListValues(dict):
    """Python 2.4 replacement for Python 2.5+ collections.defaultdict(list)."""
    def __getitem__(self, item):
        if item not in iter(self.keys()):
            self[item] = []

        return super(DictWListValues, self).__getitem__(item)
