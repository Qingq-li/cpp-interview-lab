# C++ Lambda 捕获、`const operator()` 与 `this` 访问详解

这份笔记解释截图中的核心问题：

> 为什么 lambda 使用 `[=]` 值捕获时，不能修改普通局部变量 `local`，却可以通过成员函数修改成员变量 `queue_`？

关键结论：

> 默认情况下，lambda 的 `operator()` 是 `const` 成员函数。  
> `const` 只保护 lambda 对象自身的成员，也就是被捕获进 lambda 内部的变量副本。  
> 但是 `[=]` 中对成员变量的访问，本质上是通过捕获到的 `this` 指针访问外部对象。`const operator()` 让 `this` 指针这个副本不能被重新赋值，但不让 `*this` 变成只读对象。

---

## 示例背景

假设在某个类的成员函数中有如下代码：

```cpp
int local = 10;

auto lam1 = [this] {
    queue_.push(5);
};

auto lam2 = [&] {
    queue_.push(5);
    local = 20;
};

auto lam3 = [=] {
    queue_.push(5);
    // local = 20; // 编译错误
};

auto lam4 = [=] {
    return local + queue_.size();
};
```

运行结果可能类似：

```text
[this] queue_.size() = 1
[&]    local = 20
[&]    queue_.size() = 2
[=]    local = 20（未变，只能读副本）
[=]    queue_.size() = 3
[=]    lam4() = 21
```

这里体现了三件事：

1. `[this]` 捕获 `this`，可以访问成员变量 `queue_`。
2. `[&]` 引用捕获局部变量，所以可以修改外部的 `local`。
3. `[=]` 值捕获局部变量，`local` 在 lambda 内部是副本；默认 `operator()` 是 `const`，所以不能修改这个副本。

---

## Lambda 本质上是什么

Lambda 表达式会被编译器转换成一个匿名类对象，也叫闭包对象。

例如：

```cpp
int local = 10;

auto f = [=] {
    return local + 1;
};
```

可以近似理解成：

```cpp
class __Lambda {
private:
    int local_copy;

public:
    __Lambda(int local)
        : local_copy(local)
    {
    }

    int operator()() const
    {
        return local_copy + 1;
    }
};

auto f = __Lambda(local);
```

重点是：

```cpp
int operator()() const
```

默认情况下，lambda 的调用运算符是 `const` 的。

因此，在 lambda 函数体中，不能修改闭包对象自己的成员变量。

---

## `[=]` 为什么不能修改 `local`

代码：

```cpp
int local = 10;

auto lam = [=] {
    // local = 20; // 编译错误
};
```

`[=]` 表示按值捕获使用到的局部变量。`local` 会被复制一份到 lambda 对象内部。

近似展开：

```cpp
class __Lambda {
private:
    int local_copy;

public:
    __Lambda(int local)
        : local_copy(local)
    {
    }

    void operator()() const
    {
        // local_copy = 20; // 错误：operator() 是 const
    }
};
```

因为 `operator() const` 中不能修改成员变量，所以 `local_copy = 20` 不允许。

注意：这里不是外部的 `local` 被保护了，而是 lambda 内部的 `local` 副本被保护了。

---

## `[&]` 为什么可以修改 `local`

代码：

```cpp
int local = 10;

auto lam = [&] {
    local = 20;
};
```

`[&]` 表示按引用捕获使用到的局部变量。lambda 内部保存的是外部 `local` 的引用。

近似展开：

```cpp
class __Lambda {
private:
    int& local_ref;

public:
    __Lambda(int& local)
        : local_ref(local)
    {
    }

    void operator()() const
    {
        local_ref = 20; // 可以：修改的是引用指向的外部对象
    }
};
```

虽然 `operator()` 仍然是 `const`，但 `const` 保护的是 lambda 对象自身的成员。

`local_ref` 这个引用成员本身不能重新绑定到别的对象，但它引用的外部 `local` 可以被修改。

这和指针很像：

```cpp
int x = 10;
int* const p = &x; // p 本身不能改，但 *p 可以改

*p = 20;           // 可以
// p = nullptr;    // 不可以
```

---

## `[this]` 捕获了什么

在类的非静态成员函数中，访问成员变量：

```cpp
queue_.push(5);
```

本质上等价于：

```cpp
this->queue_.push(5);
```

所以 lambda 中如果要访问成员变量，需要能访问 `this`。

代码：

```cpp
auto lam = [this] {
    queue_.push(5);
};
```

近似展开：

```cpp
class __Lambda {
private:
    MyClass* this_ptr;

public:
    __Lambda(MyClass* p)
        : this_ptr(p)
    {
    }

    void operator()() const
    {
        this_ptr->queue_.push(5);
    }
};
```

这里的关键点：

```cpp
void operator()() const
```

会让 `this_ptr` 这个指针成员本身不可修改，近似于：

```cpp
MyClass* const this_ptr;
```

但它不会把指针指向的对象变成 `const MyClass`。

所以：

```cpp
this_ptr->queue_.push(5);
```

仍然可以修改外部对象中的 `queue_`。

---

## `[=]` 为什么也能修改 `queue_`

在成员函数中写：

```cpp
auto lam = [=] {
    queue_.push(5);
};
```

很多人容易误解为：

> `[=]` 把 `queue_` 按值复制了一份。

这不是它实际做的事情。

在 C++17 及更早语义中，`[=]` 在成员函数里访问成员变量时，会隐式捕获 `this` 指针。也就是说：

```cpp
auto lam = [=] {
    queue_.push(5);
};
```

近似等价于：

```cpp
auto lam = [this] {
    this->queue_.push(5);
};
```

因此，`queue_` 不是被按值复制进 lambda；lambda 只是保存了一个 `this` 指针副本。

近似展开：

```cpp
class __Lambda {
private:
    MyClass* this_ptr;

public:
    __Lambda(MyClass* p)
        : this_ptr(p)
    {
    }

    void operator()() const
    {
        this_ptr->queue_.push(5);
    }
};
```

所以 `[=]` 下：

- `local` 是值捕获的副本，受 `operator() const` 保护，不能修改。
- `queue_` 是通过 `this` 指针访问的外部对象成员，不是 lambda 自己的成员副本，可以修改。

---

## 对比表：`local` 和 `queue_`

| 对象 | 在 lambda 中的访问方式 | 是否是 lambda 自己的成员 | 是否受 `operator() const` 保护 | 默认能否修改 |
|---|---|---:|---:|---:|
| `local` | `[=]` 时复制为闭包对象内部成员 | 是 | 是 | 否 |
| `local` | `[&]` 时保存引用 | 引用成员本身是，外部对象不是 | 只保护引用成员本身 | 是 |
| `queue_` | 通过 `this->queue_` 访问 | 否，属于外部对象 | 否 | 是 |
| `this` 指针副本 | lambda 内部保存的指针 | 是 | 是 | 指针不能改，指向对象可改 |

核心区别：

```text
local  是捕获进 lambda 的变量副本
queue_ 是通过 this 指向外部对象后访问到的成员
```

---

## `mutable` 的作用

如果希望按值捕获的变量副本可以在 lambda 内部被修改，可以加 `mutable`。

```cpp
int local = 10;

auto lam = [=]() mutable {
    local = 20; // 可以修改 lambda 内部的副本
};

lam();

// 外部 local 仍然是 10
```

`mutable` 的作用是让 lambda 的 `operator()` 不再是 `const`。

近似展开：

```cpp
class __Lambda {
private:
    int local_copy;

public:
    void operator()()
    {
        local_copy = 20; // 可以
    }
};
```

注意：

`mutable` 修改的是 lambda 内部的副本，不会修改外部原始变量。

---

## `[=]`、`[&]`、`[this]` 的行为对比

### `[this]`

```cpp
auto lam = [this] {
    queue_.push(5);
};
```

含义：

- 显式捕获当前对象的 `this` 指针。
- 可以访问成员变量和成员函数。
- 修改的是外部对象本身。
- 不捕获普通局部变量，除非单独写出来。

例如：

```cpp
int local = 10;

auto lam = [this] {
    queue_.push(5);
    // local = 20; // 错误：local 没有被捕获
};
```

### `[&]`

```cpp
auto lam = [&] {
    queue_.push(5);
    local = 20;
};
```

含义：

- 默认按引用捕获使用到的局部变量。
- 在成员函数中访问成员变量时，也会使用 `this`。
- 可以修改外部 `local`。
- 可以修改外部对象的 `queue_`。

### `[=]`

```cpp
auto lam = [=] {
    queue_.push(5);
    // local = 20; // 错误
};
```

含义：

- 默认按值捕获使用到的局部变量。
- `local` 进入 lambda 后是一个副本。
- 默认 `operator()` 是 `const`，所以不能修改这个副本。
- 在成员函数中访问成员变量时，实际是通过 `this` 指针访问。
- 因为 `this` 指向的外部对象不是 const，所以可以修改 `queue_`。

---

## C++20 之后的注意点

在 C++20 中，`[=]` 隐式捕获 `this` 的行为被弃用。

也就是说，虽然很多编译器仍然支持：

```cpp
auto lam = [=] {
    queue_.push(5);
};
```

但更推荐显式写出意图：

```cpp
auto lam = [this] {
    queue_.push(5);
};
```

或者，如果既要值捕获局部变量，又要访问当前对象：

```cpp
auto lam = [=, this] {
    queue_.push(5);
    std::cout << local << '\n';
};
```

如果想复制整个当前对象，而不是只捕获 `this` 指针，可以使用：

```cpp
auto lam = [*this] {
    // 这里访问的是当前对象的副本
};
```

`[*this]` 和 `[this]` 的区别很大：

| 捕获方式 | 捕获内容 | 修改影响 |
|---|---|---|
| `[this]` | 当前对象指针 | 修改原对象 |
| `[*this]` | 当前对象副本 | 修改副本，不改原对象 |

---

## 最容易混淆的一句话

`[=]` 不是“所有东西都复制”。

更准确地说：

```text
[=] 会按值捕获用到的局部变量；
在成员函数中访问成员变量时，成员变量不是局部变量；
访问成员变量需要 this；
所以成员变量通常是通过 this 指针访问的。
```

因此：

```cpp
auto lam = [=] {
    queue_.push(5); // 修改外部对象
    // local = 20;  // 不能修改值捕获副本
};
```

---

## 一句话总结

`const operator()` 只能管住 lambda 自己内部保存的捕获成员，例如按值捕获的 `local` 副本；它管不住 `this->queue_`，因为 `queue_` 属于 lambda 外部的对象，lambda 只是保存了一个指向该对象的 `this` 指针。

---

# CMakeLists.txt：最小可行配置与 `target_compile_options`

截图中的 `CMakeLists.txt` 已经是一个足够小、足够清楚的可行配置：

```cmake
cmake_minimum_required(VERSION 3.16)
project(test_sensor_logger_project)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(ThreadSafeQueue src/ThreadSafeQueue.cpp)

target_include_directories(ThreadSafeQueue
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)
```

这份配置已经完成了几件关键工作：

1. 指定最低 CMake 版本。
2. 定义项目名。
3. 指定使用 C++17。
4. 把 `src/ThreadSafeQueue.cpp` 编译成可执行文件 `ThreadSafeQueue`。
5. 把 `include/` 加入头文件搜索路径，让编译器能找到 `ThreadSafeQueue.hpp`。

---

## `set(CMAKE_CXX_STANDARD 17)` 已经做了什么

```cmake
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
```

这两行的作用是告诉 CMake：

- 项目使用 C++17 标准。
- 如果编译器不支持 C++17，就直接报错，而不是悄悄降级。

因此，通常不需要再手动写：

```cmake
target_compile_options(ThreadSafeQueue PRIVATE -std=c++17)
```

CMake 会根据编译器自动生成合适的标准选项。例如在 GCC/Clang 下通常会生成类似：

```text
-std=gnu++17
```

或在关闭扩展后生成：

```text
-std=c++17
```

如果想避免 GNU 扩展，偏向严格标准 C++，可以再加：

```cmake
set(CMAKE_CXX_EXTENSIONS OFF)
```

---

## `target_include_directories(...)` 已经做了什么

```cmake
target_include_directories(ThreadSafeQueue
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)
```

这段配置告诉 CMake：

> 编译 `ThreadSafeQueue` 这个 target 时，把当前项目目录下的 `include/` 加入头文件搜索路径。

因此，如果项目结构类似：

```text
test_sensor_logger_project/
├── CMakeLists.txt
├── include/
│   └── ThreadSafeQueue.hpp
└── src/
    └── ThreadSafeQueue.cpp
```

那么 `src/ThreadSafeQueue.cpp` 中可以写：

```cpp
#include "ThreadSafeQueue.hpp"
```

而不需要写成：

```cpp
#include "../include/ThreadSafeQueue.hpp"
```

也不需要手动给编译器传 `-Iinclude`。CMake 会根据 `target_include_directories` 自动处理。

---

## `target_compile_options` 是干什么的

`target_compile_options` 用来给某个 target 添加额外的编译器选项。

常见用途包括：

- 开启编译器警告。
- 设置优化级别。
- 添加调试信息。
- 传递特定平台或特定编译器需要的 flag。

例如：

```cmake
target_compile_options(ThreadSafeQueue
    PRIVATE
        -Wall
        -Wextra
        -pedantic
)
```

这会在编译 `ThreadSafeQueue` 时启用更多警告，帮助更早发现潜在问题。

---

## 什么时候需要 `target_compile_options`

| 场景 | 是否需要 `target_compile_options` | 原因 |
|---|---:|---|
| 启用 C++17 标准 | 不需要 | `CMAKE_CXX_STANDARD` 已经处理 |
| 添加头文件搜索路径 | 不需要 | `target_include_directories` 已经处理 |
| 添加编译器警告，例如 `-Wall -Wextra` | 需要 | 这是额外编译器选项 |
| 设置优化级别，例如 `-O2` | 视情况需要 | Release 模式通常会自动有优化选项 |
| 添加调试符号，例如 `-g` | 视情况需要 | Debug 模式通常会自动有 `-g` |
| 特定平台或特定编译器 flag | 需要 | CMake 不一定能自动推断 |

---

## 对当前项目的建议

对截图中的项目来说，当前配置已经足够正常编译：

```cmake
cmake_minimum_required(VERSION 3.16)
project(test_sensor_logger_project)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(ThreadSafeQueue src/ThreadSafeQueue.cpp)

target_include_directories(ThreadSafeQueue
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)
```

如果只是想让代码能编译运行，不需要额外添加 `target_compile_options`。

如果想让编译器更严格，推荐加上警告选项：

```cmake
target_compile_options(ThreadSafeQueue PRIVATE -Wall -Wextra -pedantic)
```

这类选项不会改变 C++ 标准，也不会帮编译器找头文件；它只是让编译器输出更多警告，帮助发现潜在问题。

---

## 最短结论

```text
set(CMAKE_CXX_STANDARD 17)
    -> 设置 C++17，不需要再手写 -std=c++17

target_include_directories(...)
    -> 设置头文件搜索路径，不需要手写 -Iinclude

target_compile_options(...)
    -> 添加额外编译选项，例如 -Wall -Wextra -pedantic
```

---

# `std::move(queue_.front())`：把队头元素移动出来

在线程安全队列的 `wait_and_pop` 中，经常会看到这样的写法：

```cpp
bool wait_and_pop(T& item) {
    std::unique_lock<std::mutex> lock(mutex_);

    cv_.wait(lock, [this] {
        return shutdown_ || !queue_.empty();
    });

    if (queue_.empty()) {
        return false;
    }

    item = std::move(queue_.front());
    queue_.pop();
    return true;
}
```

其中最关键的是这一行：

```cpp
item = std::move(queue_.front());
```

它的意思不是“复制队头元素”，而是：

> 允许 `item` 从 `queue_.front()` 这个对象中搬走资源。

---

## `std::move` 本身不移动数据

`std::move(x)` 这个名字容易误导。

它本身并不会真的移动内存，也不会自动搬运数据。它做的事情是把 `x` 转成一个右值引用，让编译器可以选择移动构造或移动赋值。

也就是说：

```cpp
item = std::move(queue_.front());
```

真正执行移动的是 `T` 类型自己的移动赋值函数：

```cpp
T& operator=(T&& other);
```

如果 `T` 是 `std::string`、`std::vector<int>`、`std::unique_ptr<int>` 或者自定义大对象，移动通常比拷贝便宜。

---

## 移动和拷贝的区别

如果写：

```cpp
item = queue_.front();
```

这是拷贝：

```text
queue_.front() 里的数据还在
item 得到一份复制出来的新数据
```

如果写：

```cpp
item = std::move(queue_.front());
```

这是移动：

```text
queue_.front() 把内部资源交给 item
item 接管原来的资源
queue_.front() 仍然存在，但内容处于有效但未指定状态
```

对于很多标准库类型，所谓“资源”常常是堆内存指针。

例如 `std::vector<int>` 可以近似理解为：

```text
move 前：

queue_.front()
  buffer -> [1, 2, 3, 4, 5]

item
  buffer -> empty

move 后：

queue_.front()
  buffer -> empty 或其他有效空状态

item
  buffer -> [1, 2, 3, 4, 5]
```

数据内容通常没有逐个元素复制，而是内部资源的所有权被转移了。

---

## 不是把对象地址交给 `item`

可以把移动粗略理解成“把内部资源交给 `item`”，但不要理解成“把队列中那个对象的地址交给 `item`”。

`queue_.front()` 这个对象本身仍然留在队列里，地址没有变：

```cpp
item = std::move(queue_.front());
```

执行后，队头元素仍然存在，只是它的资源可能已经被搬走了。

所以必须再调用：

```cpp
queue_.pop();
```

`pop()` 的作用是销毁队列里的队头对象。因为它的资源大概率已经被移动到 `item`，这个销毁通常不会再释放原来的重资源。

---

## `pop()` 不是“释放空地址”

更准确的流程是：

```text
1. queue_.front() 里有资源
2. std::move(queue_.front()) 允许 item 接管这些资源
3. queue_.front() 变成有效但内容未指定的对象
4. queue_.pop() 移除并销毁这个队头对象
5. item 现在拥有原来的数据
```

所以 `pop()` 销毁的是队列中的对象本体，不是单纯释放一个空地址。

---

## 对 `std::unique_ptr` 的意义最明显

有些类型不能拷贝，只能移动，例如 `std::unique_ptr`：

```cpp
std::queue<std::unique_ptr<int>> q;
std::unique_ptr<int> item;

item = q.front();            // 错误：unique_ptr 不能拷贝
item = std::move(q.front()); // 正确：unique_ptr 可以移动
q.pop();
```

移动后可以近似理解为：

```text
q.front() == nullptr
item     == 原来的 int*
```

这时“交出指针”的理解比较贴近。

但对不同类型来说，移动到底做什么，取决于这个类型的移动构造函数或移动赋值函数怎么实现。

---

## 为什么队列里推荐移动

在线程安全队列里，推荐：

```cpp
item = std::move(queue_.front());
queue_.pop();
```

原因：

- 支持不可拷贝但可移动的类型，例如 `std::unique_ptr<T>`。
- 对大对象更高效，例如 `std::string`、`std::vector<T>`。
- 队头元素马上就要 `pop()`，没有必要保留原内容。

如果 `T` 是 `int`、`double` 这类小类型，移动和拷贝基本没有区别。

---

## 最短结论

```text
std::move(queue_.front())
    -> 允许 item 从队头元素中搬走资源

queue_.front()
    -> 对象本身还在队列里，但可能已经被搬空

queue_.pop()
    -> 销毁队列里的队头对象

推荐写法
    -> item = std::move(queue_.front());
       queue_.pop();
```

---

# `mutable std::mutex mutex_`：为什么 mutex 需要 mutable

在线程安全队列里，经常会看到这样的成员：

```cpp
mutable std::mutex mutex_;
```

它通常是为了支持这种 `const` 成员函数：

```cpp
bool empty() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return queue_.empty();
}
```

这里的关键矛盾是：

```text
empty() const 承诺不修改队列的逻辑状态；
但 lock(mutex_) 会调用 mutex_.lock()；
mutex_.lock() 会修改 mutex_ 的内部状态。
```

如果 `mutex_` 不是 `mutable`，这段代码通常无法编译。

---

## `const` 成员函数里发生了什么

成员函数后面的 `const`：

```cpp
bool empty() const
```

表示在函数内部，`this` 近似变成：

```cpp
const ThreadSafeQueue* this
```

也就是说，成员变量会被当成只读：

```cpp
const std::mutex mutex_;
const std::queue<T> queue_;
```

但是加锁需要调用：

```cpp
mutex_.lock();
```

`std::mutex::lock()` 不是 `const` 函数，因为它确实会改变 mutex 的内部状态，例如从“未锁定”变成“已锁定”。

所以如果成员是：

```cpp
std::mutex mutex_;
```

在 `empty() const` 里会出现概念上的冲突：

```text
const 函数里不能修改成员；
lock() 需要修改 mutex_；
所以不能锁。
```

---

## `mutable` 的含义

```cpp
mutable std::mutex mutex_;
```

意思是：

> 即使当前对象是 `const`，也允许修改 `mutex_`。

这不是破坏 const 语义，而是区分两种状态：

| 状态 | 例子 | 是否属于对象的逻辑内容 |
|---|---|---:|
| 逻辑状态 | `queue_` 里有哪些元素、`shutdown_` 是否为 true | 是 |
| 同步状态 | `mutex_` 当前是否被锁住 | 否 |

`empty() const` 不应该改变队列内容，所以它是 `const` 合理。

但为了安全读取队列内容，它需要临时锁住 mutex。这个锁状态只是同步机制，不算队列的逻辑状态。

---

## 为什么 `empty()` 应该是 `const`

`empty()` 的语义是“查看队列当前是否为空”：

```cpp
bool empty() const;
```

它不应该修改队列内容：

```cpp
return queue_.empty();
```

所以从接口设计上，它应该是 `const`。

但是在多线程环境中，读取 `queue_` 也必须加锁：

```cpp
bool empty() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return queue_.empty();
}
```

因此 `mutex_` 需要 `mutable`。

---

## 推荐写法

```cpp
template <typename T>
class ThreadSafeQueue {
private:
    mutable std::mutex mutex_;
    std::condition_variable cv_;
    std::queue<T> queue_;
    bool shutdown_ = false;

public:
    bool empty() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return queue_.empty();
    }
};
```

这里：

- `empty() const` 表示不会改变队列逻辑内容。
- `mutable std::mutex mutex_` 允许 `const` 函数内部加锁。
- `std::lock_guard` 足够，因为这里只是短暂检查，不需要等待条件变量。

---

## 最短结论

```text
empty() const
    -> 逻辑上只读，所以应该是 const

lock(mutex_)
    -> 会修改 mutex_ 的内部锁状态

mutable std::mutex mutex_
    -> 允许 const 函数里加锁

原因
    -> 加锁不改变队列内容，只是线程同步细节
```
