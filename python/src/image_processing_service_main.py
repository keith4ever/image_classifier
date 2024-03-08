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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log_folder", type=str, required=True)
    return parser.parse_args()


class ImageClassifier:
    def __init__(self):
        self.in_process: bool = True
        self.num_processed: int = 0
        self.mutex: Lock = Lock()
        self.service_url: str = 'tcp://127.0.0.1:9901'
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUB)
        self.start_time: float = 0.0
        self.perf_thread = Thread(target=self.report_progress)

    def init(self) -> None:
        self.socket.bind(self.service_url)
        # use bind socket + 1
        sync_with = ':'.join(
            self.service_url.split(':')[:-1] + [str(int(self.service_url.split(':')[-1]) + 1)]
        )
        
        ctx = zmq.Context.instance()
        s = ctx.socket(zmq.REP)
        s.bind(sync_with)
        s.recv()
        s.send(b'GO')

        self.start_time = time.time()
        self.perf_thread.start()


    def report_progress(self) -> None:
        previous_processed: int = 0
        while self.in_process:
            time.sleep(1)
            print(f'[classifier] throughput: {self.num_processed - previous_processed} images/sec')
            previous_processed = self.num_processed

    def classify_imgfile(self, image_file: str) -> str:
        with Image.open(image_file) as img:
            img_np = np.copy(np.asarray(img))
            # shape: (360, 640, 3), dtype: uint8
            output = classify_image(img_np)
            # output category list: https://huggingface.co/microsoft/resnet-101/blob/main/config.json
            with self.mutex:
                self.num_processed = self.num_processed + 1
            return output

    def send_msg(self, msg) -> None:
        self.socket.send_pyobj(msg)

    def deinit(self) -> None:
        end_time = time.time()
        self.in_process = False
        self.perf_thread.join()

        msg = json.dumps({"publisher": "close"})
        self.send_msg(msg)
        
        self.socket.disconnect(self.service_url)
        self.socket.close()
        self.context.destroy()
        print("[classifier] Elapsed time: {:.2f}".format(end_time - self.start_time))
        print("[classifier] Average {:.2f} frames/sec".format(self.num_processed / (end_time - self.start_time)))


def main() -> None:
    global _in_process
    args = parse_args()
    core_count = os.cpu_count()
    image_files = glob.glob(f'{args.log_folder}/*.png')
    classifier = ImageClassifier()
    classifier.init()

    # Run the classification task on a ThreadPool, size of # CPU cores to maximize the throughput
    with futures.ThreadPoolExecutor(max_workers=core_count) as executor:
        future_inputfile = {executor.submit(classifier.classify_imgfile, image_file): 
                         image_file for image_file in image_files}
        for future in futures.as_completed(future_inputfile):
            image_file = future_inputfile[future]
            try:
                category = future.result()
            except Exception as exc:
                print('%r generated an exception: %s' % (image_file, exc))
            else:
                # print(f'{image_file}: {category}')  
                msg = json.dumps({"file": image_file, "cat": category})
                classifier.send_msg(msg)
            
    classifier.deinit()


if __name__ == "__main__":
    main()
