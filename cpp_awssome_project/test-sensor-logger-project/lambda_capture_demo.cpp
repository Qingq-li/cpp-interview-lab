#include <iostream>
#include <queue>

class Demo {
public:
    void test() {
        int local = 10;

        // ===== [this]: 捕获 this，local 未捕获 =====
        // 下面这行取消注释会编译错误:
        // auto lam1 = [this]{ queue_.push(5); local = 20; };
        // error: 'local' is not captured

        auto lam1 = [this]{ queue_.push(5); /* local 不可用 */ };
        lam1();
        std::cout << "[this] queue_.size() = " << queue_.size() << "\n";  // 1


        // ===== [&]: 引用捕获所有, this + local 都能改 =====
        auto lam2 = [&]{ queue_.push(5); local = 20; };
        lam2();
        std::cout << "[&]    local = " << local << "\n";              // 20
        std::cout << "[&]    queue_.size() = " << queue_.size() << "\n"; // 2


        // ===== [=]: 值捕获所有 =====
        // local 是副本且 const，下面这行取消注释会编译错误:
        // auto lam3 = [=]{ queue_.push(5); local = 20; };
        // error: cannot assign to a variable captured by copy in a non-mutable lambda

        // 但 queue_ 通过 this 访问，依然可以修改！
        auto lam3 = [=]{ queue_.push(5); /* local 只读 */ };
        lam3();
        std::cout << "[=]    local = " << local << "  (未变, 只能读副本)\n"; // 20
        std::cout << "[=]    queue_.size() = " << queue_.size() << "\n";      // 3

        // ===== 证明 [=] 中 local 确实是只读副本 =====
        auto lam4 = [=]{ return local + 1; std::cout<< "lam4() = " << local + 1 << "\n"; };  // OK: 只读
        std::cout << "[=]    lam4() = " << lam4() << "\n";  // 21
    }

private:
    std::queue<int> queue_;
};

int main() {
    Demo d;
    d.test();
    return 0;
}