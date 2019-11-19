#!/usr/bin/env python

import os
import sys
from config import Config, ConfigMerger
from sortedcontainers import SortedDict
import logging.handlers
import signal
import glob2
import psutil
import time
import subprocess
import requests
import traceback
import schedule
import daemon
import argparse

cfg_dir = 'cfg'
cfg_filename = 'main.cfg'


class Cam:
    cfg = Config()
    cam_cfg = []
    cam_cfg_resolver_dict = {}
    cam_streamer = []
    cam_streamer_pid = []
    cam_streamer_start_time = []
    cam_streamer_start_flag = []
    cam_streamer_poll_flag = []
    cam_capturer = []
    cam_capturer_pid = []
    cam_capturer_start_flag = []
    cam_capturer_check_flag = []
    log = logging.getLogger()
    log_handler_file = None
    main_loop_active_flag = True

    def __init__(self, config_dir, config_filename, log_level=None):
        self.cfg_dir = config_dir
        self.cfg_filename = config_filename
        self.log_level = log_level
        self.cfg_file = os.path.join(self.cfg_dir, self.cfg_filename)

        self.read_main_config()
        self.create_dirs()
        self.setup_logging()
        self.pid_file = os.path.join(self.cfg['pid_dir'], self.cfg['pid_filename'])

    def read_main_config(self):
        if os.path.isfile(self.cfg_file):
            self.cfg.load(open(self.cfg_file))
        else:
            print('Failed to open the file: ' + self.cfg_file)
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
            os.path.join(self.cfg['log_dir'], self.cfg['log_filename']),
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
            signals_name = {}
            for sig in dir(signal):
                if sig.startswith('SIG') and not sig.startswith('SIG_'):
                    signals_name[getattr(signal, sig)] = sig

            self.log.warn('Caught signal: ' + signals_name[s])

        self.kill_cams_process()

        self.log.debug('Remove own PID file: ' + self.pid_file)
        if os.path.isfile(self.pid_file):
            os.remove(self.pid_file)
        else:
            self.log.warn('PID file not found: ' + self.pid_file)

        if exit_code == 0:
            self.main_loop_active_flag = False
        else:
            sys.exit(exit_code)

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
                        self.log.warn('Failed to kill process: %i' % pid)
                else:
                    self.log.info('Process not found: %i' % pid)
            else:
                self.log.warn('PID is empty')

            if remove_pid_file:
                os.remove(pid_file)
        else:
            self.log.debug('Skip kill, PID file not found: ' + pid_file)

        return pid

    def kill_cam_processes(self, cam_index, cam_reset_flag=False, kill_streamer_flag=True, kill_capturer_flag=True):
        self.log.info('Stop cam: ' + self.cam_cfg[cam_index]['name'])

        if kill_capturer_flag:
            self.log.debug('Kill %s capturer' % self.cam_cfg[cam_index]['name'])
            self.kill_process(self.cam_capturer_pid[cam_index], True)

        if kill_streamer_flag:
            self.log.debug('Kill %s streamer' % self.cam_cfg[cam_index]['name'])
            self.kill_process(self.cam_streamer_pid[cam_index], True)

        if cam_reset_flag:
            try:
                self.cam_cfg[cam_index]['reset_cmd']
            except AttributeError:
                self.log.debug('Cam reset command not found. Skip reset')
            else:
                self.log.info('Resetting cam: ' + self.cam_cfg[cam_index]['name'])
                self.log.debug('Reset command: ' + self.cam_cfg[cam_index]['reset_cmd'])
                return_code = subprocess.call(self.cam_cfg[cam_index]['reset_cmd'], shell=True)
                self.log.info('Reseted with exit code: %s' % return_code)

    def kill_cams_process(self, cam_reset_flag=False):
        for iterator, _ in enumerate(self.cam_cfg):
            self.kill_cam_processes(iterator, cam_reset_flag=cam_reset_flag)

    def bg_run(self, cmd, pid_file=None):
        self.log.debug('Running:\n' + cmd)
        subproc = subprocess.Popen(cmd, shell=True)
        self.log.debug('Started PID: %s' % subproc.pid)

        if pid_file is not None:
            open(pid_file, 'w').write(str(subproc.pid))

        return subproc

    def replacer(self, s, cam_index):
        s = s.replace('[cam_name]', self.cam_cfg[cam_index]['name'])
        s = s.replace('[cams_number]', str(len(self.cam_cfg)))
        return s

    def cleaner(self):
        self.log.debug('Cleaner started')
        clean_flag = False
        store_file_list = None

        if int(self.cfg['cleaner_store_max_gb']) != 0:
            store_file_list = glob2.glob(os.path.join(self.cfg['cap_dir'], '**'))
            self.log.debug('Found files: %s' % store_file_list)

            store_file_total_size_bytes = 0
            for store_file in store_file_list:
                store_file_total_size_bytes += os.path.getsize(store_file)

            store_file_total_size_gigabytes = 1.0 * store_file_total_size_bytes / 1024 / 1024 / 1024
            self.log.debug('Store files size, Gb: %f' % store_file_total_size_gigabytes)

            if store_file_total_size_gigabytes > float(self.cfg['cleaner_store_max_gb']):
                self.log.info('Current store size / Configured max store size, Gb: %.3f/%.3f' %
                              (store_file_total_size_gigabytes, self.cfg['cleaner_store_max_gb']))
                clean_flag = True

        if int(self.cfg['cleaner_store_keep_free_gb']) != 0:
            store_stat = os.statvfs(self.cfg['cap_dir'])
            store_free_gb = 1.0 * store_stat.f_bavail * store_stat.f_frsize / 1024 / 1024 / 1024
            self.log.debug('Store free space, Gb: %f' % store_free_gb)

            if store_free_gb < float(self.cfg['cleaner_store_keep_free_gb']):
                self.log.info('Current store free space / Configured keep store free space, Gb: %.3f/%.3f' %
                              (store_free_gb, self.cfg['cleaner_store_keep_free_gb']))
                clean_flag = True

        if clean_flag:
            self.log.info('Clean is active')

            if store_file_list is None:
                store_file_list = glob2.glob(os.path.join(self.cfg['cap_dir'], '**'))

            store_file_list_sorted = SortedDict()
            for store_file in store_file_list:
                store_file_list_sorted.update({os.path.getmtime(store_file): store_file})

            self.log.debug('Sorted files list (with last modification date): %s' % store_file_list_sorted)
            self.log.debug('Sorted files list (by last modification date): %s' % store_file_list_sorted.values())

            removes = 0
            for file_name in store_file_list_sorted.values():
                if os.path.isfile(file_name):
                    file_size = os.path.getsize(file_name)
                    self.log.info('Remove file: ' + file_name)
                    os.remove(file_name)

                    if file_size > int(self.cfg['cleaner_force_remove_file_less_bytes']):
                        removes += 1
                    else:
                        self.log.warn('Removed "%s" file with the "%s" bytes size' % (file_name, file_size))

                    if removes == int(self.cfg['cleaner_max_removes_per_run']):
                        self.log.debug('Max removes reached: ' + self.cfg['cleaner_max_removes_per_run'])
                        break

        self.log.debug('Cleaner finished')

    def configs_resolver(self, map1, map2, key):
        self.cam_cfg_resolver_dict[key] = map1[key]
        return "overwrite"

    def main(self):
        self.log.info('Start')
        self.log.debug('Started: ' + os.path.abspath(__file__))
        self.log.debug('Setting SIGTERM, SIGINT handlers')
        signal.signal(signal.SIGTERM, self.exit_handler)
        signal.signal(signal.SIGINT, self.exit_handler)

        # Read cam configs
        cam_cfg_dir = os.path.join(self.cfg_dir, self.cfg['cam_cfg_mask'])
        self.log.debug('Configs search path: ' + cam_cfg_dir)

        cam_cfg_list = glob2.glob(os.path.join(self.cfg_dir, self.cfg['cam_cfg_mask']))
        cam_cfg_list.remove(self.cfg_file)
        self.log.debug('Found configs: %s' % cam_cfg_list)

        if len(cam_cfg_list) == 0:
            self.log.critical('No cam config found. Exit')
            sys.exit(0)

        for cur_cam_cfg in cam_cfg_list:
            self.log.debug('Read cam config: ' + cur_cam_cfg)
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

                self.log.debug('Loaded settings for: ' + self.cam_cfg[-1]['name'])
            else:
                self.log.debug('Cam config is skipped due active flag: ' + cur_cam_cfg)
        # End Read cam configs

        # Cleaner
        self.cfg['cleaner_max_removes_per_run'] = self.replacer(str(self.cfg['cleaner_max_removes_per_run']), 0)
        schedule.every(self.cfg['cleaner_run_every_minutes']).minutes.do(self.cleaner)
        # End Cleaner

        # PIDs full path
        for iterator, cam in enumerate(self.cam_cfg):
            try:
                pid_streamer = cam['pid_streamer']
            except AttributeError:
                self.log.debug('pid_streamer not found for cam: ' + cam['name'])
                try:
                    pid_streamer = self.cfg['pid_streamer']
                except AttributeError:
                    self.log.critical("Can't find pid_streamer in config")
                    sys.exit(1)

            try:
                pid_capturer = cam['pid_capturer']
            except AttributeError:
                self.log.debug('pid_capturer not found for cam: ' + cam['name'])
                try:
                    pid_capturer = self.cfg['pid_capturer']
                except AttributeError:
                    self.log.critical("Can't find pid_capturer in config")
                    sys.exit(1)

            self.cam_streamer_pid.append(self.replacer(os.path.join(self.cfg['pid_dir'], pid_streamer), iterator))
            self.cam_capturer_pid.append(self.replacer(os.path.join(self.cfg['pid_dir'], pid_capturer), iterator))
        # End PIDs full path

        self.kill_cams_process()
        self.write_main_pid()

        while self.main_loop_active_flag:
            for iterator, cam in enumerate(self.cam_cfg):
                if len(self.cam_streamer) == iterator:

                    # Create cam cap dir only if cap_cmd is not False
                    try:
                        cap_cmd = self.cam_cfg[iterator]['cap_cmd']
                    except AttributeError:
                        cap_cmd = None
                        self.log.debug('Capture command not found')

                    if cap_cmd is not False:
                        cap_dir_cam = self.replacer(self.cfg['cap_dir_cam'], iterator)
                        if not os.path.exists(cap_dir_cam):
                            try:
                                os.makedirs(cap_dir_cam)
                            except OSError:
                                self.log.critical('Failed to create directory: ' + cap_dir_cam)
                                sys.exit(1)
                    # End Create cam cap dir

                    self.cam_streamer_start_flag.append(True)

                    self.cam_streamer.append(None)
                    self.cam_streamer_start_time.append(0)
                    self.cam_streamer_poll_flag.append(False)

                    self.cam_capturer.append(None)
                    self.cam_capturer_start_flag.append(False)
                    self.cam_capturer_check_flag.append(False)
                else:
                    if self.cam_streamer[iterator].poll() is None:
                        self.log.debug('Streamer "%s" is alive' % cam['name'])
                    else:
                        self.log.warn('Streamer "%s" is dead (exit code: %s)' %
                                      (cam['name'], self.cam_streamer[iterator].returncode))
                        self.cam_streamer_start_flag[iterator] = True

                # Capturer alive check
                if self.cam_capturer_check_flag[iterator]:
                    if self.cam_capturer[iterator].poll() is None:
                        self.log.debug('Capturer "%s" is alive' % cam['name'])
                    else:
                        self.log.warn('Capturer "%s" is dead (exit code: %s)' %
                                      (cam['name'], self.cam_capturer[iterator].returncode))
                        self.cam_streamer_poll_flag[iterator] = True
                        self.cam_capturer_check_flag[iterator] = False
                # End Capturer alive check

                # Run streamer
                if self.cam_streamer_start_flag[iterator]:
                    self.log.info('Run "%s" streamer in background' % cam['name'])
                    self.cam_streamer[iterator] = self.bg_run(cam['cmd'].strip(), self.cam_streamer_pid[iterator])
                    self.cam_streamer_start_time[iterator] = time.time()
                    self.cam_streamer_poll_flag[iterator] = True
                    self.cam_streamer_start_flag[iterator] = False
                # End Run streamer

                # Poll streamer
                if self.cam_streamer_poll_flag[iterator]:
                    cap_url = self.cfg['cap_url']
                    cap_url = self.replacer(cap_url, iterator)

                    self.log.debug('Getting HTTP status: ' + cap_url)
                    http_code = 0

                    try:
                        http_code = requests.head(cap_url, timeout=1).status_code
                    except requests.exceptions.RequestException:
                        self.log.warn('Failed to connect: ' + cap_url)

                    if http_code != 0:
                        self.log.info('Checked "%s", status: %s' % (cam['name'], http_code))

                        if http_code == 200:
                            self.cam_capturer_start_flag[iterator] = True
                            self.cam_streamer_poll_flag[iterator] = False

                    start_time_delta = time.time() - self.cam_streamer_start_time[iterator]
                    if self.cam_streamer_poll_flag[iterator]:
                        if start_time_delta > cam['max_start_seconds']:
                            self.log.warn('Time outed waiting data from: ' + cam['name'])
                            self.log.info('Kill: ' + cam['name'])
                            self.kill_cam_processes(iterator, cam_reset_flag=True)
                            self.cam_streamer_start_flag[iterator] = True
                        else:
                            self.log.info('Attempt "%s": [%i/%i]' %
                                          (cam['name'], start_time_delta, cam['max_start_seconds']))
                # End Poll streamer

                # Run capturer
                if self.cam_capturer_start_flag[iterator]:
                    if self.cam_capturer[iterator] is not None and self.cam_capturer[iterator].poll() is None:
                        self.log.warn('Capturer "%s" is STILL alive' % cam['name'])
                    else:
                        cap_cmd = None
                        try:
                            cap_cmd = self.cam_cfg[iterator]['cap_cmd']
                        except AttributeError:
                            self.log.debug('Capture command not found in cam config. Using global')
                            try:
                                cap_cmd = self.cfg['cap_cmd']
                            except AttributeError:
                                self.log.critical('Capture command not found. Exit')
                                self.exit_handler(None, None, log_signal=False, exit_code=1)

                        if cap_cmd is not False:
                            cap_cmd = self.replacer(cap_cmd, iterator)

                            self.log.info('Run "%s" capturer in background' % cam['name'])
                            self.cam_capturer[iterator] = self.bg_run(cap_cmd, self.cam_capturer_pid[iterator])
                            self.cam_capturer_check_flag[iterator] = True
                        else:
                            self.log.info('Capturer "%s" is turned off' % cam['name'])

                    self.cam_capturer_start_flag[iterator] = False
                # End Run capturer

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
        c = Cam(cfg_dir, cfg_filename, args.log_level)
    else:
        c = Cam(cfg_dir, cfg_filename)

    if args.daemon:
        if args.daemon == 'stop' or args.daemon == 'restart':
            c.log.debug('[Daemon] Stopping')
            main_pid = c.kill_process(c.pid_file, False)

            if main_pid:
                kill_time = time.time()
                killed_flag = False

                while time.time() - kill_time < 5:
                    if not psutil.pid_exists(main_pid):
                        killed_flag = True
                        break

                if not killed_flag:
                    c.log.warn('[Daemon] Time outed waiting process to exit. PID: %i' % main_pid)

        if args.daemon == 'start' or args.daemon == 'restart':
            c.log.debug('[Daemon] Starting from working directory: ' + script_dir)
            with daemon.DaemonContext(working_directory=script_dir, files_preserve=[c.log_handler_file.stream]):
                c.main()
    else:
        c.main()
