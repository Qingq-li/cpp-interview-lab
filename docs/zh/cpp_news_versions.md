# C++ 版本新特性速查

这份 Note 按 C++ 标准版本整理面试高频新特性和常用标准库新增功能。目标不是完整标准库 reference，而是帮助你快速回答：“这个版本新增了什么？解决了什么问题？项目里怎么用？有什么坑？”

## 版本总览

| 版本 | 关键词 | 面试记忆点 |
|---|---|---|
| C++11 | 现代 C++ 起点 | 移动语义、RAII 智能指针、lambda、线程库、`nullptr`、`auto` |
| C++14 | C++11 打磨 | 泛型 lambda、`make_unique`、返回类型推导、放宽 `constexpr` |
| C++17 | 工程可用性提升 | 结构化绑定、`if constexpr`、fold expression、`optional`、`variant`、`string_view`、filesystem |
| C++20 | 大版本升级 | concepts、ranges、coroutines、modules、`span`、`jthread`、三路比较 |
| C++23 | 补齐现代库体验 | `expected`、`print`、`mdspan`、deducing this、ranges 增强、flat containers |

---

# C++11

## 1. C++11：`auto` 类型推导

### 中文简要介绍

`auto` 让编译器根据初始化表达式推导变量类型，减少冗长类型声明，尤其适合迭代器、模板返回值和复杂泛型代码。

### English Brief

`auto` lets the compiler deduce the variable type from the initializer. It improves readability when the explicit type is noisy, but we should avoid it when it hides ownership or important conversions.

### 中文详细解释

`auto` 的核心价值不是“偷懒少写类型”，而是让代码表达重点从“类型拼写”转移到“变量语义”。例如 STL 迭代器、lambda 返回值、模板函数返回值往往很长，显式写出来反而干扰阅读。

面试中要强调 `auto` 会按模板类型推导规则工作：普通 `auto` 通常会丢掉顶层 `const` 和引用属性，因此可能发生拷贝；如果想绑定原对象，应写 `auto&` 或 `const auto&`。在 range-for 中，`auto x` 会复制元素，`const auto& x` 更适合只读遍历大对象。

### 面试怎么说

我会用 `auto` 简化明显或冗长的类型，但不会让它隐藏重要语义。比如智能指针、所有权转移、数值窄化转换这些地方，显式类型有时更清楚。

### 对比表

| 写法 | 含义 | 常见用途 |
|---|---|---|
| `auto x = value;` | 推导并复制或移动 | 小对象、返回值 |
| `auto& x = value;` | 可修改引用 | 需要修改原对象 |
| `const auto& x = value;` | 只读引用 | 遍历大对象 |
| `auto&& x = expr;` | 转发引用或万能引用语境 | 泛型代码 |

## 2. C++11：范围 `for` 循环

### 中文简要介绍

范围 `for` 用 `for (auto& x : container)` 直接遍历范围，减少迭代器样板代码，让遍历意图更清楚。

### English Brief

Range-based `for` makes iteration more direct and less error-prone. The key interview point is choosing `auto`, `auto&`, or `const auto&` intentionally.

### 中文详细解释

C++11 之前遍历容器通常要写 begin/end 迭代器，代码重复且容易写错边界。范围 `for` 把“遍历所有元素”的意图直接写出来，特别适合顺序处理容器元素。

面试要注意引用语义：`for (auto x : v)` 会复制元素；`for (auto& x : v)` 修改原元素；`for (const auto& x : v)` 避免复制且保证只读。对于临时范围或视图，还要关注生命周期，不能把循环里的引用保存到外部长期使用。

### 小例子

```cpp
std::vector<std::string> names = {"Ada", "Bjarne"};

for (const auto& name : names) {
    std::cout << name << '\n';
}
```

### 面试怎么说

我默认用 `const auto&` 遍历只读大对象，用 `auto&` 表达修改，用 `auto` 处理便宜可复制的小对象。

## 3. C++11：lambda 表达式

### 中文简要介绍

lambda 是可在局部定义的匿名函数对象，适合传给算法、回调、线程入口或延迟执行逻辑。

### English Brief

A lambda is an inline function object with an optional capture list. It is useful for local behavior, callbacks, and STL algorithms, but captures must be designed carefully.

### 中文详细解释

lambda 解决的是“为了很小的局部行为单独写函数或仿函数太重”的问题。它可以捕获外部变量，也可以像普通函数一样接收参数。常见形式是 `[capture](params) { body }`。

面试重点在 capture：按值捕获保存副本，按引用捕获依赖外部对象生命周期，捕获 `this` 在异步场景容易悬空。默认捕获 `[=]`、`[&]` 虽方便，但项目中更推荐显式捕获关键变量，减少生命周期和线程安全风险。

### 小例子

```cpp
int threshold = 10;
std::vector<int> values = {3, 12, 8, 20};

auto count = std::count_if(values.begin(), values.end(),
                           [threshold](int x) { return x > threshold; });
```

### 面试怎么说

我会把 lambda 当成局部函数对象使用，重点关注捕获方式。如果 lambda 会跨线程或延迟执行，我会特别检查捕获对象的生命周期。

## 4. C++11：移动语义和右值引用

### 中文简要介绍

移动语义允许对象转移资源而不是深拷贝资源，是现代 C++ 性能和所有权表达的核心机制。

### English Brief

Move semantics transfer resources instead of copying them. They make returning and storing resource-owning objects efficient while preserving clear ownership.

### 中文详细解释

C++11 引入右值引用 `T&&`、move constructor、move assignment，让 `std::vector`、`std::string`、`std::unique_ptr` 这类资源对象可以低成本转移内部资源。比如移动一个 vector 通常只是转移指针、大小和容量，而不是复制每个元素。

面试中要说清楚：`std::move` 本身不移动，它只是把表达式转换成右值引用，真正的移动发生在被调用的 move 构造或 move 赋值里。被移动对象必须保持“有效但值未指定”，可以析构、重新赋值，但不应该依赖原值。

### 对比表

| 操作 | 含义 | 成本 |
|---|---|---|
| copy | 复制资源或值 | 可能深拷贝 |
| move | 转移资源所有权 | 通常很便宜 |
| copy elision | 直接在目标位置构造 | 无复制/移动 |

### 面试怎么说

我会在所有权转移时使用 move，并保证之后不再依赖源对象的旧值。对于资源管理类，我优先用标准库成员实现 Rule of Zero。

## 5. C++11：`std::unique_ptr` 和 `std::shared_ptr`

### 中文简要介绍

智能指针用 RAII 管理动态对象生命周期，`unique_ptr` 表示独占所有权，`shared_ptr` 表示共享所有权。

### English Brief

Smart pointers express ownership. `unique_ptr` is the default owning pointer, while `shared_ptr` should be used only when lifetime is truly shared.

### 中文详细解释

C++11 的智能指针把动态内存管理从手动 `new/delete` 转为对象生命周期管理。`std::unique_ptr` 不能复制，只能移动，非常适合表达“这里唯一拥有这个对象”。`std::shared_ptr` 通过引用计数共享所有权，最后一个 owner 析构时释放对象。

面试要避免说“智能指针就是更安全的裸指针”。真正重点是所有权语义。`shared_ptr` 有引用计数开销，还可能出现循环引用，需要 `std::weak_ptr` 打破环。函数参数如果不拥有对象，通常用引用或裸指针观察，不要随便传 `shared_ptr`。

### 对比表

| 类型 | 所有权 | 典型场景 |
|---|---|---|
| `T*` | 通常非拥有 | 可空观察、底层接口 |
| `std::unique_ptr<T>` | 独占拥有 | 工厂返回、Pimpl、动态多态 |
| `std::shared_ptr<T>` | 共享拥有 | 多个 owner 共同延长生命周期 |
| `std::weak_ptr<T>` | 非拥有观察 | 观察 shared 对象、打破循环 |

## 6. C++11：`nullptr`

### 中文简要介绍

`nullptr` 是类型安全的空指针字面量，替代 `NULL` 和 `0`，避免重载解析中的歧义。

### English Brief

`nullptr` is a type-safe null pointer literal. It avoids the overload problems caused by `NULL` being an integer-like macro.

### 中文详细解释

在旧 C++ 中，`NULL` 可能只是 `0` 或 `0L`，因此调用重载函数时可能匹配到整数重载，而不是指针重载。`nullptr` 的类型是 `std::nullptr_t`，可以转换成任意指针类型，但不会当成普通整数。

面试回答时可以直接说：现代 C++ 中空指针统一用 `nullptr`。它提升类型安全，也让代码意图更明确。不要再用 `NULL`，除非维护非常旧的 C/C++ 兼容代码。

### 小例子

```cpp
void f(int);
void f(int*);

f(nullptr); // 调用 f(int*)
```

## 7. C++11：统一初始化和 `std::initializer_list`

### 中文简要介绍

统一初始化用 `{}` 提供更一致的初始化语法，并能防止部分窄化转换；`initializer_list` 支持容器列表初始化。

### English Brief

Brace initialization provides a more uniform initialization syntax and helps prevent narrowing conversions. It also enables convenient list initialization for containers.

### 中文详细解释

C++11 前初始化语法很多：圆括号、等号、构造函数、数组初始化等。统一初始化希望用 `{}` 覆盖更多场景，例如 `std::vector<int> v{1, 2, 3};`。它还能阻止 `int x{3.14};` 这类窄化转换。

需要注意的是 `{}` 会优先匹配 `std::initializer_list` 构造函数，这可能导致和圆括号初始化行为不同。面试中可以提到：brace initialization 很有用，但不是所有场景都无脑替代 `()`。

### 对比表

| 写法 | 含义 |
|---|---|
| `std::vector<int> a(3, 1);` | 3 个元素，每个为 1 |
| `std::vector<int> b{3, 1};` | 两个元素：3 和 1 |

## 8. C++11：`override` 和 `final`

### 中文简要介绍

`override` 让编译器检查虚函数覆写是否正确，`final` 禁止继续覆写或继承。

### English Brief

`override` makes virtual overrides compiler-checked. `final` prevents further overriding or inheritance when a design should be closed.

### 中文详细解释

没有 `override` 时，派生类函数如果参数、`const`、引用限定符写错，可能不是覆写，而是隐藏或新增函数，运行时多态行为就会错。`override` 能让这种错误在编译期暴露。

`final` 用得更少，但在框架、性能敏感层或不希望被继承的类中有价值。它表达“这个类型或虚函数的扩展点到此为止”。面试中建议强调：`override` 应该常规使用；`final` 要根据设计意图谨慎使用。

### 小例子

```cpp
struct Base {
    virtual void run() const = 0;
    virtual ~Base() = default;
};

struct Worker final : Base {
    void run() const override {}
};
```

## 9. C++11：`std::thread` 和标准线程库

### 中文简要介绍

C++11 引入标准线程库，包括 `std::thread`、mutex、condition variable、atomic，使跨平台并发编程进入标准库。

### English Brief

C++11 standardized threading primitives. It gives portable tools for threads, locks, condition variables, and atomics, but correctness still depends on synchronization design.

### 中文详细解释

在 C++11 之前，并发通常依赖 pthread、Windows thread 或第三方库。C++11 提供统一抽象：`std::thread` 创建线程，`std::mutex` 保护共享数据，`std::condition_variable` 等待条件，`std::atomic` 支持无数据竞争的单对象操作。

面试重点不是背 API，而是知道数据竞争是 undefined behavior。`std::thread` 析构前必须 join 或 detach，否则程序会 terminate。现代 C++20 有 `std::jthread` 自动 join，能降低生命周期风险。

### 面试怎么说

我会优先减少共享可变状态；必须共享时，用 RAII 锁管理 mutex，并用 predicate 形式等待 condition variable。

## 10. C++11：`std::chrono`

### 中文简要介绍

`std::chrono` 提供类型安全的时间点、时间间隔和时钟，避免裸整数表示时间单位导致错误。

### English Brief

`std::chrono` gives type-safe durations and time points. It prevents mixing milliseconds, seconds, and raw integers accidentally.

### 中文详细解释

`chrono` 的核心抽象是 duration、time_point 和 clock。duration 表示时间长度，如 milliseconds、seconds；time_point 表示某个时钟上的时间点；clock 提供 now。它让函数接口能明确表达时间单位。

面试中可以结合工程场景说：超时、重试、性能测量、定时任务都应该避免裸 `int timeout`，更推荐 `std::chrono::milliseconds timeout`。这样调用方不容易把秒误传成毫秒。

### 小例子

```cpp
using namespace std::chrono_literals;

std::this_thread::sleep_for(100ms);
auto start = std::chrono::steady_clock::now();
```

## 11. C++11：`constexpr` 初始能力

### 中文简要介绍

`constexpr` 表示函数或变量可用于编译期求值，是现代 C++ 编译期计算的基础。

### English Brief

`constexpr` allows values and functions to be evaluated at compile time. In C++11 it was restrictive, but it established the foundation for modern compile-time programming.

### 中文详细解释

C++11 的 `constexpr` 函数限制较多，函数体通常只能包含很简单的 return 表达式。但它的重要意义是把“可编译期求值”纳入语言模型，让常量表达式不再只依赖宏或 enum hack。

面试中可以说：`constexpr` 不是强制每次都编译期执行，而是当上下文需要常量表达式且参数满足条件时可以编译期执行。后续 C++14/17/20 逐步放宽 `constexpr` 的函数体能力。

### 面试怎么说

我会用 `constexpr` 表达真正的常量计算，让编译器在能提前计算时提前计算，同时避免宏带来的类型不安全问题。

## 12. C++11：`enum class`

### 中文简要介绍

`enum class` 是强类型枚举，避免传统 enum 名字污染和隐式整数转换。

### English Brief

`enum class` is a scoped, strongly typed enum. It prevents accidental conversions to integers and avoids leaking enumerator names into the surrounding scope.

### 中文详细解释

传统 `enum` 的枚举值会进入外层作用域，而且容易隐式转换成 int。`enum class` 把枚举值限制在类型作用域内，例如 `Color::Red`，并且默认不隐式转换成整数。

面试里可以说：如果只是表达一组有限状态，现代 C++ 更推荐 `enum class`。如果需要和底层协议、文件格式或硬件寄存器交互，可以显式指定底层类型，如 `enum class Mode : uint8_t`。

### 小例子

```cpp
enum class State : unsigned char {
    Idle,
    Running,
    Failed
};
```

---

# C++14

## 13. C++14：泛型 lambda

### 中文简要介绍

泛型 lambda 允许参数使用 `auto`，让 lambda 像小型函数模板一样适配不同类型。

### English Brief

Generic lambdas allow `auto` parameters. They make local generic behavior concise without writing a separate function template.

### 中文详细解释

C++11 lambda 的参数类型必须明确写出。C++14 允许 `[](auto x, auto y) { ... }`，编译器会为不同调用生成对应的函数调用运算符模板。这对 STL 算法、variant visit、简单泛型比较器很方便。

面试中要知道泛型 lambda 本质仍是闭包类型，只是它的 `operator()` 是模板。不要过度使用泛型 lambda 隐藏类型要求；如果逻辑复杂或约束重要，C++20 concepts 或普通函数模板更清楚。

### 小例子

```cpp
auto add = [](const auto& a, const auto& b) {
    return a + b;
};
```

## 14. C++14：函数返回类型推导

### 中文简要介绍

C++14 允许普通函数返回类型写 `auto`，由 return 语句推导返回类型。

### English Brief

C++14 allows return type deduction for normal functions. It is useful when the return type is obvious from the implementation, but public APIs should still consider readability.

### 中文详细解释

C++11 主要在 lambda 中支持返回类型推导，普通函数通常还要显式写返回类型。C++14 允许 `auto makeValue() { return T{}; }`。这减少了模板代码中的重复类型拼写。

面试要注意：多个 return 分支必须推导出一致类型；递归函数也需要编译器能确定返回类型。对于公共 API，显式返回类型有时更利于阅读、文档和 ABI 稳定。

### 面试怎么说

我会在实现细节或类型很明显时用返回类型推导；如果函数是公共接口，返回类型影响调用者理解，我倾向显式写出。

## 15. C++14：`std::make_unique`

### 中文简要介绍

`std::make_unique` 是创建 `unique_ptr` 的工厂函数，避免手写 `new`，让独占所有权创建更安全。

### English Brief

`std::make_unique` creates a `unique_ptr` safely and concisely. It is the preferred way to allocate uniquely owned objects.

### 中文详细解释

C++11 有 `std::make_shared`，但缺少 `make_unique`，C++14 补齐了这个空缺。`make_unique<T>(args...)` 直接构造对象并返回 `unique_ptr<T>`，代码更短，也避免资源创建过程中异常导致的泄漏风险。

面试中可以说：现代 C++ 项目里，直接写 `new` 应该很少见。需要独占动态对象时优先 `make_unique`；需要共享所有权时再考虑 `make_shared`，但不要为了方便就使用 shared ownership。

### 小例子

```cpp
auto worker = std::make_unique<Worker>("camera");
```

## 16. C++14：放宽 `constexpr`

### 中文简要介绍

C++14 放宽了 `constexpr` 函数限制，允许局部变量、循环和分支，让编译期计算更实用。

### English Brief

C++14 made `constexpr` functions much more practical by allowing local variables, loops, and branches. This enabled clearer compile-time algorithms.

### 中文详细解释

C++11 的 `constexpr` 函数非常受限，复杂一点的逻辑很难写。C++14 放宽后，很多普通函数风格的代码可以在满足条件时参与编译期求值，例如循环计算、条件分支和局部变量。

面试中可以强调：`constexpr` 的价值是类型安全、可测试、可复用的编译期计算，而不是用宏做文本替换。后续 C++20 继续增强 `constexpr`，甚至允许更多标准库操作在编译期执行。

### 小例子

```cpp
constexpr int sumTo(int n) {
    int result = 0;
    for (int i = 1; i <= n; ++i) {
        result += i;
    }
    return result;
}
```

## 17. C++14：变量模板

### 中文简要介绍

变量模板允许定义依赖模板参数的变量，常用于 type traits 的 `_v` 简写风格。

### English Brief

Variable templates define templated variables. They are commonly used to make type trait code shorter and easier to read.

### 中文详细解释

变量模板让 `template<class T> constexpr bool is_x_v = ...;` 这种写法成为可能。标准库在 C++17 中大量提供 `_v` 辅助变量，例如 `std::is_same_v<T, U>`，比 `std::is_same<T, U>::value` 更清晰。

面试中可以把它放在模板元编程演进里理解：C++11 用 traits 类型和 `::value`，C++14/17 用变量模板简化表达，C++20 用 concepts 把约束进一步提升到接口层。

### 面试怎么说

我会在 traits 或编译期布尔条件中使用 `_v` 风格，减少模板代码噪音。

---

# C++17

## 18. C++17：结构化绑定

### 中文简要介绍

结构化绑定可以把 pair、tuple、数组或简单结构体拆成多个具名变量，提升返回多个值时的可读性。

### English Brief

Structured bindings unpack tuple-like objects into named variables. They make multi-value returns and map iteration easier to read.

### 中文详细解释

结构化绑定解决的是 `std::pair`、`std::tuple` 使用 `.first`、`.second` 或 `std::get<0>` 可读性差的问题。典型写法是 `auto [it, inserted] = set.insert(x);`，变量名直接表达语义。

面试中要注意复制和引用：`auto [k, v]` 会复制；`auto& [k, v]` 绑定原对象；遍历 map 时 key 是 const，不能修改。结构化绑定不是新对象模型，它只是编译器帮你把成员或元素绑定到名字上。

### 小例子

```cpp
std::map<std::string, int> scores;
for (const auto& [name, score] : scores) {
    std::cout << name << ": " << score << '\n';
}
```

## 19. C++17：`if` / `switch` 初始化语句

### 中文简要介绍

C++17 允许在 `if` 和 `switch` 条件前声明局部变量，把临时状态限制在判断语句作用域内。

### English Brief

`if` and `switch` initializers keep temporary variables scoped to the condition. This reduces leakage of names into the surrounding scope.

### 中文详细解释

旧写法常常要先在外层声明变量，再写 `if` 判断，导致变量作用域比需要的更大。C++17 可以写 `if (auto it = m.find(key); it != m.end())`，`it` 只在 if/else 内可见。

面试中可以强调这是一种作用域管理工具：让变量生命周期更短，减少误用，也让代码更接近“查找并判断”的业务意图。它和 RAII 思想一致，尽量缩小资源和变量的可见范围。

### 小例子

```cpp
if (auto it = cache.find(id); it != cache.end()) {
    return it->second;
}
```

## 20. C++17：`if constexpr`

### 中文简要介绍

`if constexpr` 是编译期分支，未选择的分支不会实例化，常用于模板中根据类型选择实现。

### English Brief

`if constexpr` selects a branch at compile time. It is especially useful in templates because discarded branches are not instantiated.

### 中文详细解释

模板代码中经常需要根据类型特征走不同逻辑。C++17 前常用 SFINAE、重载或特化，代码容易分散。`if constexpr` 允许把类型分支写在函数体内部，未选分支不会参与实例化，因此可以包含对当前类型无效的代码。

面试中要区分：`if constexpr` 解决函数体内部实现分支；C++20 concepts 解决接口层约束。两者互补，不是完全替代关系。

### 小例子

```cpp
template <class T>
void printValue(const T& value) {
    if constexpr (std::is_integral_v<T>) {
        std::cout << "int-like: " << value << '\n';
    } else {
        std::cout << value << '\n';
    }
}
```

## 21. C++17：fold expression

### 中文简要介绍

fold expression 简化可变参数模板中对参数包的展开，例如求和、逻辑合并、批量调用。

### English Brief

Fold expressions make parameter pack expansion concise. They replace many recursive variadic template patterns.

### 中文详细解释

C++11/14 写可变参数模板时，常用递归模板或 initializer_list hack 展开参数包。C++17 提供 fold expression，例如 `(args + ...)`、`(... && predicates)`，表达更直接。

面试中可以说：fold expression 让模板元编程更接近普通表达式，减少递归模板样板代码。需要注意操作符结合方向、空参数包是否合法，以及操作符是否对所有参数类型有意义。

### 小例子

```cpp
template <class... Args>
auto sum(Args... args) {
    return (args + ...);
}
```

## 22. C++17：inline variable

### 中文简要介绍

inline variable 允许变量定义放在头文件中并被多个翻译单元包含，解决 header-only 常量定义的 ODR 问题。

### English Brief

Inline variables allow a variable definition in a header without violating the One Definition Rule. They are useful for header-only constants and static data members.

### 中文详细解释

C++17 前，类的 `static` 数据成员通常需要类外定义；头文件里的全局变量容易造成多重定义。`inline` 变量让多个翻译单元看到同一个变量定义成为合法，链接器会合并这些定义。

面试中要强调它解决的是 ODR 和头文件定义问题，不是性能优化。对于常量，优先考虑 `inline constexpr`；对于有状态全局对象，仍要谨慎，因为初始化顺序和全局状态管理仍然复杂。

### 小例子

```cpp
struct Config {
    inline static constexpr int maxRetries = 3;
};
```

## 23. C++17：`std::optional`

### 中文简要介绍

`std::optional<T>` 表达“可能有值，也可能没有值”，适合没有复杂错误原因的查询、解析或缓存命中。

### English Brief

`std::optional` represents an optional value. It is better than sentinel values when absence is normal and does not need rich error information.

### 中文详细解释

`optional` 让接口不再依赖 `-1`、空字符串、特殊对象这类 sentinel value。它内部要么没有对象，要么原地存放一个 `T`。调用方通过 `has_value()`、`operator bool` 或 `value_or` 处理缺失。

面试中要说清楚：`optional` 表达 absence，不表达丰富错误原因。如果失败原因重要，应使用异常、错误码、`variant` 或 C++23 `expected`。也不要把 `optional` 理解成指针，它通常直接存储值，不表示共享或观察生命周期。

### 小例子

```cpp
std::optional<int> findPort(std::string_view name);

if (auto port = findPort("camera")) {
    connect(*port);
}
```

## 24. C++17：`std::variant`

### 中文简要介绍

`std::variant` 是类型安全的多选一值，适合候选类型集合固定的状态、消息或解析结果。

### English Brief

`std::variant` is a type-safe discriminated union. It works well when the set of possible alternatives is closed and known at compile time.

### 中文详细解释

`variant<A, B, C>` 在同一时刻只保存一种候选类型，比裸 union 安全，因为它知道当前持有的类型并正确管理对象生命周期。访问时可以用 `std::get_if` 或 `std::visit`。

面试中常被问 variant 和虚函数多态区别：variant 是封闭类型集合，新增类型要改 variant 定义和访问逻辑；虚函数多态是开放实现集合，新增派生类不一定改调用方。选择取决于扩展方向。

### 对比表

| 方案 | 适合场景 | 代价 |
|---|---|---|
| `std::variant` | 类型集合固定、值语义 | 新增类型要改访问逻辑 |
| 虚函数多态 | 实现集合可扩展 | 堆分配/间接调用/生命周期设计 |

## 25. C++17：`std::string_view`

### 中文简要介绍

`std::string_view` 是非拥有只读字符串视图，适合作为只读参数，避免不必要的字符串拷贝。

### English Brief

`std::string_view` is a non-owning read-only view of character data. It is efficient for parameters, but dangerous if it outlives the source string.

### 中文详细解释

`string_view` 只保存指针和长度，不拥有字符数据，也不保证以 `\0` 结尾。它可以接收 `std::string`、字符串字面量、字符数组等，适合“只在函数调用期间读取”的参数。

最大风险是生命周期。不能长期保存指向临时 string、局部缓冲或已释放内存的 view。面试中要明确：需要保存文本时用 `std::string`；只读观察且不保存时用 `std::string_view`。

### 小例子

```cpp
void logName(std::string_view name) {
    std::cout << name << '\n';
}
```

## 26. C++17：filesystem

### 中文简要介绍

`std::filesystem` 提供跨平台路径、文件状态、目录遍历和文件操作接口。

### English Brief

`std::filesystem` standardizes path and file-system operations. It replaces many platform-specific path handling utilities.

### 中文详细解释

C++17 前，文件路径处理通常依赖 POSIX、Windows API、Boost.Filesystem 或项目自定义工具。`std::filesystem` 引入 `path`、`exists`、`is_regular_file`、`directory_iterator` 等能力，让常见文件系统操作进入标准库。

面试中可以强调：filesystem 让路径拼接和跨平台分隔符处理更安全，但文件系统本身仍有权限、符号链接、并发修改、编码等复杂问题。生产代码要处理异常或错误码重载，不要假设文件状态检查后文件一定不变。

### 小例子

```cpp
namespace fs = std::filesystem;

for (const auto& entry : fs::directory_iterator{"."}) {
    std::cout << entry.path() << '\n';
}
```

## 27. C++17：并行算法执行策略

### 中文简要介绍

C++17 为部分标准算法引入执行策略，如 `seq`、`par`、`par_unseq`，表达算法可并行执行。

### English Brief

Execution policies allow selected standard algorithms to run sequentially or in parallel. They express parallel intent, but the implementation and safety constraints matter.

### 中文详细解释

执行策略让调用者可以写 `std::sort(std::execution::par, ...)` 这类代码，把并行化意图交给标准库实现。它适合无共享副作用、数据范围清晰、计算量足够大的算法场景。

面试中要注意：并行算法不是自动加速按钮。回调函数必须避免数据竞争，迭代器和操作要满足算法要求；小数据量可能因为调度开销更慢。实际项目里仍要 profiling。

### 面试怎么说

我会先保证算法是纯计算或副作用受控，再考虑并行策略，并用性能数据验证它是否真的改善吞吐。

---

# C++20

## 28. C++20：concepts

### 中文简要介绍

concepts 把模板参数要求写成可读约束，让泛型接口更清楚，错误信息通常比 SFINAE 更友好。

### English Brief

Concepts make template requirements explicit. They improve readability and diagnostics, but they do not automatically make template design simple.

### 中文详细解释

C++20 前模板约束常用 `std::enable_if`、traits、SFINAE，代码分散且错误信息难读。concepts 允许定义命名约束，如 `std::integral<T>` 或自定义 `Sortable<T>`，并把约束写在模板声明上。

面试中要强调：concepts 约束的是“这个模板接受什么类型”，它参与重载决议，也让调用错误更早暴露。但 concept 仍需要设计语义，不应该只是堆表达式检查。

### 小例子

```cpp
template <std::integral T>
T add(T a, T b) {
    return a + b;
}
```

## 29. C++20：`requires` clause 和 requires expression

### 中文简要介绍

`requires` clause 用来约束模板，requires expression 用来检查表达式是否合法并形成 concept 条件。

### English Brief

A requires-clause constrains a template, while a requires-expression checks whether expressions are valid. Together they make template requirements explicit.

### 中文详细解释

`requires` 有两种常见用法。写在模板声明后的 `requires` clause 表示“这个模板只有满足条件才能参与匹配”。`requires (T x) { x.begin(); }` 这种 requires expression 则生成一个编译期布尔条件，用于描述类型必须支持哪些操作。

面试中可以说：requires 比 SFINAE 更直接，因为约束出现在接口附近。读函数声明时就能知道类型要求，而不是深入函数体或 traits 技巧才能理解。

### 面试怎么说

我会用 requires 把公共模板接口的要求写清楚，让调用错误更早、更可读。

## 30. C++20：ranges

### 中文简要介绍

ranges 让算法直接接受范围对象，并提供 views 管道组合，减少 begin/end 样板和临时容器。

### English Brief

Ranges make algorithms work with range objects and composable views. They improve expressiveness for filtering, transforming, and slicing sequences.

### 中文详细解释

传统算法通常需要 `begin`/`end` 迭代器对。C++20 ranges 允许 `std::ranges::sort(v)`，并通过 views 构建惰性管道，例如 filter、transform、take。这样代码更接近数据处理意图。

面试中要注意 views 通常是惰性非拥有视图，生命周期非常重要。不能让 view 引用已经销毁的容器。ranges 提升表达能力，但复杂管道也可能降低可读性，需要适度使用。

### 小例子

```cpp
auto even = values
    | std::views::filter([](int x) { return x % 2 == 0; })
    | std::views::transform([](int x) { return x * 2; });
```

## 31. C++20：coroutines

### 中文简要介绍

coroutine 让函数可以暂停和恢复，是构建异步任务、生成器和协作式流程的语言基础设施。

### English Brief

Coroutines allow a function to suspend and resume. C++20 provides the language mechanism, but not a complete async runtime by itself.

### 中文详细解释

C++20 coroutine 通过 `co_await`、`co_yield`、`co_return` 表达暂停点。编译器把 coroutine 转换成状态机，局部状态保存在 coroutine frame 中。它适合异步 IO、生成器、事件驱动逻辑等场景。

面试中最重要的坑是：C++20 只提供底层语言机制，标准库没有完整 async runtime。真正使用时需要任务类型、调度器、awaiter、生命周期管理。不要说“C++20 coroutine 等于 async/await 框架已经内置完整可用”。

### 面试怎么说

我会把 coroutine 理解成可暂停函数的基础设施，项目里是否使用取决于框架和 runtime 是否成熟。

## 32. C++20：modules

### 中文简要介绍

modules 通过模块接口替代部分头文件包含模型，目标是减少宏污染、重复解析和编译依赖。

### English Brief

Modules provide a structured alternative to textual header inclusion. They can improve build times and isolation, but migration requires tooling and build-system support.

### 中文详细解释

传统 `#include` 是文本包含，容易造成宏污染、重复解析和依赖扩散。modules 引入 `export module`、`import` 等机制，让接口和实现边界更明确。编译器可以缓存模块接口，理论上改善构建性能。

面试中要务实：modules 是重要方向，但落地依赖编译器、构建系统、第三方库和团队迁移策略。短期项目中，Pimpl、前置声明、include-what-you-use 仍然是控制依赖的重要手段。

### 面试怎么说

我会说 modules 解决头文件模型的一些根本问题，但工程迁移需要渐进，不是简单替换所有 include。

## 33. C++20：三路比较 `<=>`

### 中文简要介绍

三路比较运算符 `<=>` 可以一次表达小于、等于、大于关系，并支持自动生成常见比较运算符。

### English Brief

The spaceship operator provides three-way comparison. It reduces boilerplate for ordering and equality operations.

### 中文详细解释

以前自定义类型要实现 `==`、`!=`、`<`、`<=`、`>`、`>=` 往往写很多重复代码，还容易不一致。C++20 的 `<=>` 可以返回比较类别，如 strong_ordering、weak_ordering、partial_ordering，并由编译器生成相关比较。

面试中要知道不同排序语义：整数通常 strong ordering；浮点有 NaN，可能是 partial ordering。不要机械 default 所有类型，仍要确认成员比较是否符合业务语义。

### 小例子

```cpp
struct Point {
    int x;
    int y;
    auto operator<=>(const Point&) const = default;
};
```

## 34. C++20：`std::span`

### 中文简要介绍

`std::span<T>` 是非拥有连续内存视图，适合函数参数接收数组、vector 或缓冲区而不复制。

### English Brief

`std::span` is a non-owning view over contiguous memory. It is useful for APIs that read or modify buffers without taking ownership.

### 中文详细解释

`span` 保存指针和长度，表达“我观察这一段连续元素”。它比裸指针加长度更安全，因为长度和指针绑定在同一个对象里；比 vector 引用更通用，因为它也能接收数组和其他连续存储。

面试重点仍是生命周期：`span` 不拥有数据，不能比底层缓冲活得更久。接口如果需要保存数据，应复制到拥有型容器；如果只在调用期间处理 buffer，`span` 很合适。

### 小例子

```cpp
void normalize(std::span<float> samples) {
    for (float& x : samples) {
        x = std::clamp(x, -1.0f, 1.0f);
    }
}
```

## 35. C++20：`std::jthread` 和 `stop_token`

### 中文简要介绍

`std::jthread` 是 RAII 风格线程，析构时自动 join，并支持通过 `stop_token` 做协作式取消。

### English Brief

`std::jthread` automatically joins on destruction and supports cooperative cancellation through stop tokens. It is safer than raw `std::thread` for many cases.

### 中文详细解释

`std::thread` 的生命周期坑是析构前必须 join 或 detach，否则 terminate。`jthread` 在析构时自动请求停止并 join，减少忘记 join 的风险。配合 `std::stop_token`，线程函数可以定期检查是否收到停止请求。

面试中要强调这是“协作式取消”，不是强制杀线程。线程里的阻塞 IO、长时间计算、锁等待都需要设计可响应停止请求的检查点。

### 对比表

| 类型 | join 行为 | 取消支持 |
|---|---|---|
| `std::thread` | 手动 join/detach | 无内建 stop token |
| `std::jthread` | 析构自动 join | 支持协作式停止 |

## 36. C++20：`std::format`

### 中文简要介绍

`std::format` 提供类型安全、可读性更好的字符串格式化，风格接近 Python format / fmt 库。

### English Brief

`std::format` provides type-safe string formatting. It is clearer than stream chains and safer than `printf`-style formatting.

### 中文详细解释

传统 C++ 格式化常用 iostream 或 `printf`。iostream 类型安全但可读性差，`printf` 简洁但格式字符串和参数类型不匹配会出问题。`std::format` 使用 `{}` 占位符，返回格式化字符串。

面试中可以说：`format` 让日志、错误消息、用户输出更清晰。不过实际项目还要考虑编译器支持情况；很多代码库在 C++20 前已经使用 fmt 库，迁移时要看 ABI 和工具链。

### 小例子

```cpp
auto msg = std::format("sensor {} latency {} ms", name, latency);
```

## 37. C++20：calendar 和 timezone

### 中文简要介绍

C++20 扩展 chrono，加入日历日期和时区能力，让日期计算不再完全依赖第三方库。

### English Brief

C++20 extends `chrono` with calendar and timezone support. It improves standard handling of dates, clocks, and civil time.

### 中文详细解释

C++11 `chrono` 主要处理 duration、time_point 和 clock。C++20 增加 year/month/day、weekday、time zone database 等能力，可以更标准地表达日期和本地时间。

面试中可以提到：时间处理非常容易出错，尤其是时区、夏令时、闰秒和本地化。标准库提供了更强基础，但业务系统仍要明确使用 UTC 还是本地时间，存储和显示要分层。

### 面试怎么说

我会内部存储尽量使用明确时钟和 UTC 时间点，展示层再转换成本地时间，避免业务逻辑混用时区。

---

# C++23

## 38. C++23：deducing this

### 中文简要介绍

deducing this 允许显式声明对象参数，让成员函数模板更容易保留 `const`、引用和值类别信息。

### English Brief

Deducing `this` makes the object parameter explicit and deducible. It helps remove duplicated overloads for const and value-category variations.

### 中文详细解释

以前类成员函数为了支持 `const&`、`&`、`&&` 等不同对象类别，常要写多组重载。C++23 的显式对象参数可以写 `this auto&& self`，让 `self` 像普通模板参数一样推导，从而减少重复。

面试中不用写很复杂语法，但要知道它解决的是成员函数中 `this` 不可模板推导的问题。它对 fluent API、wrapper、optional-like 类型、CRTP 替代写法都有价值。

### 面试怎么说

我会把 deducing this 理解成成员函数的完美转发工具，主要价值是减少 const/ref-qualified overload 重复。

## 39. C++23：`std::expected`

### 中文简要介绍

`std::expected<T, E>` 表达“要么成功得到 T，要么失败得到 E”，适合需要显式错误信息的返回值。

### English Brief

`std::expected` represents either a value or an error. It is useful when failure is expected and the caller should handle error information explicitly.

### 中文详细解释

`optional<T>` 只能表达有没有值，不能表达为什么失败。`expected<T, E>` 把成功值和错误值放在类型系统里，适合解析、IO、协议处理、无异常边界等场景。调用方必须面对错误路径，而不是忽略异常或检查全局错误码。

面试中可以比较异常、optional、expected：异常适合无法局部处理的异常失败；optional 适合单纯 absence；expected 适合失败是正常业务分支且错误信息重要的场景。

### 对比表

| 工具 | 表达含义 | 适合场景 |
|---|---|---|
| `std::optional<T>` | 可能无值 | 无复杂失败原因 |
| `std::expected<T, E>` | 值或错误 | 错误信息重要 |
| exception | 抛出失败 | 异常路径、构造失败 |

## 40. C++23：`std::print`

### 中文简要介绍

`std::print` 提供直接输出格式化文本的标准接口，建立在 format 风格格式化之上。

### English Brief

`std::print` prints formatted text directly. It is a convenient standard alternative to stream chains and `printf` for simple output.

### 中文详细解释

C++20 有 `std::format` 返回字符串，C++23 的 `std::print` 进一步提供直接输出能力，写法简洁，例如 `std::print("id = {}\n", id);`。它让简单日志、命令行工具输出、调试信息更直接。

面试中要知道它不是替代所有日志系统。生产服务通常仍会使用结构化日志、级别、异步写入和上下文信息；`print` 更像标准化的便利输出工具。

### 小例子

```cpp
std::print("value = {}\n", value);
```

## 41. C++23：`std::mdspan`

### 中文简要介绍

`std::mdspan` 是多维非拥有数组视图，适合矩阵、图像、张量等连续或自定义布局数据访问。

### English Brief

`std::mdspan` is a non-owning multidimensional view. It is useful for numerical code, images, matrices, and layout-aware data access.

### 中文详细解释

`span` 主要是一维连续视图，`mdspan` 把视图扩展到多维索引，并允许描述 layout 和 accessor。它不拥有数据，只负责用多维坐标解释底层存储。

面试中可以结合性能说：图像和矩阵代码不仅关心元素类型，还关心行主序/列主序、stride、cache locality。`mdspan` 提供标准抽象，有助于把算法和存储布局解耦。

### 面试怎么说

我会把 `mdspan` 用在需要多维索引但不想复制数据的数值或图像处理接口里，同时明确底层内存生命周期由外部管理。

## 42. C++23：ranges 增强

### 中文简要介绍

C++23 继续增强 ranges，补充更多 views 和算法能力，让范围管道更完整、更接近实际数据处理需求。

### English Brief

C++23 extends ranges with more views and algorithms. It makes range pipelines more practical for real-world transformations.

### 中文详细解释

C++20 ranges 建立了基础模型，C++23 补充更多常用组件，例如 zip、enumerate、chunk、slide 等方向的能力，让多个序列组合、分块处理、带索引遍历更自然。

面试中不用死背每个 view，而要说出 ranges 的设计方向：惰性视图、组合式数据处理、减少临时容器。风险仍然是生命周期和可读性，复杂管道需要拆分命名。

### 面试怎么说

我会用 ranges 表达清晰的数据流；如果管道太长，我会拆成中间变量或普通循环，保证团队能维护。

## 43. C++23：flat containers

### 中文简要介绍

C++23 引入 `flat_map`、`flat_set` 等扁平关联容器，通常基于有序连续存储，适合读多写少且关注 cache locality 的场景。

### English Brief

Flat containers provide associative-container interfaces over contiguous sorted storage. They can be faster for lookup-heavy, small-to-medium datasets with infrequent updates.

### 中文详细解释

传统 `std::map` / `std::set` 通常基于树，节点分散在堆上，迭代和查找会受到 cache miss 影响。flat containers 使用连续存储保存有序数据，提升局部性，但插入删除可能需要移动元素。

面试中要说清楚取舍：如果频繁插入删除，树或 hash 容器可能更合适；如果数据构建后主要查询和遍历，flat container 可能性能更好。最终仍要根据数据规模和 profiling 决定。

### 对比表

| 容器 | 存储 | 适合场景 |
|---|---|---|
| `std::map` | 节点树 | 频繁插入、稳定引用、按序 |
| `std::unordered_map` | hash table | 平均快速查找、不需要顺序 |
| `std::flat_map` | 连续有序存储 | 读多写少、缓存友好 |

## 44. C++23：`std::generator`

### 中文简要介绍

`std::generator` 是基于 coroutine 的惰性序列生成工具，适合按需产生元素。

### English Brief

`std::generator` provides coroutine-based lazy sequence generation. It is useful when values should be produced on demand instead of stored eagerly.

### 中文详细解释

生成器可以用 `co_yield` 一个个产生值，调用方像遍历范围一样消费。它适合流式数据、遍历树结构、生成组合结果等场景，避免一次性构建完整容器。

面试中要知道它背后依赖 coroutine 状态机和生命周期管理。惰性生成可以节省内存，但也可能让控制流更隐蔽；如果逻辑简单，普通容器或迭代器仍然更直接。

### 面试怎么说

我会在数据天然是流式、可能很大或生成成本高时考虑 generator；如果数据规模小且需要随机访问，直接容器更简单。
