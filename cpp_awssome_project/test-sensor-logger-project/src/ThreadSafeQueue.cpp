#include "ThreadSafeQueue.hpp"
# include <iostream>

int main(){
    ThreadSafeQueue<int> queue_;
    for(int i = 0; i < 10; ++i)
        queue_.push(i);

    while(queue_.empty() == false){
        int value;
        queue_.wait_and_pop(value);
        std::cout << value << std::endl;
    }
}
