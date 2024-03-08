import argparse
import glob, os
import time 
import numpy as np
import concurrent.futures as futures
import zmq
import json

from threading import Thread, Lock
from PIL import Image
from utils import classify_image 

_in_process: bool = True
_num_processed: int = 0
_mutex: Lock = Lock()

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log_folder", type=str, required=True)
    return parser.parse_args()


def report_progress() -> None:
    previous_processed: int = 0

    while _in_process:
        time.sleep(1)
        print(" processing {:.2f} images/sec".format(_num_processed - previous_processed))
        previous_processed = _num_processed


def classify_imgfile(image_file: str) -> str:
    global _num_processed, _mutex
    
    with Image.open(image_file) as img:
        img_np = np.copy(np.asarray(img))
        # shape: (360, 640, 3), dtype: uint8
        output = classify_image(img_np)
        # output category list: https://huggingface.co/microsoft/resnet-101/blob/main/config.json
        with _mutex:
            _num_processed = _num_processed + 1

        return output


def pub_sync(service_url: str) -> None:
    # use bind socket + 1
    sync_with = ':'.join(
        service_url.split(':')[:-1] + [str(int(service_url.split(':')[-1]) + 1)]
    )
    ctx = zmq.Context.instance()
    socket = ctx.socket(zmq.REP)
    socket.bind(sync_with)
    socket.recv()
    socket.send(b'GO')


def main() -> None:
    global _in_process
    args = parse_args()
    core_count = os.cpu_count()
    image_files = glob.glob(f'{args.log_folder}/*.png')

    service_url: str = 'tcp://127.0.0.1:9901'
    ctx = zmq.Context()
    socket = ctx.socket(zmq.PUB)
    socket.bind(service_url)
    pub_sync(service_url)

    perf_thread = Thread(target=report_progress)
    perf_thread.start()
    start_time = time.time()

    # Run the classification task on a ThreadPool, size of # CPU cores to maximize the throughput
    with futures.ThreadPoolExecutor(max_workers=core_count) as executor:
        future_inputfile = {executor.submit(classify_imgfile, image_file): 
                         image_file for image_file in image_files}
        for future in futures.as_completed(future_inputfile):
            image_file = future_inputfile[future]
            try:
                category = future.result()
            except Exception as exc:
                print('%r generated an exception: %s' % (image_file, exc))
            else:
                # print(f'{image_file}: {category}')  
                msg = json.dumps({image_file: category})
                socket.send_pyobj(msg)
            
    end_time = time.time()
    _in_process = False
    perf_thread.join()
    socket.close()
    ctx.destroy()

    print("elapsed time: {:.2f}".format(end_time - start_time))
    print("{:.2f} frames/sec".format(_num_processed / (end_time - start_time)))

if __name__ == "__main__":
    main()
