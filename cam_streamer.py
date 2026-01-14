#!/usr/bin/env python3

from config import Config, ConfigMerger
from sortedcontainers import SortedDict
from str_to_bool import str_to_bool
import argparse
import daemon
import datetime
import glob2
import logging.handlers
import os
import psutil
import schedule
import signal
import subprocess
import sys
import time
import traceback

CFG_DIR = os.getenv('CFG_DIR', 'cfg')
CFG_FILENAME = os.getenv('CFG_FILENAME', 'main.cfg')


class Cam:
    cfg = Config()
    cam_cfg = []
    cam_cfg_resolver_dict = {}
    cam_streamer = []
    cam_streamer_pid = []
    cam_streamer_start_time = []
    cam_streamer_start_flag = []
    cam_streamer_poll_flag = []
    log = logging.getLogger()
    log_handler_file = None
    main_loop_active_flag = True
    signals_name = {}

    def __init__(self, config_dir, config_filename, log_level=None):
        self.cfg_dir = config_dir
        self.cfg_filename = config_filename
        self.log_level = log_level
        self.cfg_file = os.path.join(self.cfg_dir, self.cfg_filename)

        self.read_main_config()
        self.create_dirs()
        self.setup_logging()
        self.pid_file = os.path.join(self.cfg['pid_dir'], self.cfg['pid_filename'])

        for sig in dir(signal):
            if sig.startswith('SIG') and not sig.startswith('SIG_'):
                self.signals_name[getattr(signal, sig)] = sig

    def read_main_config(self):
        if os.path.isfile(self.cfg_file):
            self.cfg.load(open(self.cfg_file))
        else:
            print('Failed to open the file: %s' % self.cfg_file)
            sys.exit(1)

    def create_dirs(self):
        if not os.path.exists(self.cfg['log_dir']):
            os.makedirs(self.cfg['log_dir'])

        if not os.path.exists(self.cfg['pid_dir']):
            os.makedirs(self.cfg['pid_dir'])

    @staticmethod
    def get_log_level(log_level):
        log_levels = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }

        if log_level is None:
            log_level = 'INFO'

        return log_levels.get(log_level.strip().upper(), logging.INFO)

    def setup_logging(self):
        if self.log_level is None:
            self.log_level = self.cfg['log_level']

        self.log_level = self.get_log_level(self.log_level)
        self.log.setLevel(self.log_level)

        logging_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        log_handler_stream = logging.StreamHandler()
        log_handler_stream.setFormatter(logging_formatter)
        log_handler_stream.setLevel(self.log_level)

        self.log_handler_file = logging.handlers.TimedRotatingFileHandler(
            filename=str(os.path.join(self.cfg['log_dir'], self.cfg['log_filename'])),
            when='midnight')
        self.log_handler_file.setFormatter(logging_formatter)
        self.log_handler_file.setLevel(self.log_level)

        self.log.addHandler(log_handler_stream)
        self.log.addHandler(self.log_handler_file)

        logging.getLogger('requests').setLevel(logging.WARNING)
        logging.getLogger('schedule').setLevel(logging.WARNING)
        sys.excepthook = self.exception_handler

    def write_main_pid(self):
        if os.path.isfile(self.pid_file):
            pid_file_content = open(self.pid_file, 'r').read()

            if len(pid_file_content.strip()):
                pid = int(pid_file_content)

                if psutil.pid_exists(pid):
                    print('Error. Already running, PID: %i' % pid)
                    sys.exit(1)

        open(self.pid_file, 'w').write(str(os.getpid()))

    def exit_handler(self, s, frame, log_signal=True, exit_code=0):
        if log_signal:
            self.log.warning('Caught signal: %s' % self.signals_name[s])

        self.kill_cams_process()

        self.log.debug('Remove own PID file: %s' % self.pid_file)
        if os.path.isfile(self.pid_file):
            os.remove(self.pid_file)
        else:
            self.log.warning('PID file not found: %s' % self.pid_file)

        if exit_code == 0:
            self.main_loop_active_flag = False
        else:
            sys.exit(exit_code)

    def exit_child(self, s, frame, log_signal=True):
        while True:
            try:
                pid, status = os.waitpid(-1, os.WNOHANG)

                if pid != 0:
                    self.log.warning('Received "%s" signal for "%s" PID with "%s" status' %
                                     (self.signals_name[s], pid, status))
                else:
                    break
            except ChildProcessError:
                self.log.debug('ChildProcessError: No child processes')
                break

    def exception_handler(self, *exception_data):
        self.log.critical('Unhandled exception:\n%s', ''.join(traceback.format_exception(*exception_data)))
        self.exit_handler(None, None, log_signal=False, exit_code=1)

    def kill_process(self, pid_file, remove_pid_file):
        pid = None

        if os.path.isfile(pid_file):
            pid_file_content = open(pid_file, 'r').read()
            self.log.debug('PID file content: "%s"' % pid_file_content)

            if len(pid_file_content.strip()):
                pid = int(pid_file_content)
                self.log.debug('Process id: %i' % pid)

                if psutil.pid_exists(pid):
                    self.log.debug('Kill process: %i' % pid)
                    try:
                        os.kill(pid, signal.SIGTERM)
                    except OSError:
                        self.log.warning('Failed to kill process: %i' % pid)
                else:
                    self.log.info('Process not found: %i' % pid)
            else:
                self.log.warning('PID is empty')

            if remove_pid_file:
                os.remove(pid_file)
        else:
            self.log.debug('Skip kill, PID file not found: %s' % pid_file)

        return pid

    def kill_cam_processes(self, cam_index, cam_reset_flag=False, kill_streamer_flag=True):
        self.log.info('Stop: %s' % self.cam_cfg[cam_index]['name'])

        if kill_streamer_flag:
            self.log.debug('Kill %s streamer' % self.cam_cfg[cam_index]['name'])
            self.kill_process(self.cam_streamer_pid[cam_index], True)

        if cam_reset_flag:
            try:
                self.cam_cfg[cam_index]['reset_cmd']
            except AttributeError:
                self.log.debug('Cam reset command not found. Skip reset')
            else:
                self.log.info('Reset "%s": ' % self.cam_cfg[cam_index]['name'])
                self.log.debug('Reset command: %s' % self.cam_cfg[cam_index]['reset_cmd'])
                return_code = subprocess.call(self.cam_cfg[cam_index]['reset_cmd'], shell=True)
                self.log.info('Reset exit code: %s' % return_code)

    def kill_cams_process(self, cam_reset_flag=False):
        for iterator, _ in enumerate(self.cam_cfg):
            self.kill_cam_processes(iterator, cam_reset_flag=cam_reset_flag)

    def bg_run(self, cmd, pid_file=None):
        self.log.debug('Running:\n%s' % cmd)

        subproc = subprocess.Popen(cmd, shell=True,
                                   stdout=subprocess.DEVNULL,
                                   stdin=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)

        self.log.debug('Started PID: %s' % subproc.pid)

        if pid_file is not None:
            open(pid_file, 'w').write(str(subproc.pid))

        return subproc

    def replacer(self, s, cam_index):
        s = s.replace('[cam_name]', self.cam_cfg[cam_index]['name'])
        s = s.replace('[cams_number]', str(len(self.cam_cfg)))
        return s

    def get_store_files_list(self):
        store_files_list = glob2.glob(os.path.join(self.cfg['cap_dir'], '**'))
        self.log.debug('Found files: %s' % store_files_list)
        return store_files_list

    def get_store_files_list_sorted(self, store_files_list):
        store_files_list_sorted = SortedDict()
        for store_file in store_files_list:
            store_files_list_sorted.update({os.path.getmtime(store_file): store_file})

        self.log.debug('Sorted files list: %s' % store_files_list_sorted)

        return store_files_list_sorted

    def cleaner(self):
        self.log.debug('Cleaner started')
        clean_flag = False
        store_files_list = None

        if int(self.cfg['cleaner_store_max_gb']) != 0:
            store_files_list = self.get_store_files_list()

            store_files_total_size_bytes = 0
            for store_file in store_files_list:
                store_files_total_size_bytes += os.path.getsize(store_file)

            store_files_total_size_gigabytes = 1.0 * store_files_total_size_bytes / 1024 / 1024 / 1024
            self.log.debug('Store files size, GB: %.3f' % store_files_total_size_gigabytes)

            if store_files_total_size_gigabytes > float(self.cfg['cleaner_store_max_gb']):
                self.log.info('Current store size / Configured max store size, GB: %.3f/%.3f' %
                              (store_files_total_size_gigabytes, self.cfg['cleaner_store_max_gb']))
                clean_flag = True

        if int(self.cfg['cleaner_store_keep_free_gb']) != 0:
            store_stat = os.statvfs(self.cfg['cap_dir'])
            store_free_gb = 1.0 * store_stat.f_bavail * store_stat.f_frsize / 1024 / 1024 / 1024
            self.log.debug('Store free space, GB: %.3f' % store_free_gb)

            if store_free_gb < float(self.cfg['cleaner_store_keep_free_gb']):
                self.log.info('Current store free space / Configured keep store free space, GB: %.3f/%.3f' %
                              (store_free_gb, self.cfg['cleaner_store_keep_free_gb']))
                clean_flag = True

        if clean_flag:
            self.log.info('Clean is active')

            if store_files_list is None:
                store_files_list = self.get_store_files_list()

            store_files_list_sorted = self.get_store_files_list_sorted(store_files_list)

            removes = 0
            for file_name in store_files_list_sorted.values():
                if os.path.isfile(file_name):
                    file_size = os.path.getsize(file_name)
                    self.log.info('Remove file: %s, file size: %s' % (file_name, file_size))
                    os.remove(file_name)

                    if file_size > int(self.cfg['cleaner_force_remove_file_less_bytes']):
                        removes += 1
                    else:
                        self.log.warning('Removed "%s" file with the "%s" bytes size' % (file_name, file_size))

                    if removes == int(self.cfg['cleaner_max_removes_per_run']):
                        self.log.debug('Max removes reached: %s' % self.cfg['cleaner_max_removes_per_run'])
                        break

        self.log.debug('Cleaner finished')

    def recording_checker(self):
        self.log.debug('Recording checker started')
        store_files_list = self.get_store_files_list()
        store_files_list_sorted = self.get_store_files_list_sorted(store_files_list)
        store_files_list_sorted_reversed = list(reversed(store_files_list_sorted.items()))
        self.log.debug('Reverse sorted files list: %s' % store_files_list_sorted_reversed)

        for iterator, cam in enumerate(self.cam_cfg):
            if self.cam_streamer_poll_flag[iterator] is True:
                cam_dir = os.path.join(self.cfg['cap_dir'], cam['name'], '')
                self.log.debug('Search the latest file for path: %s' % cam_dir)

                ts = None
                file = None
                file_found_flag = False

                for ts, file in store_files_list_sorted_reversed:
                    if file.startswith(cam_dir):
                        file_found_flag = True
                        break

                if file_found_flag:
                    dt = datetime.datetime.fromtimestamp(ts)
                    dt_diff = datetime.datetime.now() - dt
                    dt_diff_seconds = dt_diff.total_seconds()
                    self.log.debug('Found the latest file for path: %s, file: %s, ts: %s, '
                                   'dt: %s, diff: %s, diff seconds: %s' %
                                   (cam_dir, file, ts,
                                    dt, dt_diff, dt_diff_seconds))

                    if dt_diff_seconds > int(self.cfg['recording_checker_rerun_streamer_on_dt_diff_less_seconds']):
                        self.log.warning('Found the latest file: %s, diff seconds: %s' % (file, dt_diff_seconds))
                        self.kill_cam_processes(iterator, cam_reset_flag=True)
                else:
                    self.log.debug('Search failed for path: %s' % cam_dir)

        self.log.debug('Recording checker finished')

    def configs_resolver(self, map1, map2, key):
        self.cam_cfg_resolver_dict[key] = map1[key]
        return "overwrite"

    def main(self):
        self.log.info('Start')
        self.log.debug('Started: %s' % os.path.abspath(__file__))
        self.log.debug('Set SIGTERM, SIGINT, SIGCHLD handlers')
        signal.signal(signal.SIGTERM, self.exit_handler)
        signal.signal(signal.SIGINT, self.exit_handler)
        signal.signal(signal.SIGCHLD, self.exit_child)

        # Read configs
        cam_cfg_dir = os.path.join(self.cfg_dir, self.cfg['cam_cfg_mask'])
        self.log.debug('Configs search path: %s' % cam_cfg_dir)

        cam_cfg_list = glob2.glob(os.path.join(self.cfg_dir, self.cfg['cam_cfg_mask']))
        cam_cfg_list.remove(self.cfg_file)
        self.log.debug('Found configs: %s' % cam_cfg_list)

        if len(cam_cfg_list) == 0:
            self.log.critical('No config found. Exit')
            sys.exit(0)

        for cur_cam_cfg in cam_cfg_list:
            self.log.debug('Read config: %s' % cur_cam_cfg)
            tmp_cfg = Config(open(cur_cam_cfg))
            cur_cam_cfg_active_flag = True

            try:
                tmp_cfg['active']
            except AttributeError:
                self.log.debug('active flag not found')
            else:
                cur_cam_cfg_active_flag = tmp_cfg['active']

            if cur_cam_cfg_active_flag:
                self.cam_cfg.append(tmp_cfg)
                self.cam_cfg_resolver_dict.clear()
                merger = ConfigMerger(resolver=self.configs_resolver)
                merger.merge(self.cam_cfg[-1], self.cfg)

                for key in self.cam_cfg_resolver_dict:
                    self.cam_cfg[-1][key] = self.cam_cfg_resolver_dict[key]

                self.log.debug('Loaded settings for: %s' % self.cam_cfg[-1]['name'])
            else:
                self.log.debug('Config is skipped due active flag: %s' % cur_cam_cfg)
        # End Read configs

        # Cleaner
        if str_to_bool(self.cfg['cleaner_active']):
            self.cfg['cleaner_max_removes_per_run'] = self.replacer(str(self.cfg['cleaner_max_removes_per_run']), 0)
            schedule.every(self.cfg['cleaner_run_every_minutes']).minutes.do(self.cleaner)
        # End Cleaner

        # Recording checker
        if str_to_bool(self.cfg['recording_checker_active']):
            schedule.every(self.cfg['recording_checker_run_every_minutes']).minutes.do(self.recording_checker)
        # End Recording checker

        # PIDs full path
        for iterator, cam in enumerate(self.cam_cfg):
            try:
                pid_streamer = cam['pid_streamer']
            except AttributeError:
                self.log.debug('pid_streamer not found for "%s": ' % cam['name'])
                try:
                    pid_streamer = self.cfg['pid_streamer']
                except AttributeError:
                    self.log.critical("Can't find pid_streamer in config")
                    sys.exit(1)

            pid_streamer_replaced = self.replacer(os.path.join(self.cfg['pid_dir'], pid_streamer), iterator)
            self.log.debug('pid_streamer "%s" file name: %s' % (cam['name'], pid_streamer_replaced))
            self.cam_streamer_pid.append(pid_streamer_replaced)
        # End PIDs full path

        self.kill_cams_process()
        self.write_main_pid()

        # Fill empty cam_* lists
        for _, cam in enumerate(self.cam_cfg):
            self.cam_streamer.append(None)
            self.cam_streamer_start_time.append(0)
            self.cam_streamer_poll_flag.append(False)
            self.cam_streamer_start_flag.append(True)
        # End Fill empty cam_* lists

        while self.main_loop_active_flag:
            for iterator, cam in enumerate(self.cam_cfg):
                if self.cam_streamer_poll_flag[iterator] is True:
                    if self.cam_streamer[iterator].poll() is None:
                        self.log.debug('Streamer "%s" is alive' % cam['name'])
                    else:
                        self.log.warning('Streamer "%s" is dead (exit code: %s)' %
                                         (cam['name'], self.cam_streamer[iterator].returncode))
                        self.cam_streamer_start_flag[iterator] = True

                # Run streamer
                if self.cam_streamer_start_flag[iterator]:
                    self.log.info('Start in background: %s' % cam['name'])
                    self.cam_streamer[iterator] = self.bg_run(cam['cmd'].strip(), self.cam_streamer_pid[iterator])
                    self.cam_streamer_start_time[iterator] = time.time()
                    self.cam_streamer_poll_flag[iterator] = True
                    self.cam_streamer_start_flag[iterator] = False
                # End Run streamer

            schedule.run_pending()
            time.sleep(1)

        self.log.info('Finish')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-daemon', choices=['start', 'stop', 'restart'],
                        help='Daemon mode startup options')
    parser.add_argument('-log_level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help='Override config log_level')
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    if args.log_level:
        c = Cam(CFG_DIR, CFG_FILENAME, args.log_level)
    else:
        c = Cam(CFG_DIR, CFG_FILENAME)

    if args.daemon:
        if args.daemon == 'stop' or args.daemon == 'restart':
            c.log.debug('[Daemon] Stopping')
            main_pid = c.kill_process(c.pid_file, False)

            if main_pid:
                kill_time = time.time()
                killed_flag = False

                timeout = 20

                while time.time() - kill_time < timeout:
                    if not psutil.pid_exists(main_pid):
                        killed_flag = True
                        break

                if not killed_flag:
                    c.log.warning('[Daemon] Time outed waiting process to exit (timeout: "%i" seconds). PID: "%i"' %
                                  (timeout, main_pid))

        if args.daemon == 'start' or args.daemon == 'restart':
            c.log.debug('[Daemon] Starting from working directory: %s' % script_dir)
            with daemon.DaemonContext(working_directory=script_dir, files_preserve=[c.log_handler_file.stream]):
                c.main()
    else:
        c.main()
