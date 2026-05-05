// Online C++ compiler to run C++ program online
#include <iostream>
#include <vector>
#include <mutex>
#include <memory>
#include <thread>
#include <atomic>
#include <queue>
#include <numeric>
#include <chrono>
#include <condition_variable>

struct WorkItem{
    int id = 0;
    std::vector<int> payload;
};

template <typename T>
class SafeThreadQueue {
  public:
    SafeThreadQueue () = default;
    SafeThreadQueue (const SafeThreadQueue &) = delete;
    SafeThreadQueue& operator=(const SafeThreadQueue &) = delete;

    ////////////////////////////////////////////
    /////////// T &value 不能move ////////////////////
    ///////////////////////////////
    void push(T value){
      std::lock_guard<std::mutex> lock(mutex_);
      queue_.push(std::move(value)); 
      cv_.notify_one();
    }

    void wait_and_pop(T &value){
      std::unique_lock<std::mutex> lock(mutex_);
      cv_.wait(lock, [this]{return !queue_.empty();});

      value = std::move(queue_.front());
      queue_.pop();
    }

    bool empty(){
      std::lock_guard<std::mutex> lock(mutex_);
      return queue_.empty();
    }

  private:
    std::mutex mutex_;
    std::condition_variable cv_;
    std::queue<T> queue_;
};



int main() {
    // Write C++ code here
    {  
      std::cout << "Start small. Ship something."<< std::endl;
      std::vector<int> vec{1,2,3};
      std::cout<< vec.size()<<std::endl;
      // for loop 
      for(auto &v : vec){
          std::cout<< v <<std::endl;
      }
    }
    
    // no muex
    {
        std::unique_ptr<int> p = std::make_unique<int>();
        std::cout << "Unique -> " <<*p<<std::endl;
        *p = 10;
        std::cout << "Unique -> " <<*p<<std::endl;
        
        std::unique_ptr<int> new_p;
        new_p = std::move(p);
        if(p==nullptr){std::cout << "Original P is emptry now!" << std::endl;;}
        p = std::move(new_p);
        if(new_p==nullptr){std::cout << "New P is emptry now!" << std::endl;;}
        
        std::cout<<"\n >>>>> [THREAD] <<<<<<" <<std::endl;
        std::thread t([&]{
            std::cout<<"I'm in a thread " << std::endl;
            std::cout<< "original:" <<*p<< std::endl;
            *p = 100;
            std::cout<< "UpdatedinThread:" <<*p<< std::endl;
        });
         std::cout<< "UpdatedOutThread:" <<*p<< std::endl;
        t.join();
    }

    {
        std::cout<<"\n >>>>> [MULTI-THREAD Queue] <<<<<<" <<std::endl;
        {
          auto start= std::chrono::steady_clock::now();
            // std::queue<WorkItem> 
            SafeThreadQueue<std::unique_ptr<WorkItem>> work_queue;

            constexpr int work_queue_length = 1000;
          
            for(int i = 0; i < work_queue_length; i++){
              auto item = std::make_unique<WorkItem>();
              item-> id = i;
              item-> payload.reserve(i);
              for(int j=0;j<i;j++){
                item->payload.push_back(j);
              }
              work_queue.push(std::move(item));
             }                   

           /////////////////  end SIGNAL
             for(int i = 0; i < work_queue_length; i++)
               work_queue.push(nullptr);
               
            std::atomic<long> sum_ = 0;
            std::mutex mtx_;
            std::vector<std::thread> thread_vec;
            constexpr int WORKCOUNT = 8;  
            thread_vec.reserve(WORKCOUNT);
            
 
          // while(!work_queue.empty()){ 
          
          for(int i =0; i<WORKCOUNT; i++){
                thread_vec.emplace_back([&work_queue, &sum_]{ 
                  ///////
                  ////// While 的写法 更好
                  while(true){
                      auto new_item = std::make_unique<WorkItem>(); 
                     int local_sum = 0;
                      work_queue.wait_and_pop(new_item);  
                    if(new_item == nullptr) break; 
                    
                    //for(auto iter = new_item->payload.begin(); 
                     // iter!=new_item->payload.end();
                      //iter++){
                      //  local_sum = local_sum + *iter;
                     // }
                      // for(auto v: new_item->payload){
                      //   local_sum+= v;
                      // }
                     local_sum = std::accumulate(
                                        new_item->payload.begin(),
                                        new_item->payload.end(),
                                        0
                                    );
                      sum_ = sum_ + local_sum;
                       // sum_.fetch_add(local_sum, std::memory_order_relaxed);
                      if(new_item->id %100==0)
                      std::cout << "    ID:" << new_item->id << "   ,SUM: "<< local_sum << std::endl;
    
                      ////////
                      /////////
                    }
                  });
            }
          
            for(auto &th:thread_vec){
              th.join();
            }

          auto end= std::chrono::steady_clock::now();
          auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end-start);
          std::cout << "FINAL_SUM: " << sum_ << std::endl;
          std::cout << "TIME_COST: " << duration.count() << " us"<< std::endl;
          
            
        
        }
      
    }
    
    
    
    
    
    return 0;
}
