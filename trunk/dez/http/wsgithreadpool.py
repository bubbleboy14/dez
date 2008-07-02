import threading
import Queue

class WSGIThreadPool(object):
  
#    insert_stmt = stats.insert()
    
    def __init__(self, num_threads=5, ):
        self.num_threads = num_threads
        self.work_queue = Queue.Queue()
        self.threads = []
        for i in range(self.num_threads):
            self.threads.append(threading.Thread(target=self.run))
            
    def start(self):
        for i, thread in enumerate(self.threads):
            print "Starting WSGI thread", thread.getName()
            thread.start()

    def dispatch(self, response):
        self.work_queue.put(response)
        
    def run(self):
        name = threading.currentThread().getName()
        while True:
            try:
                response = self.work_queue.get()
                if not response:
                    break
                response.dispatch()
            except Exception, e:
                import sys, traceback
                print "error:", e
                print "todo: fix exception handling in threads"
                print traceback.print_tb(sys.exc_info()[2])
        print "Shutting down thread", name
                
    def stop(self):
        for t in self.threads:
            self.work_queue.put(None)
        # We aren't cleaning up our threadpool. For now, we're making
        # the assumption that if stop has been called it's because we
        # caught ^C (or something) and so we aren't worrying about
        # leaving stuff around.
