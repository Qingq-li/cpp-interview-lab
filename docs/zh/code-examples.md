# C++ Code Examples：知识点代码库

这一篇用可运行代码复习 C++ 高频知识点。每张卡只聚焦一个主题，代码内部用中文注释标出正式写法、易错点和面试解释重点。

建议使用方式：

1. 先读知识点目标，明确这段代码要证明什么。
2. 再点开核心代码，关注中文注释和输出行为。
3. 用 RUN C++ 加载示例，修改一两行观察编译或运行结果。
4. 最后用面试表达把代码行为转成口头回答。

---

## 1. `const` 的变量、指针和成员函数

### 知识点目标

- 区分顶层 const 和底层 const
- 理解 `const` 成员函数表达只读接口
- 知道 `mutable` 只适合缓存/统计等逻辑不变场景

### 核心代码

```cpp
#include <iostream>

class Counter {
public:
    explicit Counter(int value) : value_(value) {}

    int value() const {
        ++read_count_; // 中文注释：mutable 字段可在 const 函数里更新统计信息
        return value_;
    }

private:
    int value_ = 0;
    mutable int read_count_ = 0;
};

int main() {
    int x = 10;
    const int* p = &x;  // 中文注释：不能通过 p 修改 x，但 p 可以改指向
    int* const q = &x;  // 中文注释：q 不能改指向，但可以通过 q 修改 x

    // *p = 20;         // 不要这样写：p 指向 const int
    *q = 30;

    const Counter c(7);
    std::cout << *p << ' ' << c.value() << '\n';
}
```

### 关键注释

- `const int*` 限制的是被指向对象的修改
- `int* const` 限制的是指针变量本身的重新绑定
- `value() const` 让 const 对象也能调用这个只读接口

### 常见易错点

- 把 `const int*` 和 `int* const` 混为一谈
- 认为 const 成员函数里绝对不能改任何成员
- 为了绕过类型系统滥用 `const_cast`

### 面试表达

我会说：`const` 不只是防止误修改，也是接口承诺。只读参数用 `const T&`，只读成员函数加 `const`，能让调用者更清楚函数不会改变对象的逻辑状态。

### 扩展练习

- 把 `p` 改指向另一个变量，观察能否编译
- 增加一个非 const 成员函数，对比 const 对象能否调用
- 尝试去掉 `mutable` 看编译错误
---

## 2. 指针和引用的参数选择

### 知识点目标

- 用引用表达必选对象
- 用指针表达可空或可重新指向
- 用 `const T&` 避免不必要拷贝

### 核心代码

```cpp
#include <iostream>
#include <string>

void printName(const std::string& name) {
    // 中文注释：name 必须存在，函数承诺不修改它
    std::cout << "name=" << name << '\n';
}

void maybePrint(const std::string* name) {
    // 中文注释：指针可以为空，所以使用前必须检查
    if (name == nullptr) {
        std::cout << "no name\n";
        return;
    }
    std::cout << "name=" << *name << '\n';
}

int main() {
    std::string user = "Ada";
    printName(user);
    maybePrint(&user);
    maybePrint(nullptr);
}
```

### 关键注释

- `printName` 的引用参数表达调用方必须传入有效对象
- `maybePrint` 的指针参数表达这个依赖可以不存在
- 指针解引用前要做空指针检查

### 常见易错点

- 用引用表示可选参数
- 指针不检查空就直接解引用
- 为了避免拷贝把所有参数都写成裸指针

### 面试表达

我会说：参数不能为空时优先用引用或 `const T&`；参数可能缺失、需要表达可选依赖或多态对象时，指针语义更清楚。

### 扩展练习

- 把 `maybePrint` 改成引用参数，思考如何表达“没有值”
- 增加一个会修改字符串的函数，对比 `std::string&` 和 `const std::string&`
- 用智能指针表达所有权，再和裸指针对比
---

## 3. 生命周期和返回值安全

### 知识点目标

- 不要返回局部变量的引用或指针
- 优先返回值，让调用方拥有结果
- 理解悬垂引用是未定义行为

### 核心代码

```cpp
#include <iostream>
#include <string>

std::string makeName() {
    std::string name = "Grace";
    return name; // 中文注释：返回值安全，编译器通常会做返回值优化
}

const std::string& pickLonger(const std::string& a, const std::string& b) {
    // 中文注释：返回的是调用方传入对象的引用，调用方要保证对象仍然存活
    return a.size() >= b.size() ? a : b;
}

int main() {
    std::string a = makeName();
    std::string b = "C++";
    std::cout << pickLonger(a, b) << '\n';

    // 不要这样写：返回局部变量引用会悬垂
    // const std::string& bad() { std::string s = "x"; return s; }
}
```

### 关键注释

- `makeName` 返回值由调用方接收，生命周期清晰
- `pickLonger` 返回引用时依赖实参继续存活
- 注释中的 bad 写法是典型悬垂引用

### 常见易错点

- 误以为返回引用一定比返回值高效
- 返回局部自动变量地址
- 保存指向临时对象内部数据的指针

### 面试表达

我会说：现代 C++ 返回值很安全，很多场景还有 RVO/NRVO。只有能证明被引用对象活得足够久时，才返回引用或指针。

### 扩展练习

- 把 `pickLonger(makeName(), b)` 写出来，分析返回引用是否安全
- 改成返回 `std::string`，比较接口语义
- 加入 `std::string_view`，观察生命周期风险
---

## 4. 作用域和 `static` 局部变量

### 知识点目标

- 区分名字可见范围和对象存储期
- 理解局部 static 只初始化一次
- 知道 C++11 起局部 static 初始化线程安全

### 核心代码

```cpp
#include <iostream>

int nextId() {
    static int id = 0; // 中文注释：只初始化一次，函数返回后仍保留值
    return ++id;
}

int main() {
    std::cout << nextId() << '\n';
    std::cout << nextId() << '\n';

    for (int i = 0; i < 2; ++i) {
        int local = i; // 中文注释：local 每次循环迭代都会重新创建
        std::cout << local << '\n';
    }
}
```

### 关键注释

- `id` 名字只在 `nextId` 内可见，但对象持续存在
- `local` 是普通自动对象，离开作用域就销毁
- 局部 static 适合延迟初始化的全局唯一对象

### 常见易错点

- 把 static 局部变量当成普通局部变量
- 滥用 static 制造隐藏全局状态
- 认为 static 一定意味着线程安全的读写

### 面试表达

我会说：`static` 局部变量解决的是存储期问题，不等于线程安全容器或同步机制。初始化线程安全，但之后读写共享状态仍要同步。

### 扩展练习

- 把 `id` 改成普通局部变量，观察输出变化
- 在多线程中调用 `nextId`，思考数据竞争
- 把 `static` 用于单例并讨论测试问题
---

## 5. 成员初始化列表

### 知识点目标

- 直接初始化成员而不是先默认构造再赋值
- 处理 const 成员、引用成员和无默认构造成员
- 理解成员初始化顺序由声明顺序决定

### 核心代码

```cpp
#include <iostream>
#include <string>
#include <utility>

class User {
public:
    User(int id, std::string name)
        : id_(id), name_(std::move(name)) { // 中文注释：直接初始化成员
        std::cout << "construct user\n";
    }

    void print() const {
        std::cout << id_ << ':' << name_ << '\n';
    }

private:
    const int id_;      // 中文注释：const 成员必须在初始化列表中初始化
    std::string name_;
};

int main() {
    User u(1, "Linus");
    u.print();
}
```

### 关键注释

- `id_` 不能在构造函数体里再赋值
- `name_(std::move(name))` 避免一次不必要拷贝
- 构造函数体执行时成员已经初始化完成

### 常见易错点

- 把初始化列表当作性能细节而不是语义要求
- 误以为初始化顺序按列表书写顺序决定
- 在构造函数体里对 const 成员赋值

### 面试表达

我会说：初始化列表是构造对象的主要位置。资源类、const 成员、依赖注入对象都应该在这里明确初始化。

### 扩展练习

- 交换 `id_` 和 `name_` 的声明顺序，观察编译器 warning
- 添加引用成员并尝试在函数体赋值
- 把 `std::move` 去掉比较行为
---

## 6. 构造、析构和 RAII

### 知识点目标

- 构造函数建立对象不变量
- 析构函数释放资源
- RAII 让异常路径也能自动清理

### 核心代码

```cpp
#include <iostream>
#include <stdexcept>

class ScopeLog {
public:
    explicit ScopeLog(const char* name) : name_(name) {
        std::cout << "enter " << name_ << '\n';
    }

    ~ScopeLog() {
        // 中文注释：析构函数离开作用域时自动执行，包括异常路径
        std::cout << "leave " << name_ << '\n';
    }

private:
    const char* name_;
};

int main() {
    try {
        ScopeLog log("work");
        throw std::runtime_error("fail");
    } catch (const std::exception& e) {
        std::cout << e.what() << '\n';
    }
}
```

### 关键注释

- `ScopeLog` 构造时记录进入作用域
- 抛异常后栈展开会调用析构函数
- 这就是 RAII 的基础行为

### 常见易错点

- 析构函数里抛异常
- 资源获取后靠手写 `cleanup()` 管理
- 认为异常会跳过局部对象析构

### 面试表达

我会说：RAII 的价值在异常路径最明显。资源绑定到对象生命周期，离开作用域自动释放，避免遗漏清理逻辑。

### 扩展练习

- 把 `throw` 去掉观察析构顺序
- 用文件句柄或 mutex 替换日志资源
- 尝试在析构函数抛异常并分析风险
---

## 7. 拷贝构造和拷贝赋值

### 知识点目标

- 拷贝构造用于创建新对象
- 拷贝赋值用于覆盖已有对象
- 资源类要明确深拷贝、禁拷贝或共享语义

### 核心代码

```cpp
#include <iostream>
#include <string>

class User {
public:
    explicit User(std::string name) : name_(std::move(name)) {}

    User(const User& other) : name_(other.name_) {
        std::cout << "copy construct\n";
    }

    User& operator=(const User& other) {
        std::cout << "copy assign\n";
        if (this != &other) { // 中文注释：处理自赋值
            name_ = other.name_;
        }
        return *this;
    }

private:
    std::string name_;
};

int main() {
    User a("A");
    User b = a; // 拷贝构造
    b = a;      // 拷贝赋值
}
```

### 关键注释

- `User b = a` 创建新对象，调用拷贝构造
- `b = a` 覆盖已有对象，调用拷贝赋值
- `this != &other` 防止直接自赋值造成问题

### 常见易错点

- 看到等号就认为一定是赋值
- 资源类默认浅拷贝导致 double free
- 拷贝赋值忘记返回 `*this`

### 面试表达

我会说：拷贝构造和拷贝赋值处在不同生命周期阶段。管理资源的类必须明确拷贝语义，否则默认行为可能非常危险。

### 扩展练习

- 把 `User b(a);` 加进去观察输出
- 加入一个裸指针成员，分析默认拷贝风险
- 改成 `User(const User&) = delete` 表达不可拷贝
---

## 8. 移动语义和 moved-from 状态

### 知识点目标

- 移动语义转移资源而不是深拷贝
- `std::move` 只是类型转换，不执行移动本身
- 被移动对象仍需有效、可析构、可赋值

### 核心代码

```cpp
#include <iostream>
#include <string>
#include <vector>

int main() {
    std::vector<std::string> names;
    std::string name = "Bjarne";

    names.push_back(std::move(name)); // 中文注释：允许 vector 移动接管 name 的内部资源
    std::cout << names.front() << '\n';

    // 中文注释：name 仍然有效，但值不应再被业务逻辑依赖
    name = "Stroustrup";
    names.push_back(name); // 中文注释：这里是拷贝，因为 name 是左值

    std::cout << names.back() << '\n';
}
```

### 关键注释

- `std::move(name)` 让表达式匹配移动重载
- 移动后 `name` 可以重新赋值
- 第二次 `push_back(name)` 不会移动，因为 `name` 是左值

### 常见易错点

- 以为 `std::move` 本身搬走资源
- 继续依赖 moved-from 对象原值
- 对小对象到处乱加 `std::move`

### 面试表达

我会说：移动语义优化的是资源转移成本。移动后源对象仍有效，但只适合析构、赋值或重新建立状态。

### 扩展练习

- 把第二次 push 改成 `std::move(name)`
- 打印 moved-from 字符串并解释为什么不能依赖结果
- 用自定义类打印 move constructor 调用
---

## 9. `explicit` 防止意外隐式转换

### 知识点目标

- 单参数构造函数可能参与隐式转换
- `explicit` 能阻止不期望的自动构造
- 接口越底层越应该谨慎隐式转换

### 核心代码

```cpp
#include <iostream>

class Port {
public:
    explicit Port(int value) : value_(value) {}
    int value() const { return value_; }

private:
    int value_ = 0;
};

void connect(Port port) {
    std::cout << "connect to " << port.value() << '\n';
}

int main() {
    connect(Port{8080});
    // connect(8080); // 不要这样写：explicit 阻止 int 隐式变成 Port
}
```

### 关键注释

- `Port{8080}` 显式表达构造意图
- `explicit` 让 `connect(8080)` 无法编译
- 这能避免数字参数被误解释成端口对象

### 常见易错点

- 所有单参数构造都允许隐式转换
- 为了省字少写 `explicit`
- 把 explicit 当成性能优化

### 面试表达

我会说：`explicit` 是接口安全工具。它让类型边界更清楚，减少参数误传带来的隐藏 bug。

### 扩展练习

- 去掉 `explicit`，观察 `connect(8080)` 是否可编译
- 给 `Port` 增加范围检查
- 比较 `Port p = 8080` 和 `Port p{8080}`
---

## 10. `static` 成员变量和成员函数

### 知识点目标

- static 成员属于类而不是某个对象
- static 成员函数没有 `this` 指针
- 适合表达类级别计数、工厂或共享配置

### 核心代码

```cpp
#include <iostream>

class InstanceCounter {
public:
    InstanceCounter() { ++count_; }
    ~InstanceCounter() { --count_; }

    static int count() {
        // 中文注释：static 成员函数不能直接访问非 static 成员，因为没有 this
        return count_;
    }

private:
    inline static int count_ = 0; // 中文注释：C++17 inline static 可在类内定义
};

int main() {
    InstanceCounter a;
    InstanceCounter b;
    std::cout << InstanceCounter::count() << '\n';
}
```

### 关键注释

- `count_` 被所有对象共享
- 构造和析构维护共享计数
- `InstanceCounter::count()` 不依赖具体对象

### 常见易错点

- 认为 static 成员每个对象一份
- 在 static 函数里访问普通成员
- 忘记在 C++17 前 static 数据成员需要类外定义

### 面试表达

我会说：`static` 成员表达类级别状态。它方便，但也是共享状态，涉及并发时要额外同步。

### 扩展练习

- 把 `inline` 去掉，讨论 C++17 前后的区别
- 在多线程里创建对象，分析数据竞争
- 把 `count_` 改成 `std::atomic<int>`
---

## 11. `inline` 和头文件函数

### 知识点目标

- inline 允许多翻译单元中有相同函数定义
- 现代 C++ 中更多用于 ODR 管理
- 是否真的内联由编译器决定

### 核心代码

```cpp
#include <iostream>

inline int add(int a, int b) { return a + b; } // 中文注释：可安全放在头文件中
int main() { std::cout << add(1, 2) << '\n'; }
```

### 关键注释

- 代码块是单文件 C++17 示例，可直接放到 playground 运行
- 中文注释标出正式用法或易错边界
- 输出用于帮助确认行为

### 常见易错点

- 只记 API 名字，不理解生命周期和失效规则
- 把演示代码里的简化写法直接搬到复杂项目
- 忽略异常、并发或所有权边界

### 面试表达

我会用这段代码先说明知识点解决什么问题，再指出实际项目里的边界，例如所有权、迭代器失效、线程同步或异常安全。

### 扩展练习

- 修改输入数据，观察输出变化
- 故意打开注释里的错误写法，理解编译器报错
- 把示例封装成函数，思考接口应该如何设计
---

## 12. `enum class` 强类型枚举

### 知识点目标

- 枚举值不污染外层作用域
- 不会随意隐式转换成 int
- 适合表达有限状态

### 核心代码

```cpp
#include <iostream>

enum class State { Idle, Running, Stopped };
int main() { State s = State::Running; if (s == State::Running) std::cout << "running\n"; }
```

### 关键注释

- 代码块是单文件 C++17 示例，可直接放到 playground 运行
- 中文注释标出正式用法或易错边界
- 输出用于帮助确认行为

### 常见易错点

- 只记 API 名字，不理解生命周期和失效规则
- 把演示代码里的简化写法直接搬到复杂项目
- 忽略异常、并发或所有权边界

### 面试表达

我会用这段代码先说明知识点解决什么问题，再指出实际项目里的边界，例如所有权、迭代器失效、线程同步或异常安全。

### 扩展练习

- 修改输入数据，观察输出变化
- 故意打开注释里的错误写法，理解编译器报错
- 把示例封装成函数，思考接口应该如何设计
---

## 13. `vector` push/pop/reserve/resize

### 知识点目标

- `reserve` 改容量不改 size
- `resize` 改元素个数
- `pop_back` 不返回元素，要先读取再删除

### 核心代码

```cpp
#include <iostream>
#include <vector>

int main() { std::vector<int> v; v.reserve(4); v.push_back(10); v.push_back(20); int last = v.back(); v.pop_back(); v.resize(3); std::cout << last << ' ' << v.size() << ' ' << v.capacity() << '\n'; }
```

### 关键注释

- 代码块是单文件 C++17 示例，可直接放到 playground 运行
- 中文注释标出正式用法或易错边界
- 输出用于帮助确认行为

### 常见易错点

- 只记 API 名字，不理解生命周期和失效规则
- 把演示代码里的简化写法直接搬到复杂项目
- 忽略异常、并发或所有权边界

### 面试表达

我会用这段代码先说明知识点解决什么问题，再指出实际项目里的边界，例如所有权、迭代器失效、线程同步或异常安全。

### 扩展练习

- 修改输入数据，观察输出变化
- 故意打开注释里的错误写法，理解编译器报错
- 把示例封装成函数，思考接口应该如何设计
---

## 14. `vector` 迭代器失效

### 知识点目标

- 扩容会让旧迭代器失效
- 保存索引通常比保存迭代器更稳
- 预估容量可用 reserve 降低扩容次数

### 核心代码

```cpp
#include <iostream>
#include <vector>

int main() { std::vector<int> v{1,2,3}; std::size_t index = 1; v.reserve(100); v.push_back(4); std::cout << v[index] << '\n'; }
```

### 关键注释

- 代码块是单文件 C++17 示例，可直接放到 playground 运行
- 中文注释标出正式用法或易错边界
- 输出用于帮助确认行为

### 常见易错点

- 只记 API 名字，不理解生命周期和失效规则
- 把演示代码里的简化写法直接搬到复杂项目
- 忽略异常、并发或所有权边界

### 面试表达

我会用这段代码先说明知识点解决什么问题，再指出实际项目里的边界，例如所有权、迭代器失效、线程同步或异常安全。

### 扩展练习

- 修改输入数据，观察输出变化
- 故意打开注释里的错误写法，理解编译器报错
- 把示例封装成函数，思考接口应该如何设计
---

## 15. `std::array` 固定大小数组

### 知识点目标

- 大小是类型的一部分
- 连续存储，可配合 STL 算法
- 适合固定长度数据

### 核心代码

```cpp
#include <array>
#include <iostream>

int main() { std::array<int, 3> a{1,2,3}; for (int& x : a) x *= 2; std::cout << a.size() << ' ' << a[0] << '\n'; }
```

### 关键注释

- 代码块是单文件 C++17 示例，可直接放到 playground 运行
- 中文注释标出正式用法或易错边界
- 输出用于帮助确认行为

### 常见易错点

- 只记 API 名字，不理解生命周期和失效规则
- 把演示代码里的简化写法直接搬到复杂项目
- 忽略异常、并发或所有权边界

### 面试表达

我会用这段代码先说明知识点解决什么问题，再指出实际项目里的边界，例如所有权、迭代器失效、线程同步或异常安全。

### 扩展练习

- 修改输入数据，观察输出变化
- 故意打开注释里的错误写法，理解编译器报错
- 把示例封装成函数，思考接口应该如何设计
---

## 16. `std::deque` 双端操作

### 知识点目标

- 头尾插入删除都高效
- 支持随机访问
- 通常不是整体连续内存

### 核心代码

```cpp
#include <deque>
#include <iostream>

int main() { std::deque<int> q; q.push_back(2); q.push_front(1); q.pop_back(); std::cout << q.front() << '\n'; }
```

### 关键注释

- 代码块是单文件 C++17 示例，可直接放到 playground 运行
- 中文注释标出正式用法或易错边界
- 输出用于帮助确认行为

### 常见易错点

- 只记 API 名字，不理解生命周期和失效规则
- 把演示代码里的简化写法直接搬到复杂项目
- 忽略异常、并发或所有权边界

### 面试表达

我会用这段代码先说明知识点解决什么问题，再指出实际项目里的边界，例如所有权、迭代器失效、线程同步或异常安全。

### 扩展练习

- 修改输入数据，观察输出变化
- 故意打开注释里的错误写法，理解编译器报错
- 把示例封装成函数，思考接口应该如何设计
---

## 17. `std::list` 稳定迭代器

### 知识点目标

- 链表节点分散存储
- 已知位置插删高效
- 不支持随机访问

### 核心代码

```cpp
#include <iostream>
#include <list>

int main() { std::list<int> xs{1,3}; auto it = xs.begin(); ++it; xs.insert(it, 2); for (int x : xs) std::cout << x << ' '; }
```

### 关键注释

- 代码块是单文件 C++17 示例，可直接放到 playground 运行
- 中文注释标出正式用法或易错边界
- 输出用于帮助确认行为

### 常见易错点

- 只记 API 名字，不理解生命周期和失效规则
- 把演示代码里的简化写法直接搬到复杂项目
- 忽略异常、并发或所有权边界

### 面试表达

我会用这段代码先说明知识点解决什么问题，再指出实际项目里的边界，例如所有权、迭代器失效、线程同步或异常安全。

### 扩展练习

- 修改输入数据，观察输出变化
- 故意打开注释里的错误写法，理解编译器报错
- 把示例封装成函数，思考接口应该如何设计
---

## 18. `std::map` 有序映射

### 知识点目标

- 键有序
- 适合范围查询和有序输出
- 查找插入通常 O(log n)

### 核心代码

```cpp
#include <iostream>
#include <map>
#include <string>

int main() { std::map<std::string,int> score{{"b",2},{"a",1}}; for (const auto& [k,v] : score) std::cout << k << ':' << v << ' '; }
```

### 关键注释

- 代码块是单文件 C++17 示例，可直接放到 playground 运行
- 中文注释标出正式用法或易错边界
- 输出用于帮助确认行为

### 常见易错点

- 只记 API 名字，不理解生命周期和失效规则
- 把演示代码里的简化写法直接搬到复杂项目
- 忽略异常、并发或所有权边界

### 面试表达

我会用这段代码先说明知识点解决什么问题，再指出实际项目里的边界，例如所有权、迭代器失效、线程同步或异常安全。

### 扩展练习

- 修改输入数据，观察输出变化
- 故意打开注释里的错误写法，理解编译器报错
- 把示例封装成函数，思考接口应该如何设计
---

## 19. `std::unordered_map` 哈希查找

### 知识点目标

- 平均 O(1) 查找
- 元素无序
- reserve 可降低 rehash 次数

### 核心代码

```cpp
#include <iostream>
#include <string>
#include <unordered_map>

int main() { std::unordered_map<std::string,int> count; count.reserve(10); ++count["cpp"]; std::cout << count.at("cpp") << '\n'; }
```

### 关键注释

- 代码块是单文件 C++17 示例，可直接放到 playground 运行
- 中文注释标出正式用法或易错边界
- 输出用于帮助确认行为

### 常见易错点

- 只记 API 名字，不理解生命周期和失效规则
- 把演示代码里的简化写法直接搬到复杂项目
- 忽略异常、并发或所有权边界

### 面试表达

我会用这段代码先说明知识点解决什么问题，再指出实际项目里的边界，例如所有权、迭代器失效、线程同步或异常安全。

### 扩展练习

- 修改输入数据，观察输出变化
- 故意打开注释里的错误写法，理解编译器报错
- 把示例封装成函数，思考接口应该如何设计
---

## 20. `std::set` 去重和排序

### 知识点目标

- 元素唯一且有序
- 插入重复元素不会新增节点
- 适合集合语义

### 核心代码

```cpp
#include <iostream>
#include <set>

int main() { std::set<int> s{3,1,3,2}; auto [it, inserted] = s.insert(2); std::cout << inserted << ' ' << *s.begin() << '\n'; }
```

### 关键注释

- 代码块是单文件 C++17 示例，可直接放到 playground 运行
- 中文注释标出正式用法或易错边界
- 输出用于帮助确认行为

### 常见易错点

- 只记 API 名字，不理解生命周期和失效规则
- 把演示代码里的简化写法直接搬到复杂项目
- 忽略异常、并发或所有权边界

### 面试表达

我会用这段代码先说明知识点解决什么问题，再指出实际项目里的边界，例如所有权、迭代器失效、线程同步或异常安全。

### 扩展练习

- 修改输入数据，观察输出变化
- 故意打开注释里的错误写法，理解编译器报错
- 把示例封装成函数，思考接口应该如何设计
---

## 21. queue/stack/priority_queue

### 知识点目标

- 适配器限制接口以表达数据结构语义
- queue 是 FIFO
- priority_queue 默认大顶堆

### 核心代码

```cpp
#include <iostream>
#include <queue>
#include <stack>

int main() { std::queue<int> q; q.push(1); q.push(2); std::stack<int> st; st.push(1); st.push(2); std::priority_queue<int> pq; pq.push(1); pq.push(3); std::cout << q.front() << ' ' << st.top() << ' ' << pq.top() << '\n'; }
```

### 关键注释

- 代码块是单文件 C++17 示例，可直接放到 playground 运行
- 中文注释标出正式用法或易错边界
- 输出用于帮助确认行为

### 常见易错点

- 只记 API 名字，不理解生命周期和失效规则
- 把演示代码里的简化写法直接搬到复杂项目
- 忽略异常、并发或所有权边界

### 面试表达

我会用这段代码先说明知识点解决什么问题，再指出实际项目里的边界，例如所有权、迭代器失效、线程同步或异常安全。

### 扩展练习

- 修改输入数据，观察输出变化
- 故意打开注释里的错误写法，理解编译器报错
- 把示例封装成函数，思考接口应该如何设计
---

## 22. range-based for 值和引用

### 知识点目标

- `auto x` 会拷贝
- `auto& x` 修改原元素
- `const auto&` 适合只读大对象

### 核心代码

```cpp
#include <iostream>
#include <vector>

int main() { std::vector<int> v{1,2}; for (auto x : v) x *= 10; for (auto& x : v) x *= 10; std::cout << v[0] << '\n'; }
```

### 关键注释

- 代码块是单文件 C++17 示例，可直接放到 playground 运行
- 中文注释标出正式用法或易错边界
- 输出用于帮助确认行为

### 常见易错点

- 只记 API 名字，不理解生命周期和失效规则
- 把演示代码里的简化写法直接搬到复杂项目
- 忽略异常、并发或所有权边界

### 面试表达

我会用这段代码先说明知识点解决什么问题，再指出实际项目里的边界，例如所有权、迭代器失效、线程同步或异常安全。

### 扩展练习

- 修改输入数据，观察输出变化
- 故意打开注释里的错误写法，理解编译器报错
- 把示例封装成函数，思考接口应该如何设计
---

## 23. `std::sort` 比较器

### 知识点目标

- 比较器要满足严格弱序
- 返回 lhs 是否排在 rhs 前
- 不要写 `<=`

### 核心代码

```cpp
#include <algorithm>
#include <iostream>
#include <vector>

int main() { std::vector<int> v{3,1,2}; std::sort(v.begin(), v.end(), [](int a, int b){ return a > b; }); for (int x : v) std::cout << x; }
```

### 关键注释

- 代码块是单文件 C++17 示例，可直接放到 playground 运行
- 中文注释标出正式用法或易错边界
- 输出用于帮助确认行为

### 常见易错点

- 只记 API 名字，不理解生命周期和失效规则
- 把演示代码里的简化写法直接搬到复杂项目
- 忽略异常、并发或所有权边界

### 面试表达

我会用这段代码先说明知识点解决什么问题，再指出实际项目里的边界，例如所有权、迭代器失效、线程同步或异常安全。

### 扩展练习

- 修改输入数据，观察输出变化
- 故意打开注释里的错误写法，理解编译器报错
- 把示例封装成函数，思考接口应该如何设计
---

## 24. find/count/any_of

### 知识点目标

- 算法表达意图比手写循环更清楚
- 注意迭代器范围是左闭右开
- 谓词不要有隐藏副作用

### 核心代码

```cpp
#include <algorithm>
#include <iostream>
#include <vector>

int main() { std::vector<int> v{1,2,3,2}; bool has_even = std::any_of(v.begin(), v.end(), [](int x){ return x % 2 == 0; }); std::cout << std::count(v.begin(), v.end(), 2) << ' ' << has_even << '\n'; }
```

### 关键注释

- 代码块是单文件 C++17 示例，可直接放到 playground 运行
- 中文注释标出正式用法或易错边界
- 输出用于帮助确认行为

### 常见易错点

- 只记 API 名字，不理解生命周期和失效规则
- 把演示代码里的简化写法直接搬到复杂项目
- 忽略异常、并发或所有权边界

### 面试表达

我会用这段代码先说明知识点解决什么问题，再指出实际项目里的边界，例如所有权、迭代器失效、线程同步或异常安全。

### 扩展练习

- 修改输入数据，观察输出变化
- 故意打开注释里的错误写法，理解编译器报错
- 把示例封装成函数，思考接口应该如何设计
---

## 25. erase-remove idiom

### 知识点目标

- remove 不改变容器大小
- erase 才真正删除尾部垃圾区间
- 适用于 vector/string/deque 等顺序容器

### 核心代码

```cpp
#include <algorithm>
#include <iostream>
#include <vector>

int main() { std::vector<int> v{1,2,3,2}; v.erase(std::remove(v.begin(), v.end(), 2), v.end()); for (int x : v) std::cout << x; }
```

### 关键注释

- 代码块是单文件 C++17 示例，可直接放到 playground 运行
- 中文注释标出正式用法或易错边界
- 输出用于帮助确认行为

### 常见易错点

- 只记 API 名字，不理解生命周期和失效规则
- 把演示代码里的简化写法直接搬到复杂项目
- 忽略异常、并发或所有权边界

### 面试表达

我会用这段代码先说明知识点解决什么问题，再指出实际项目里的边界，例如所有权、迭代器失效、线程同步或异常安全。

### 扩展练习

- 修改输入数据，观察输出变化
- 故意打开注释里的错误写法，理解编译器报错
- 把示例封装成函数，思考接口应该如何设计
---

## 26. lambda 捕获

### 知识点目标

- 值捕获适合延迟执行
- 引用捕获要保证被引用对象仍存活
- 捕获列表应尽量明确

### 核心代码

```cpp
#include <functional>
#include <iostream>

std::function<int()> makeTask() { int value = 42; return [value]{ return value; }; }
int main() { std::cout << makeTask()() << '\n'; }
```

### 关键注释

- 代码块是单文件 C++17 示例，可直接放到 playground 运行
- 中文注释标出正式用法或易错边界
- 输出用于帮助确认行为

### 常见易错点

- 只记 API 名字，不理解生命周期和失效规则
- 把演示代码里的简化写法直接搬到复杂项目
- 忽略异常、并发或所有权边界

### 面试表达

我会用这段代码先说明知识点解决什么问题，再指出实际项目里的边界，例如所有权、迭代器失效、线程同步或异常安全。

### 扩展练习

- 修改输入数据，观察输出变化
- 故意打开注释里的错误写法，理解编译器报错
- 把示例封装成函数，思考接口应该如何设计
---

## 27. 结构化绑定

### 知识点目标

- 可读性更好
- map 遍历常用 `const auto& [k,v]`
- 按值绑定会拷贝 pair

### 核心代码

```cpp
#include <iostream>
#include <map>

int main() { std::map<int, const char*> m{{1,"one"}}; for (const auto& [id, name] : m) std::cout << id << ':' << name << '\n'; }
```

### 关键注释

- 代码块是单文件 C++17 示例，可直接放到 playground 运行
- 中文注释标出正式用法或易错边界
- 输出用于帮助确认行为

### 常见易错点

- 只记 API 名字，不理解生命周期和失效规则
- 把演示代码里的简化写法直接搬到复杂项目
- 忽略异常、并发或所有权边界

### 面试表达

我会用这段代码先说明知识点解决什么问题，再指出实际项目里的边界，例如所有权、迭代器失效、线程同步或异常安全。

### 扩展练习

- 修改输入数据，观察输出变化
- 故意打开注释里的错误写法，理解编译器报错
- 把示例封装成函数，思考接口应该如何设计
---

## 28. RAII 管理锁

### 知识点目标

- lock_guard 构造时加锁析构时解锁
- 异常路径也会释放锁
- 共享数据访问要放在临界区

### 核心代码

```cpp
#include <iostream>
#include <mutex>

int main() { std::mutex m; int value = 0; { std::lock_guard<std::mutex> lock(m); ++value; } std::cout << value << '\n'; }
```

### 关键注释

- 代码块是单文件 C++17 示例，可直接放到 playground 运行
- 中文注释标出正式用法或易错边界
- 输出用于帮助确认行为

### 常见易错点

- 只记 API 名字，不理解生命周期和失效规则
- 把演示代码里的简化写法直接搬到复杂项目
- 忽略异常、并发或所有权边界

### 面试表达

我会用这段代码先说明知识点解决什么问题，再指出实际项目里的边界，例如所有权、迭代器失效、线程同步或异常安全。

### 扩展练习

- 修改输入数据，观察输出变化
- 故意打开注释里的错误写法，理解编译器报错
- 把示例封装成函数，思考接口应该如何设计
---

## 29. `unique_ptr` 独占所有权

### 知识点目标

- 不能拷贝，只能移动
- 适合表达唯一拥有者
- 优先用 make_unique

### 核心代码

```cpp
#include <iostream>
#include <memory>

int main() { auto p = std::make_unique<int>(7); auto q = std::move(p); std::cout << *q << ' ' << (p == nullptr) << '\n'; }
```

### 关键注释

- 代码块是单文件 C++17 示例，可直接放到 playground 运行
- 中文注释标出正式用法或易错边界
- 输出用于帮助确认行为

### 常见易错点

- 只记 API 名字，不理解生命周期和失效规则
- 把演示代码里的简化写法直接搬到复杂项目
- 忽略异常、并发或所有权边界

### 面试表达

我会用这段代码先说明知识点解决什么问题，再指出实际项目里的边界，例如所有权、迭代器失效、线程同步或异常安全。

### 扩展练习

- 修改输入数据，观察输出变化
- 故意打开注释里的错误写法，理解编译器报错
- 把示例封装成函数，思考接口应该如何设计
---

## 30. `shared_ptr` 共享所有权

### 知识点目标

- 引用计数管理共享生命周期
- 拷贝会增加 use_count
- 不要用它替代所有裸指针观察关系

### 核心代码

```cpp
#include <iostream>
#include <memory>

int main() { auto a = std::make_shared<int>(5); auto b = a; std::cout << *b << ' ' << a.use_count() << '\n'; }
```

### 关键注释

- 代码块是单文件 C++17 示例，可直接放到 playground 运行
- 中文注释标出正式用法或易错边界
- 输出用于帮助确认行为

### 常见易错点

- 只记 API 名字，不理解生命周期和失效规则
- 把演示代码里的简化写法直接搬到复杂项目
- 忽略异常、并发或所有权边界

### 面试表达

我会用这段代码先说明知识点解决什么问题，再指出实际项目里的边界，例如所有权、迭代器失效、线程同步或异常安全。

### 扩展练习

- 修改输入数据，观察输出变化
- 故意打开注释里的错误写法，理解编译器报错
- 把示例封装成函数，思考接口应该如何设计
---

## 31. `weak_ptr::lock`

### 知识点目标

- weak_ptr 不增加所有权
- lock 返回 shared_ptr 或空
- 使用前必须检查

### 核心代码

```cpp
#include <iostream>
#include <memory>

int main() { std::weak_ptr<int> w; { auto p = std::make_shared<int>(9); w = p; if (auto alive = w.lock()) std::cout << *alive << '\n'; } std::cout << (w.expired() ? "expired" : "alive") << '\n'; }
```

### 关键注释

- 代码块是单文件 C++17 示例，可直接放到 playground 运行
- 中文注释标出正式用法或易错边界
- 输出用于帮助确认行为

### 常见易错点

- 只记 API 名字，不理解生命周期和失效规则
- 把演示代码里的简化写法直接搬到复杂项目
- 忽略异常、并发或所有权边界

### 面试表达

我会用这段代码先说明知识点解决什么问题，再指出实际项目里的边界，例如所有权、迭代器失效、线程同步或异常安全。

### 扩展练习

- 修改输入数据，观察输出变化
- 故意打开注释里的错误写法，理解编译器报错
- 把示例封装成函数，思考接口应该如何设计
---

## 32. make_unique/make_shared

### 知识点目标

- 避免裸 new
- 异常安全更好
- make_shared 通常一次分配对象和控制块

### 核心代码

```cpp
#include <iostream>
#include <memory>
#include <string>

int main() { auto name = std::make_unique<std::string>("cpp"); auto count = std::make_shared<int>(3); std::cout << *name << ' ' << *count << '\n'; }
```

### 关键注释

- 代码块是单文件 C++17 示例，可直接放到 playground 运行
- 中文注释标出正式用法或易错边界
- 输出用于帮助确认行为

### 常见易错点

- 只记 API 名字，不理解生命周期和失效规则
- 把演示代码里的简化写法直接搬到复杂项目
- 忽略异常、并发或所有权边界

### 面试表达

我会用这段代码先说明知识点解决什么问题，再指出实际项目里的边界，例如所有权、迭代器失效、线程同步或异常安全。

### 扩展练习

- 修改输入数据，观察输出变化
- 故意打开注释里的错误写法，理解编译器报错
- 把示例封装成函数，思考接口应该如何设计
---

## 33. 自定义 deleter

### 知识点目标

- 把释放策略放进智能指针
- 适合 C API 资源
- deleter 类型会影响 unique_ptr 类型

### 核心代码

```cpp
#include <cstdio>
#include <iostream>
#include <memory>

int main() { using FilePtr = std::unique_ptr<FILE, decltype(&std::fclose)>; FilePtr file(std::tmpfile(), &std::fclose); if (file) std::cout << "file ok\n"; }
```

### 关键注释

- 代码块是单文件 C++17 示例，可直接放到 playground 运行
- 中文注释标出正式用法或易错边界
- 输出用于帮助确认行为

### 常见易错点

- 只记 API 名字，不理解生命周期和失效规则
- 把演示代码里的简化写法直接搬到复杂项目
- 忽略异常、并发或所有权边界

### 面试表达

我会用这段代码先说明知识点解决什么问题，再指出实际项目里的边界，例如所有权、迭代器失效、线程同步或异常安全。

### 扩展练习

- 修改输入数据，观察输出变化
- 故意打开注释里的错误写法，理解编译器报错
- 把示例封装成函数，思考接口应该如何设计
---

## 34. `std::optional`

### 知识点目标

- 表达可能没有值
- 避免魔法返回值
- 使用前检查 has_value

### 核心代码

```cpp
#include <iostream>
#include <optional>
#include <string>

std::optional<int> parse(const std::string& s) { if (s.empty()) return std::nullopt; return std::stoi(s); }
int main() { if (auto v = parse("42")) std::cout << *v << '\n'; }
```

### 关键注释

- 代码块是单文件 C++17 示例，可直接放到 playground 运行
- 中文注释标出正式用法或易错边界
- 输出用于帮助确认行为

### 常见易错点

- 只记 API 名字，不理解生命周期和失效规则
- 把演示代码里的简化写法直接搬到复杂项目
- 忽略异常、并发或所有权边界

### 面试表达

我会用这段代码先说明知识点解决什么问题，再指出实际项目里的边界，例如所有权、迭代器失效、线程同步或异常安全。

### 扩展练习

- 修改输入数据，观察输出变化
- 故意打开注释里的错误写法，理解编译器报错
- 把示例封装成函数，思考接口应该如何设计
---

## 35. `std::variant`

### 知识点目标

- 类型安全地持有多个候选类型之一
- visit 统一处理当前值
- 适合封闭类型集合

### 核心代码

```cpp
#include <iostream>
#include <string>
#include <variant>

int main() { std::variant<int, std::string> v = std::string{"ok"}; std::visit([](const auto& x){ std::cout << x << '\n'; }, v); }
```

### 关键注释

- 代码块是单文件 C++17 示例，可直接放到 playground 运行
- 中文注释标出正式用法或易错边界
- 输出用于帮助确认行为

### 常见易错点

- 只记 API 名字，不理解生命周期和失效规则
- 把演示代码里的简化写法直接搬到复杂项目
- 忽略异常、并发或所有权边界

### 面试表达

我会用这段代码先说明知识点解决什么问题，再指出实际项目里的边界，例如所有权、迭代器失效、线程同步或异常安全。

### 扩展练习

- 修改输入数据，观察输出变化
- 故意打开注释里的错误写法，理解编译器报错
- 把示例封装成函数，思考接口应该如何设计
---

## 36. `std::string_view` 生命周期

### 知识点目标

- 不拥有字符串
- 适合只读入参
- 不要保存指向临时对象的 view

### 核心代码

```cpp
#include <iostream>
#include <string>
#include <string_view>

void print(std::string_view s) { std::cout << s << '\n'; }
int main() { std::string text = "hello"; print(text); print("literal"); }
```

### 关键注释

- 代码块是单文件 C++17 示例，可直接放到 playground 运行
- 中文注释标出正式用法或易错边界
- 输出用于帮助确认行为

### 常见易错点

- 只记 API 名字，不理解生命周期和失效规则
- 把演示代码里的简化写法直接搬到复杂项目
- 忽略异常、并发或所有权边界

### 面试表达

我会用这段代码先说明知识点解决什么问题，再指出实际项目里的边界，例如所有权、迭代器失效、线程同步或异常安全。

### 扩展练习

- 修改输入数据，观察输出变化
- 故意打开注释里的错误写法，理解编译器报错
- 把示例封装成函数，思考接口应该如何设计
---

## 37. `if constexpr`

### 知识点目标

- 编译期分支
- 未选分支不会实例化
- 适合泛型代码按类型选择行为

### 核心代码

```cpp
#include <iostream>
#include <string>
#include <type_traits>

template <typename T> void print(const T& v) { if constexpr (std::is_integral_v<T>) std::cout << "int-like " << v << '\n'; else std::cout << "other " << v << '\n'; }
int main() { print(1); print(std::string{"x"}); }
```

### 关键注释

- 代码块是单文件 C++17 示例，可直接放到 playground 运行
- 中文注释标出正式用法或易错边界
- 输出用于帮助确认行为

### 常见易错点

- 只记 API 名字，不理解生命周期和失效规则
- 把演示代码里的简化写法直接搬到复杂项目
- 忽略异常、并发或所有权边界

### 面试表达

我会用这段代码先说明知识点解决什么问题，再指出实际项目里的边界，例如所有权、迭代器失效、线程同步或异常安全。

### 扩展练习

- 修改输入数据，观察输出变化
- 故意打开注释里的错误写法，理解编译器报错
- 把示例封装成函数，思考接口应该如何设计
---

## 38. 折叠表达式

### 知识点目标

- 展开参数包
- 可替代递归模板
- 适合求和和批量输出

### 核心代码

```cpp
#include <iostream>

template <typename... Ts> auto sum(Ts... xs) { return (xs + ...); }
int main() { std::cout << sum(1,2,3,4) << '\n'; }
```

### 关键注释

- 代码块是单文件 C++17 示例，可直接放到 playground 运行
- 中文注释标出正式用法或易错边界
- 输出用于帮助确认行为

### 常见易错点

- 只记 API 名字，不理解生命周期和失效规则
- 把演示代码里的简化写法直接搬到复杂项目
- 忽略异常、并发或所有权边界

### 面试表达

我会用这段代码先说明知识点解决什么问题，再指出实际项目里的边界，例如所有权、迭代器失效、线程同步或异常安全。

### 扩展练习

- 修改输入数据，观察输出变化
- 故意打开注释里的错误写法，理解编译器报错
- 把示例封装成函数，思考接口应该如何设计
---

## 39. `std::function` 类型擦除

### 知识点目标

- 统一保存不同 callable
- 有间接调用成本
- 适合回调接口

### 核心代码

```cpp
#include <functional>
#include <iostream>
#include <vector>

int main() { std::vector<std::function<void()>> tasks; tasks.push_back([]{ std::cout << "task\n"; }); for (auto& task : tasks) task(); }
```

### 关键注释

- 代码块是单文件 C++17 示例，可直接放到 playground 运行
- 中文注释标出正式用法或易错边界
- 输出用于帮助确认行为

### 常见易错点

- 只记 API 名字，不理解生命周期和失效规则
- 把演示代码里的简化写法直接搬到复杂项目
- 忽略异常、并发或所有权边界

### 面试表达

我会用这段代码先说明知识点解决什么问题，再指出实际项目里的边界，例如所有权、迭代器失效、线程同步或异常安全。

### 扩展练习

- 修改输入数据，观察输出变化
- 故意打开注释里的错误写法，理解编译器报错
- 把示例封装成函数，思考接口应该如何设计
---

## 40. `std::thread` join

### 知识点目标

- thread 对象析构前必须 join 或 detach
- join 等待线程完成
- 优先让生命周期清晰

### 核心代码

```cpp
#include <iostream>
#include <thread>

int main() { std::thread worker([]{ std::cout << "work\n"; }); worker.join(); }
```

### 关键注释

- 代码块是单文件 C++17 示例，可直接放到 playground 运行
- 中文注释标出正式用法或易错边界
- 输出用于帮助确认行为

### 常见易错点

- 只记 API 名字，不理解生命周期和失效规则
- 把演示代码里的简化写法直接搬到复杂项目
- 忽略异常、并发或所有权边界

### 面试表达

我会用这段代码先说明知识点解决什么问题，再指出实际项目里的边界，例如所有权、迭代器失效、线程同步或异常安全。

### 扩展练习

- 修改输入数据，观察输出变化
- 故意打开注释里的错误写法，理解编译器报错
- 把示例封装成函数，思考接口应该如何设计
---

## 41. mutex + lock_guard

### 知识点目标

- mutex 保护共享数据
- lock_guard 用 RAII 管锁
- 临界区越小越好

### 核心代码

```cpp
#include <iostream>
#include <mutex>
#include <thread>

int main() { std::mutex m; int counter = 0; auto work = [&]{ for (int i=0;i<1000;++i) { std::lock_guard<std::mutex> lock(m); ++counter; } }; std::thread a(work), b(work); a.join(); b.join(); std::cout << counter << '\n'; }
```

### 关键注释

- 代码块是单文件 C++17 示例，可直接放到 playground 运行
- 中文注释标出正式用法或易错边界
- 输出用于帮助确认行为

### 常见易错点

- 只记 API 名字，不理解生命周期和失效规则
- 把演示代码里的简化写法直接搬到复杂项目
- 忽略异常、并发或所有权边界

### 面试表达

我会用这段代码先说明知识点解决什么问题，再指出实际项目里的边界，例如所有权、迭代器失效、线程同步或异常安全。

### 扩展练习

- 修改输入数据，观察输出变化
- 故意打开注释里的错误写法，理解编译器报错
- 把示例封装成函数，思考接口应该如何设计
---

## 42. unique_lock + condition_variable

### 知识点目标

- wait 会释放锁并阻塞
- 被唤醒后重新持锁
- 必须用谓词防止虚假唤醒

### 核心代码

```cpp
#include <condition_variable>
#include <iostream>
#include <mutex>
#include <thread>

int main() { std::mutex m; std::condition_variable cv; bool ready=false; std::thread worker([&]{ std::unique_lock<std::mutex> lock(m); cv.wait(lock, [&]{ return ready; }); std::cout << "ready\n"; }); { std::lock_guard<std::mutex> lock(m); ready=true; } cv.notify_one(); worker.join(); }
```

### 关键注释

- 代码块是单文件 C++17 示例，可直接放到 playground 运行
- 中文注释标出正式用法或易错边界
- 输出用于帮助确认行为

### 常见易错点

- 只记 API 名字，不理解生命周期和失效规则
- 把演示代码里的简化写法直接搬到复杂项目
- 忽略异常、并发或所有权边界

### 面试表达

我会用这段代码先说明知识点解决什么问题，再指出实际项目里的边界，例如所有权、迭代器失效、线程同步或异常安全。

### 扩展练习

- 修改输入数据，观察输出变化
- 故意打开注释里的错误写法，理解编译器报错
- 把示例封装成函数，思考接口应该如何设计
---

## 43. atomic counter

### 知识点目标

- atomic 适合简单共享计数
- fetch_add 是读改写原子操作
- 复杂不变量仍需 mutex

### 核心代码

```cpp
#include <atomic>
#include <iostream>
#include <thread>

int main() { std::atomic<int> counter{0}; auto work=[&]{ for(int i=0;i<1000;++i) counter.fetch_add(1); }; std::thread a(work), b(work); a.join(); b.join(); std::cout << counter.load() << '\n'; }
```

### 关键注释

- 代码块是单文件 C++17 示例，可直接放到 playground 运行
- 中文注释标出正式用法或易错边界
- 输出用于帮助确认行为

### 常见易错点

- 只记 API 名字，不理解生命周期和失效规则
- 把演示代码里的简化写法直接搬到复杂项目
- 忽略异常、并发或所有权边界

### 面试表达

我会用这段代码先说明知识点解决什么问题，再指出实际项目里的边界，例如所有权、迭代器失效、线程同步或异常安全。

### 扩展练习

- 修改输入数据，观察输出变化
- 故意打开注释里的错误写法，理解编译器报错
- 把示例封装成函数，思考接口应该如何设计
---

## 44. promise/future

### 知识点目标

- promise 设置结果
- future 获取结果并同步等待
- 适合跨线程结果交付

### 核心代码

```cpp
#include <future>
#include <iostream>
#include <thread>

int main() { std::promise<int> p; auto f = p.get_future(); std::thread worker([&]{ p.set_value(42); }); std::cout << f.get() << '\n'; worker.join(); }
```

### 关键注释

- 代码块是单文件 C++17 示例，可直接放到 playground 运行
- 中文注释标出正式用法或易错边界
- 输出用于帮助确认行为

### 常见易错点

- 只记 API 名字，不理解生命周期和失效规则
- 把演示代码里的简化写法直接搬到复杂项目
- 忽略异常、并发或所有权边界

### 面试表达

我会用这段代码先说明知识点解决什么问题，再指出实际项目里的边界，例如所有权、迭代器失效、线程同步或异常安全。

### 扩展练习

- 修改输入数据，观察输出变化
- 故意打开注释里的错误写法，理解编译器报错
- 把示例封装成函数，思考接口应该如何设计
---

## 45. async

### 知识点目标

- 更高层地启动异步任务
- future 保存结果
- launch::async 明确异步执行

### 核心代码

```cpp
#include <future>
#include <iostream>

int main() { auto f = std::async(std::launch::async, []{ return 21 * 2; }); std::cout << f.get() << '\n'; }
```

### 关键注释

- 代码块是单文件 C++17 示例，可直接放到 playground 运行
- 中文注释标出正式用法或易错边界
- 输出用于帮助确认行为

### 常见易错点

- 只记 API 名字，不理解生命周期和失效规则
- 把演示代码里的简化写法直接搬到复杂项目
- 忽略异常、并发或所有权边界

### 面试表达

我会用这段代码先说明知识点解决什么问题，再指出实际项目里的边界，例如所有权、迭代器失效、线程同步或异常安全。

### 扩展练习

- 修改输入数据，观察输出变化
- 故意打开注释里的错误写法，理解编译器报错
- 把示例封装成函数，思考接口应该如何设计
---

## 46. 头文件组织

### 知识点目标

- 头文件暴露接口
- 源文件隐藏实现
- 示例用单文件模拟头/源拆分

### 核心代码

```cpp
#include <iostream>
#include <string>

class User { public: explicit User(std::string name) : name_(std::move(name)) {} const std::string& name() const { return name_; } private: std::string name_; };
int main() { User u("Ada"); std::cout << u.name() << '\n'; }
```

### 关键注释

- 代码块是单文件 C++17 示例，可直接放到 playground 运行
- 中文注释标出正式用法或易错边界
- 输出用于帮助确认行为

### 常见易错点

- 只记 API 名字，不理解生命周期和失效规则
- 把演示代码里的简化写法直接搬到复杂项目
- 忽略异常、并发或所有权边界

### 面试表达

我会用这段代码先说明知识点解决什么问题，再指出实际项目里的边界，例如所有权、迭代器失效、线程同步或异常安全。

### 扩展练习

- 修改输入数据，观察输出变化
- 故意打开注释里的错误写法，理解编译器报错
- 把示例封装成函数，思考接口应该如何设计
---

## 47. namespace

### 知识点目标

- 避免名字冲突
- 公共 API 应放在明确命名空间
- 头文件避免 using namespace

### 核心代码

```cpp
#include <iostream>

namespace project { int add(int a, int b) { return a + b; } }
int main() { std::cout << project::add(1, 2) << '\n'; }
```

### 关键注释

- 代码块是单文件 C++17 示例，可直接放到 playground 运行
- 中文注释标出正式用法或易错边界
- 输出用于帮助确认行为

### 常见易错点

- 只记 API 名字，不理解生命周期和失效规则
- 把演示代码里的简化写法直接搬到复杂项目
- 忽略异常、并发或所有权边界

### 面试表达

我会用这段代码先说明知识点解决什么问题，再指出实际项目里的边界，例如所有权、迭代器失效、线程同步或异常安全。

### 扩展练习

- 修改输入数据，观察输出变化
- 故意打开注释里的错误写法，理解编译器报错
- 把示例封装成函数，思考接口应该如何设计
---

## 48. 异常 try/catch

### 知识点目标

- throw 表达异常失败
- catch 处理具体异常
- RAII 负责异常路径清理

### 核心代码

```cpp
#include <iostream>
#include <stdexcept>

int parse(bool ok) { if (!ok) throw std::runtime_error("bad input"); return 1; }
int main() { try { std::cout << parse(false) << '\n'; } catch (const std::exception& e) { std::cout << e.what() << '\n'; } }
```

### 关键注释

- 代码块是单文件 C++17 示例，可直接放到 playground 运行
- 中文注释标出正式用法或易错边界
- 输出用于帮助确认行为

### 常见易错点

- 只记 API 名字，不理解生命周期和失效规则
- 把演示代码里的简化写法直接搬到复杂项目
- 忽略异常、并发或所有权边界

### 面试表达

我会用这段代码先说明知识点解决什么问题，再指出实际项目里的边界，例如所有权、迭代器失效、线程同步或异常安全。

### 扩展练习

- 修改输入数据，观察输出变化
- 故意打开注释里的错误写法，理解编译器报错
- 把示例封装成函数，思考接口应该如何设计
---

## 49. operator overloading

### 知识点目标

- 只在语义自然时重载
- 保持直觉行为
- 不要改变调用者预期

### 核心代码

```cpp
#include <iostream>

struct Point { int x; int y; };
Point operator+(Point a, Point b) { return {a.x + b.x, a.y + b.y}; }
int main() { Point p = Point{1,2} + Point{3,4}; std::cout << p.x << ',' << p.y << '\n'; }
```

### 关键注释

- 代码块是单文件 C++17 示例，可直接放到 playground 运行
- 中文注释标出正式用法或易错边界
- 输出用于帮助确认行为

### 常见易错点

- 只记 API 名字，不理解生命周期和失效规则
- 把演示代码里的简化写法直接搬到复杂项目
- 忽略异常、并发或所有权边界

### 面试表达

我会用这段代码先说明知识点解决什么问题，再指出实际项目里的边界，例如所有权、迭代器失效、线程同步或异常安全。

### 扩展练习

- 修改输入数据，观察输出变化
- 故意打开注释里的错误写法，理解编译器报错
- 把示例封装成函数，思考接口应该如何设计
---

## 50. 编译/链接错误对比

### 知识点目标

- 编译错误多来自语法和类型检查
- 链接错误多来自声明存在但定义缺失
- 单文件示例展示正确声明和定义配对

### 核心代码

```cpp
#include <iostream>

void print(); // 中文注释：只有声明还不够，最终必须有定义
int main() { print(); }
void print() { std::cout << "linked\n"; } // 中文注释：如果删掉这个定义，会出现链接错误
```

### 关键注释

- 代码块是单文件 C++17 示例，可直接放到 playground 运行
- 中文注释标出正式用法或易错边界
- 输出用于帮助确认行为

### 常见易错点

- 只记 API 名字，不理解生命周期和失效规则
- 把演示代码里的简化写法直接搬到复杂项目
- 忽略异常、并发或所有权边界

### 面试表达

我会用这段代码先说明知识点解决什么问题，再指出实际项目里的边界，例如所有权、迭代器失效、线程同步或异常安全。

### 扩展练习

- 修改输入数据，观察输出变化
- 故意打开注释里的错误写法，理解编译器报错
- 把示例封装成函数，思考接口应该如何设计
