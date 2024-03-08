import sys 
import zmq
import json
from inspect import currentframe, getframeinfo

def sub_sync(server_url: str) -> None:
    # use connect socket + 1
    sync_with = ':'.join(
        server_url.split(':')[:-1] + [str(int(server_url.split(':')[-1]) + 1)]
    )
    ctx = zmq.Context.instance()
    socket = ctx.socket(zmq.REQ)
    socket.connect(sync_with)
    socket.send(b'READY')
    socket.recv()


def receiv_msg(socket):
    while True:
        try:
            msg = socket.recv_pyobj()
            print(f'Msg received: {msg}')
        except zmq.Error as e:
            print(e.stderr.decode(), file=sys.stderr)
            sys.exit(1)
    

def main() -> None:
    server_url:str = 'tcp://127.0.0.1:9901'
    ctx = zmq.Context()
    socket = ctx.socket(zmq.SUB)
    socket.connect(server_url)
    socket.setsockopt(zmq.SUBSCRIBE, b'')
    
    sub_sync(server_url)
    receiv_msg(socket)
    print(" Done ")

if __name__ == "__main__":
    main()
