# C++17 / C++20 高频特性

这一篇整理现代 C++ 面试最常问的新特性。建议回答方式是：

- 先讲它解决什么问题
- 再讲什么时候该用
- 最后讲它的边界和误用风险

---

## 1. `std::optional`

### 解决什么问题

表示“可能有值，也可能没有值”，避免用特殊值、裸指针或额外布尔变量表达缺失状态。


### English explanation

In an English interview, I would say:

Represents "may or may not have a value" and avoids using special values, raw pointers, or extra Boolean variables to express missing states.

### 面试官想听什么

- 你是否理解它表达的是可选值语义
- 你是否知道它比返回魔法值更安全

### 示例

```cpp
#include <iostream>
#include <optional>
#include <string>

std::optional<int> parseInt(const std::string& s) {
    if (s.empty()) {
        return std::nullopt;
    }
    return std::stoi(s);
}

int main() {
    auto v = parseInt("42");
    if (v) {
        std::cout << *v << '\n';
    }
}
```

### 使用建议

- 用于函数“可能没有结果”但不算异常的情况
- 不要拿它替代真正的错误处理系统

### 补充理解

- `optional<T>` 通常直接把 `T` 嵌在对象内部，不是默认在堆上分配
- 它适合表达“有或没有一个值”，不适合表达复杂错误原因
- 使用前应检查是否有值，避免直接解引用空 `optional`

---

## 2. `std::variant`

### 解决什么问题

在多个备选类型中安全地持有其中一个，替代 `union` 和弱类型分支。


### English explanation

In an English interview, I would say:

Safely hold one of multiple alternative types, replacing `union` and weakly typed branches.

### 面试官想听什么

- 你是否知道它是类型安全的代数和类型
- 你是否会配合 `std::visit` 使用

### 示例

```cpp
#include <iostream>
#include <string>
#include <variant>

int main() {
    std::variant<int, std::string> value = "hello";

    std::visit([](const auto& x) {
        std::cout << x << '\n';
    }, value);
}
```

### 使用建议

- 适合状态机、消息系统、AST 节点等有限备选类型场景
- 不要把大量业务分支都堆成一个失控的大 variant

### 补充理解

- `variant` 是类型安全的联合体，同一时刻只持有其中一个类型
- 它的大小通常由最大成员类型决定，再加上一些状态开销
- 和继承多态相比，它更适合“类型集合在编译期已知”的场景

---

## 3. `std::string_view`

### 解决什么问题

提供对字符串的只读非拥有视图，避免不必要拷贝。


### English explanation

In an English interview, I would say:

Provides a read-only, non-owning view of strings to avoid unnecessary copies.

### 面试官想听什么

- 你是否知道它不拥有底层内存
- 你是否知道生命周期风险

### 示例

```cpp
#include <iostream>
#include <string>
#include <string_view>

void print(std::string_view sv) {
    std::cout << sv << '\n';
}

int main() {
    std::string s = "hello";
    print(s);
    print("world");
}
```

### 使用建议

- 非拥有只读入参非常适合用 `string_view`
- 不要返回指向临时字符串的 `string_view`

### 补充理解

- `string_view` 自己通常只保存指针和长度，不拥有字符内存
- 它可以指向字符串字面量、`std::string`、字符数组等
- 最大风险是悬空视图，因此生命周期判断比性能收益更重要

---

## 4. `if constexpr`

### 解决什么问题

在模板代码中做编译期条件分支，让泛型代码更可读。


### English explanation

In an English interview, I would say:

Make compile-time conditional branches in template code to make generic code more readable.

### 面试官想听什么

- 你是否知道无效分支会在编译期丢弃
- 你是否知道它能替代一部分 SFINAE

### 示例

```cpp
#include <iostream>
#include <type_traits>

template <typename T>
void printInfo(const T& value) {
    if constexpr (std::is_integral_v<T>) {
        std::cout << "integral: " << value << '\n';
    } else {
        std::cout << "other\n";
    }
}
```

### 使用建议

- 适合少量分支差异
- 如果是接口约束问题，C++20 的 concepts 往往更合适

### 补充理解

- `if constexpr` 和普通 `if` 最大差别在于无效分支会在编译期丢弃
- 这让泛型代码能写得更直观，而不必大量依赖 SFINAE
- 它解决的是“实现分支”问题，不完全等于“接口约束”问题

---

## 5. 结构化绑定

### 解决什么问题

更方便地解构 pair、tuple、结构体，提高可读性。


### English explanation

In an English interview, I would say:

Deconstruct pairs, tuples, and structures more conveniently to improve readability.

### 示例

```cpp
#include <iostream>
#include <tuple>

int main() {
    std::tuple<int, double> t{1, 3.14};
    auto [id, score] = t;
    std::cout << id << " " << score << '\n';
}
```

### 使用建议

- 遍历 map、接收多返回值时很常用
- 注意默认是按值绑定，必要时用引用绑定

### 补充理解

- 结构化绑定提高了可读性，但也可能不小心产生拷贝
- 对大对象或需要修改原对象时，应考虑 `auto& [a, b]`
- 在 `map` 遍历里它尤其常见，比如 `for (auto& [k, v] : mp)`

---

## 6. 折叠表达式

### 解决什么问题

简化可变参数模板的递归展开写法。


### English explanation

In an English interview, I would say:

Simplify the recursive expansion of variable parameter templates.

### 示例

```cpp
#include <iostream>

template <typename... Args>
auto sum(Args... args) {
    return (args + ...);
}

int main() {
    std::cout << sum(1, 2, 3, 4) << '\n';
}
```

### 使用建议

- 写泛型工具时很方便
- 要注意空参数包时的行为

### 补充理解

- 折叠表达式本质是把参数包按某个运算符展开
- 它大幅简化了传统可变参数模板递归写法
- 运算符和初始值选择会影响空参数包下的可用性

---

## 7. `std::filesystem`

### 解决什么问题

提供跨平台文件系统路径和文件操作接口，减少平台相关 API 依赖。


### English explanation

In an English interview, I would say:

Provides cross-platform file system paths and file operation interfaces to reduce platform-related API dependencies.

### 示例

```cpp
#include <filesystem>
#include <iostream>

int main() {
    std::filesystem::path p = "docs/zh";
    std::cout << std::filesystem::exists(p) << '\n';
}
```

### 使用建议

- 适合工具链、文件遍历、路径拼接
- 注意异常和错误码版本接口的选择

### 补充理解

- `filesystem::path` 关注的是路径语义和跨平台处理，不只是字符串拼接
- 某些接口会抛异常，另一些接受 `std::error_code`，两种风格要分清
- 做工具类项目时它通常比手写平台相关路径逻辑更可靠

---

## 8. `std::span`（C++20）

### 解决什么问题

表示一段连续内存的非拥有视图，适合统一接收数组、`vector`、`array` 等连续数据。


### English explanation

In an English interview, I would say:

Represents a non-owned view of a continuous memory, suitable for uniformly receiving continuous data such as arrays, `vector`, and `array`.

### 面试官想听什么

- 你是否知道它不拥有数据
- 你是否知道它只适用于连续内存

### 示例

```cpp
#include <iostream>
#include <span>
#include <vector>

void printAll(std::span<const int> values) {
    for (int v : values) {
        std::cout << v << ' ';
    }
}

int main() {
    std::vector<int> nums = {1, 2, 3};
    printAll(nums);
}
```

### 使用建议

- 参数类型设计上很实用
- 生命周期问题和 `string_view` 类似，不能越界持有

### 补充理解

- `span` 只适用于连续内存，如数组、`vector`、`array`
- 它自己不拥有元素，因此通常只是轻量视图对象
- 这让接口能统一接收多种连续容器，而不必模板化到处展开

---

## 9. `concepts`（C++20）

### 解决什么问题

给模板参数增加显式约束，让错误更清晰、接口更易读。


### English explanation

In an English interview, I would say:

Add explicit constraints to template parameters to make errors clearer and interfaces more readable.

### 面试官想听什么

- 你是否知道 concepts 是模板约束机制
- 你是否知道它能改善模板报错体验

### 示例

```cpp
#include <concepts>
#include <iostream>

template <std::integral T>
T add(T a, T b) {
    return a + b;
}

int main() {
    std::cout << add(1, 2) << '\n';
}
```

### 使用建议

- 新项目做泛型接口时非常推荐
- 但也别把简单函数都过度概念化

### 补充理解

- concepts 把模板要求写到接口层，错误信息通常比 SFINAE 友好很多
- 它既提升可读性，也能让调用者更早知道为什么类型不匹配
- 但如果接口非常简单，过度抽象的 concepts 也会增加理解成本

---

## 10. `ranges`（C++20）

### 解决什么问题

让算法、视图和管道式组合更自然，减少中间容器和样板代码。


### English explanation

In an English interview, I would say:

Make algorithm, view, and pipeline composition more natural, reducing intermediate containers and boilerplate code.

### 示例

```cpp
#include <iostream>
#include <ranges>
#include <vector>

int main() {
    std::vector<int> nums = {1, 2, 3, 4, 5, 6};
    auto even = nums | std::views::filter([](int x) { return x % 2 == 0; });

    for (int x : even) {
        std::cout << x << ' ';
    }
}
```

### 使用建议

- 数据变换链很清晰时非常适合
- 注意团队编译器支持和调试体验

### 补充理解

- `ranges` 强调“算法 + 视图 + 管道式组合”，能减少中间容器
- 视图通常是惰性求值，这既是性能优势，也意味着调试时要理解求值时机
- 它适合数据处理链明显的代码，不适合为了语法新而强行替换所有循环

---

## 11. `constexpr` 在 C++17/C++20 里的增强

### 解决什么问题

让更多函数和对象可以参与编译期求值，提升泛型表达力和编译期验证能力。


### English explanation

In an English interview, I would say:

Allow more functions and objects to participate in compile-time evaluation, improving generic expression and compile-time verification capabilities.

### 示例

```cpp
constexpr int fib(int n) {
    if (n <= 1) {
        return n;
    }
    return fib(n - 1) + fib(n - 2);
}

static_assert(fib(5) == 5);
```

### 使用建议

- 编译期配置、traits、轻量纯函数都适合
- 不要为了炫技把普通业务逻辑强行 constexpr 化

### 补充理解

- 现代标准让 `constexpr` 支持的语法和场景越来越多
- 它的真正价值是把更多逻辑前移到编译期检查，而不是“看起来高性能”
- 如果编译期求值让代码显著难读，收益通常不值得

---

## 12. `std::jthread`（C++20）

### 解决什么问题

比 `std::thread` 更安全地管理线程生命周期，析构时会自动请求停止并 join。


### English explanation

In an English interview, I would say:

It manages the thread life cycle more safely than `std::thread`, and will automatically request stop and join when destructed.

### 示例

```cpp
#include <chrono>
#include <iostream>
#include <thread>

int main() {
    std::jthread worker([] {
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
        std::cout << "done\n";
    });
}
```

### 使用建议

- 简化线程收尾逻辑
- 如果项目标准较老，仍需熟悉 `std::thread`

### 补充理解

- `jthread` 的优势主要在于生命周期管理更安全，减少忘记 `join` 的问题
- 它还与停止机制配合得更自然，适合写可取消任务
- 现代并发接口很多都在往“更难写错”的方向演进，`jthread` 是典型例子

---

## 现代 C++ 复习建议

- 每个特性都要先说“解决了什么问题”
- 强调所有权和生命周期的特性时，重点提风险边界
- 泛型相关特性，重点讲可读性、约束和错误信息改善
