# (c) Copyright [2015] Hewlett Packard Enterprise Development LP
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

from subprocess import Popen, PIPE
from threading import Thread
from Queue import Queue, Empty

import time


class NodeTest():
    io_q = None
    proc = None
    errors_occurred = False
    error_text = ''
    test_result_text = ''
    stream_open = True

    def stream_watcher(self, identifier, stream):
        for line in stream:
            # block for 1 sec
            self.io_q.put((identifier, line))

        if not stream.closed:
            self.stream_open = False
            stream.close()

    def printer(self):
        while True:
            try:
                item = self.io_q.get(True, 1)
            except Empty:
                # no output in either stream for 1 sec so check if we are done
                if self.proc.poll() is not None:
                    break
            else:
                identifier, line = item
                if identifier is 'STDERR':
                    test_line = line.lower()
                    if 'failed' in test_line or 'error' in test_line:
                        self.errors_occurred = True
                        self.error_text += line
                else:
                    self.test_result_text += line

    def run_credentials_check_test(self, conf_data):
        self.errors_occurred = False
        self.error_text = ''
        self.test_result_text = ''
        self.io_q = Queue()
        self.proc = Popen(['cinderdiags', 'ssh-credentials-check', '-f',
                           'json', '-conf-data', conf_data],
                          stdout=PIPE,
                          stderr=PIPE)
        Thread(target=self.stream_watcher, name='stdout-watcher',
               args=('STDOUT', self.proc.stdout)).start()
        Thread(target=self.stream_watcher, name='stderr-watcher',
               args=('STDERR', self.proc.stderr)).start()
        Thread(target=self.printer, name='printer').start()

        done = False
        while not done:
            time.sleep(2)
            if self.proc.stdout.closed and self.proc.stderr.closed:
                done = True

    def run_options_check_test(self, conf_data):
        self.errors_occurred = False
        self.error_text = ''
        self.test_result_text = ''
        self.io_q = Queue()
        self.proc = Popen(['cinderdiags', '-v', 'options-check', '-f', 'json',
                           '-conf-data', conf_data, '-incl-system-info'],
                          stdout=PIPE,
                          stderr=PIPE)
        Thread(target=self.stream_watcher, name='stdout-watcher',
               args=('STDOUT', self.proc.stdout)).start()
        Thread(target=self.stream_watcher, name='stderr-watcher',
               args=('STDERR', self.proc.stderr)).start()
        Thread(target=self.printer, name='printer').start()

        done = False
        while not done:
            time.sleep(2)
            if self.proc.stdout.closed and self.proc.stderr.closed:
                done = True

    def run_software_check_test(self, conf_data, software_test_data):
        self.errors_occurred = False
        self.error_text = ''
        self.test_result_text = ''
        self.io_q = Queue()
        self.proc = Popen(['cinderdiags', '-v', 'software-check', '-f', 'json',
                           '-conf-data', conf_data,
                           '-software-pkgs', software_test_data],
                          stdout=PIPE,
                          stderr=PIPE)
        Thread(target=self.stream_watcher, name='stdout-watcher',
               args=('STDOUT', self.proc.stdout)).start()
        Thread(target=self.stream_watcher, name='stderr-watcher',
               args=('STDERR', self.proc.stderr)).start()
        Thread(target=self.printer, name='printer').start()

        done = False
        while not done:
            time.sleep(2)
            if self.proc.stdout.closed and self.proc.stderr.closed:
                done = True
