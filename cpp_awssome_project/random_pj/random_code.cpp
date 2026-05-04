// Online C++ compiler to run C++ program online
#include <iostream>
#include <vector>
#include <mutex>
#include <memory>
#include <thread>
#include <atomic>
#include <queue>

struct WorkItem{
    int id = 0;
    std::vector<int> payload;
};

int main() {
    // Write C++ code here
    std::cout << "Start small. Ship something."<< std::endl;
    std::vector<int> vec{1,2,3};
    std::cout<< vec.size()<<std::endl;
    // for loop 
    for(auto &v : vec){
        std::cout<< v <<std::endl;
    }
    
    // no muex
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
    
    std::cout<<"\n >>>>> [MULTI-THREAD] <<<<<<" <<std::endl;
    {
        // std::queue<WorkItem> 
        std::queue<WorkItem> work_item;
        for(int i = 0; i < 100; i++){
          

         }                   

        std::atomic<double> sum_ = 0;
        std::mutex mtx_;
        std::vector<std::thread> thread_vec;
        constexpr int WORKCOUNT = 4;  
        thread_vec.reserve(WORKCOUNT);
        
        for(int i =0; i<WORKCOUNT; i++){
            thread_vec.emplace_back([&sum_]{
            std::cout << "In thread " << std::endl;
            });
        }
        for(auto &th:thread_vec){
          th.join();
        }
        
    
    }
    
    
    
    
    
    
    
    return 0;
}
