# `std` 标准库学习材料

这份材料不是标准库 reference，而是帮你建立一个工程化的判断框架：

- 这个类型是不是拥有资源？
- 这个接口是在拷贝、转移还是只读观察？
- 这个算法是在处理范围、迭代器还是原始缓冲区？
- 这个对象会不会跨线程、跨作用域、跨异步边界？

如果你想直接运行文中的示例，建议先把编译器版本对齐到对应标准：

```bash
g++ -std=c++17 demo.cpp -O2 -Wall -Wextra -pedantic -o demo
g++ -std=c++20 demo.cpp -O2 -Wall -Wextra -pedantic -o demo
g++ -std=c++23 demo.cpp -O2 -Wall -Wextra -pedantic -o demo
```

---

## 1. `std` 标准库到底怎么学？

### 核心答案

先学“表达语义”的类型，再学“提高效率”的工具。也就是先理解 `string_view`、`span`、`optional`、智能指针这些对象在表达什么，再去学容器、算法、时间、文件系统和并发。

### English explanation

I would learn the standard library by categories: ownership, non-owning views, algorithms, time, filesystem, and concurrency. The key is to pick the type that matches the lifetime and intent of the data.

### 项目里怎么说

我不会把 `std` 当成一堆零散 API 来背，而是把它分成几类：拥有型、观察型、可选型、变体型、时间型、并发型。这样选型会更稳定。

### 深入解释

- 容器解决“数据怎么存”
- 算法解决“数据怎么处理”
- `string_view` / `span` 解决“只读观察一段数据”
- `optional` / `variant` / `expected` 解决“值可能不存在或有多种形态”
- 智能指针解决“对象谁来管”
- `chrono`、`filesystem`、并发工具解决“时间、路径、同步”

### 示例

```cpp
#include <iostream>
#include <optional>
#include <string>
#include <string_view>

std::optional<int> parse_port(std::string_view text) {
    if (text == "http") {
        return 80;
    }
    if (text == "https") {
        return 443;
    }
    return std::nullopt;
}

int main() {
    if (auto port = parse_port("https")) {
        std::cout << "port = " << *port << '\n';
    }
}
```

### 代码讲解

- `std::string_view` 只做只读观察，不拷贝字符串
- `std::optional<int>` 表示“有结果或没有结果”
- 这类接口最适合做解析、查找、配置读取的第一层返回值

## 2. 容器怎么选？

### 核心答案

默认先选 `std::vector`，因为它连续存储、局部性好、遍历快。只有在你明确需要稳定引用、频繁头插头删、或者需要有序键值映射时，才考虑 `deque`、`list`、`map`、`unordered_map` 等其他容器。

### English explanation

My default container choice is `std::vector`. I switch to other containers only when the access pattern requires stable iterators, cheap front insertion, ordering, or hash lookup.

### 项目里怎么说

我会先看数据规模和访问模式。读多写少、需要连续内存时优先 `vector`；需要 key lookup 时再在 `map` 和 `unordered_map` 之间按是否需要顺序来选。

### 深入解释

- `vector` 适合绝大多数顺序数据
- `unordered_map` 适合平均 O(1) 查找
- `map` 适合按序遍历和稳定的有序语义
- `list` 在现代工程里通常不是默认选项，除非你真的需要 splice 或非常特殊的迭代器稳定性

### 示例

```cpp
#include <iostream>
#include <string>
#include <unordered_map>
#include <vector>

int main() {
    std::vector<std::string> words = {"Ada", "Bjarne", "Ada", "Stroustrup"};
    std::unordered_map<std::string, int> freq;
    freq.reserve(words.size());

    for (const auto& word : words) {
        ++freq[word];
    }

    std::cout << "Ada -> " << freq["Ada"] << '\n';
    std::cout << "Bjarne -> " << freq["Bjarne"] << '\n';
}
```

### 代码讲解

- `std::vector` 保存输入序列，适合顺序遍历
- `std::unordered_map` 用于统计词频，体现 key lookup 场景
- `reserve` 可以减少哈希表扩容次数

## 3. 算法和迭代器怎么搭配？

### 核心答案

标准算法把“做什么”从“怎么遍历”里分离出来。你通常应该先选容器，再用算法处理它，而不是自己手写循环来重复实现排序、查找、变换和聚合。

### English explanation

Algorithms separate intent from iteration. I usually pick a container first, then use standard algorithms for sorting, searching, transforming, and counting.

### 项目里怎么说

我会优先使用标准算法，因为它们更容易读、也更容易让团队统一风格。只有在算法流程很复杂或者需要特殊副作用时，我才写显式循环。

### 示例

```cpp
#include <algorithm>
#include <iostream>
#include <numeric>
#include <vector>

int main() {
    std::vector<int> values{5, 1, 3, 8, 2};

    std::sort(values.begin(), values.end());

    int even_count = std::count_if(values.begin(), values.end(),
                                   [](int x) { return x % 2 == 0; });

    std::vector<int> doubled;
    doubled.reserve(values.size());
    std::transform(values.begin(), values.end(), std::back_inserter(doubled),
                   [](int x) { return x * 2; });

    std::cout << "sum = " << std::accumulate(values.begin(), values.end(), 0) << '\n';
    std::cout << "even_count = " << even_count << '\n';
    for (int x : doubled) {
        std::cout << x << ' ';
    }
    std::cout << '\n';
}
```

### 代码讲解

- `std::sort`、`std::count_if`、`std::transform` 都在表达明确意图
- `std::back_inserter` 避免手动管理输出位置
- 你应该把循环逻辑尽量收敛到算法调用里

## 4. `string`、`string_view`、`char*` 怎么选？

### 核心答案

需要拥有文本就用 `std::string`，只读观察且不保存就用 `std::string_view`，底层接口或者 C API 才考虑 `char*`。`string_view` 的最大风险不是效率，而是生命周期。

### English explanation

Use `std::string` when you own the text, `std::string_view` when you only read it temporarily, and raw C strings only when you must interoperate with C APIs.

### 项目里怎么说

我会把函数参数尽量设计成 `std::string_view`，这样调用方可以传 `std::string`、字面量或临时视图。但如果函数要长期保存文本，我会改成 `std::string`。

### 示例

```cpp
#include <iostream>
#include <string>
#include <string_view>

int main() {
    std::string line = "name=cpp";
    auto pos = line.find('=');

    std::string_view key{line.data(), pos};
    std::string_view value{line.data() + pos + 1, line.size() - pos - 1};

    std::cout << key << " -> " << value << '\n';
}
```

### 代码讲解

- `string_view` 不拷贝字符数据
- 它只是一个“指针 + 长度”的观察窗口
- 如果 `line` 生命周期结束，`key` 和 `value` 也就失效了

## 5. `optional`、`variant`、`expected` 怎么区分？

### 核心答案

`optional` 表示“有值或没值”，`variant` 表示“几种固定类型中的一种”，`expected` 表示“成功值或错误值”。这三个类型都在用类型系统表达分支结果，但表达的信息量不同。

### English explanation

`optional` represents presence or absence, `variant` represents one of several fixed alternatives, and `expected` represents a success value or an error value.

### 项目里怎么说

如果失败很正常但原因不重要，我用 `optional`。如果结果有多种明确类型，我用 `variant`。如果失败原因必须返回给调用者，我更倾向 `expected` 或者异常。

### 示例

```cpp
#include <charconv>
#include <iostream>
#include <optional>
#include <string>
#include <string_view>
#include <variant>

std::optional<int> parse_int(std::string_view text) {
    int value = 0;
    auto first = text.data();
    auto last = text.data() + text.size();
    auto [ptr, ec] = std::from_chars(first, last, value);
    if (ec != std::errc{} || ptr != last) {
        return std::nullopt;
    }
    return value;
}

int main() {
    std::variant<int, std::string> result;

    if (auto value = parse_int("8080")) {
        result = *value;
    } else {
        result = std::string{"invalid"};
    }

    std::visit([](const auto& x) {
        std::cout << x << '\n';
    }, result);
}
```

### 代码讲解

- `optional` 用于“解析成功与否”
- `variant` 用于“值或错误信息”这种封闭集合
- `std::visit` 是访问 `variant` 的常用方式

### `expected` 说明

`std::expected` 是 C++23 的新工具。如果你的工具链已经支持，可以把“错误信息”也写进返回值；如果暂时没有支持，`optional` 和 `variant` 已经能覆盖很多场景。

## 6. `span` 为什么好用？

### 核心答案

`std::span` 是一段连续内存的非拥有视图，特别适合函数参数。它比裸指针加长度更安全，也比复制容器更轻。

### English explanation

`std::span` is a non-owning view over contiguous memory. It is ideal for buffer-style APIs that should not take ownership.

### 项目里怎么说

如果函数只需要读写一段连续缓冲区，我会优先用 `span`。如果函数要保存这段数据，就应该改成拥有型容器，而不是保存一个视图。

### 示例

```cpp
#include <algorithm>
#include <iostream>
#include <span>
#include <vector>

void clamp(std::span<float> samples) {
    for (float& x : samples) {
        x = std::clamp(x, -1.0f, 1.0f);
    }
}

int main() {
    std::vector<float> samples{1.5f, 0.2f, -3.0f};
    clamp(samples);

    for (float x : samples) {
        std::cout << x << ' ';
    }
    std::cout << '\n';
}
```

### 代码讲解

- `span` 接收 `vector` 时不会复制元素
- `std::span<float>` 明确表达“连续浮点缓冲区”
- 这类 API 很适合图像、音频、网络包、矩阵块

## 7. `chrono` 和 `filesystem` 怎么落地？

### 核心答案

`chrono` 用类型安全的方式表达时间点和时间间隔，`filesystem` 用标准方式处理路径、目录和文件状态。它们的价值都是把“容易写错的底层细节”变成可组合的类型。

### English explanation

`chrono` gives type-safe time points and durations, while `filesystem` standardizes path and file operations.

### 项目里怎么说

我会把超时、重试、性能统计都写成 `chrono::duration`，不要用裸整数。文件路径和目录遍历尽量用 `std::filesystem`，避免手写字符串拼接。

### 示例

```cpp
#include <chrono>
#include <filesystem>
#include <iostream>

int main() {
    namespace fs = std::filesystem;
    using clock = std::chrono::steady_clock;

    auto start = clock::now();
    for (const auto& entry : fs::directory_iterator{"."}) {
        std::cout << entry.path() << '\n';
    }
    auto end = clock::now();

    auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);
    std::cout << "elapsed(ms) = " << elapsed.count() << '\n';
}
```

### 代码讲解

- `steady_clock` 适合测耗时，因为它不会受系统时间调整影响
- `directory_iterator` 是标准库目录遍历入口
- `duration_cast` 显式把时间单位转换成毫秒

## 8. 智能指针和资源管理怎么选？

### 核心答案

默认先考虑 `std::unique_ptr`，因为它表达独占所有权。只有在确实需要共享生命周期时才用 `std::shared_ptr`，并且要意识到循环引用风险。

### English explanation

`std::unique_ptr` should be the default owning pointer. `std::shared_ptr` should be used only when ownership is genuinely shared.

### 项目里怎么说

我会把“谁拥有对象”先设计清楚，再决定是返回 `unique_ptr`、传引用，还是用 `shared_ptr`。如果只是观察，不应该拿 `shared_ptr` 当通用参数类型。

### 示例

```cpp
#include <iostream>
#include <memory>
#include <string>

struct Node {
    std::string name;
    std::weak_ptr<Node> parent;
};

std::unique_ptr<std::string> make_name() {
    return std::make_unique<std::string>("camera");
}

int main() {
    auto name = make_name();
    std::cout << *name << '\n';

    auto root = std::make_shared<Node>();
    root->name = "root";

    auto child = std::make_shared<Node>();
    child->name = "child";
    child->parent = root;

    std::cout << child->name << " parent = " << child->parent.lock()->name << '\n';
}
```

### 代码讲解

- `unique_ptr` 表达独占资源
- `shared_ptr` 适合共享生命周期
- `weak_ptr` 用来观察 shared 对象，同时避免循环引用

## 9. 并发标准库工具怎么记？

### 核心答案

先记住两个原则：不要默认共享可变状态，真的共享时用 RAII 管锁。`mutex`、`lock_guard`、`condition_variable`、`thread` 是最常见的基础组合，`jthread` 是更安全的现代替代。

### English explanation

In concurrency, reduce shared mutable state first. When you must share state, protect it with RAII locks and condition variables.

### 项目里怎么说

我会优先把任务设计成消息传递或数据分片。只有必须共享队列、缓存或状态时，才引入 mutex、条件变量和线程同步。

### 示例

```cpp
#include <condition_variable>
#include <iostream>
#include <mutex>
#include <thread>

int main() {
    std::mutex m;
    std::condition_variable cv;
    bool ready = false;
    int data = 0;

    std::thread producer([&] {
        {
            std::lock_guard<std::mutex> lock(m);
            data = 42;
            ready = true;
        }
        cv.notify_one();
    });

    std::thread consumer([&] {
        std::unique_lock<std::mutex> lock(m);
        cv.wait(lock, [&] { return ready; });
        std::cout << "data = " << data << '\n';
    });

    producer.join();
    consumer.join();
}
```

### 代码讲解

- `lock_guard` 负责最简单的互斥保护
- `unique_lock` 适合配合条件变量等待
- `wait` 里一定要带谓词，避免虚假唤醒问题

## 10. 一页速查

### 核心答案

- 想存顺序数据，先看 `vector`
- 想表达只读视图，用 `string_view` 或 `span`
- 想表达“可能没有”，用 `optional`
- 想表达“多种封闭结果”，用 `variant`
- 想表达“谁拥有对象”，优先 `unique_ptr`
- 想表达“时间和超时”，用 `chrono`
- 想表达“文件和路径”，用 `filesystem`
- 想表达“同步和并发”，从 `mutex`、`condition_variable`、`thread` 开始

### English explanation

The standard library is best learned by intent: ownership, views, optionality, time, filesystem, and concurrency.

### 项目里怎么说

我会优先选能把语义写进类型系统的 `std` 工具，而不是让接口依赖注释和约定。
