import sys 
import zmq
import json
import time 
from threading import Thread

class StatsReporter:
    def __init__(self):
        self.in_process: bool = True
        self.detected_objs: dict[int, int] = {}
        self.server_url:str = 'tcp://127.0.0.1:9901'
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect(self.server_url)
        self.socket.setsockopt(zmq.SUBSCRIBE, b'')
        self.stats_thread  = Thread(target=self.report_stats)
    
    def print_stats(self, bfinal: bool) -> None:
        if bfinal:
            print(f'[stats] final stats:')
        else:
            print(f'[stats] In the past 10s:')
        keys = list(self.detected_objs.keys())
        keys.sort()
        for key in keys:
            print(f'[stats] class {key} detected {self.detected_objs[key]} times')

    def report_stats(self) -> None:
        count: int = 0
        while self.in_process:
            time.sleep(1)
            count = count + 1
            if (count % 10) != 0:
                continue
            self.print_stats(False)
        self.print_stats(True)

    def init(self) -> None:
        # use connect socket + 1
        sync_with = ':'.join(
            self.server_url.split(':')[:-1] + [str(int(self.server_url.split(':')[-1]) + 1)]
        )
        ctx = zmq.Context.instance()
        s = ctx.socket(zmq.REQ)
        s.connect(sync_with)
        s.send(b'READY')
        s.recv()
        self.stats_thread.start()

    def receiv_msg(self):
        while True:
            try:
                msg = str(self.socket.recv_pyobj())
                jsonmsg = json.loads(msg)

                if "publisher" in jsonmsg:
                    if jsonmsg["publisher"] == "close":
                        break
                elif "cat" in jsonmsg:
                    cat = int(jsonmsg["cat"])
                    self.detected_objs[cat] = (
                        1 if cat not in self.detected_objs 
                        else (self.detected_objs[cat] + 1) 
                    )
                    # print(f'{cat}: {self.detected_cats[cat]}, size: {len(self.detected_cats)}')
            except Exception as e:
                print(e.stderr.decode(), file=sys.stderr)
                sys.exit(1)

    def deinit(self):
        self.in_process = False    
        self.stats_thread.join()


def main() -> None:
    reporter = StatsReporter()
    reporter.init()
    reporter.receiv_msg()
    reporter.deinit()


if __name__ == "__main__":
    main()
