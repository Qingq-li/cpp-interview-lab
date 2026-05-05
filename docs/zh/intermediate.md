# C++ 面试笔记：中级篇

这一篇针对 1 到 5 年经验常见问题。重点不再是“知道概念”，而是“能不能解释 tradeoff，能不能把现代 C++ 用对”。

阅读时建议按这个顺序组织答案：

1. 先说清语言规则和工程取舍，不只背术语。
2. 再用 English explanation 练习英文面试表达。
3. 重点比较资源管理、异常安全、并发边界和 STL 行为差异。
4. 最后用示例代码和中文注释确认自己能解释运行结果。

---

## 1. Rule of Three、Rule of Five、Rule of Zero 是什么？

### 核心答案

- Rule of Three：手写析构、拷贝构造、拷贝赋值中的一个，通常就要考虑另外两个
- Rule of Five：现代 C++ 还要加上移动构造和移动赋值
- Rule of Zero：优先把资源管理交给标准库类型，自己不手写特殊成员


### English explanation

In an English interview, I would answer it like this:

- Rule of Three: if you define a destructor, copy constructor, or copy assignment operator, you usually need to consider the other two as well
- Rule of Five: Modern C++ also adds move construction and move assignment
- Rule of Zero: prefer standard library resource-owning members so the class does not need hand-written special members.

### 错误回答示例

- “Rule of Five 就是比 Rule of Three 多两个函数，需要全写”
- “所有类都应该手写五大函数”
- “Rule of Zero 就是什么都不写，靠运气”

### 面试官想听什么

- 你是否理解这些规则是资源管理经验总结
- 你是否知道现代风格最推崇的是 Rule of Zero

### 项目里怎么说

在工程里我会尽量让成员本身就是资源安全的类型，比如 `std::string`、`std::vector`、`std::unique_ptr`，这样类本身大多数情况下不需要自己管理拷贝、移动和析构。

### 深入解释

- 这些规则不是死记硬背的语法表，而是资源类设计经验
- 一旦类自己接管资源生命周期，就必须认真考虑拷贝、赋值、移动和销毁之间的一致性
- Rule of Zero 的核心思想是“少自己管资源，少自己写特殊成员”，从设计上降低出错概率
- 标准库容器和智能指针已经把大量资源管理问题处理好了，优先复用通常比手写更稳

### 示例

```cpp
#include <memory>

class Buffer {
public:
    explicit Buffer(size_t n) : data(std::make_unique<int[]>(n)) {}

private:
    std::unique_ptr<int[]> data;
};
```

### 代码讲解

- `std::unique_ptr<int[]> data;` 是真正管理资源的成员
- `std::make_unique<int[]>(n)` 把动态数组所有权直接交给 `unique_ptr`
- 这个类没有手写析构、拷贝、移动函数，正是 Rule of Zero 的典型例子

---

## 2. 左值、右值、将亡值分别是什么？

### 核心答案

- 左值有身份、可取地址
- 右值通常是临时值
- 将亡值是即将被移动资源的对象表达式


### English explanation

In an English interview, I would answer it like this:

- An lvalue has identity and can usually be addressed
- rvalues are usually temporary values
- An xvalue is an expression whose resources can be reused, typically because it is about to be moved from.

### 错误回答示例

- “右值就是常量”
- “有名字的一定是左值，没名字的一定是右值”
- “`std::move(x)` 真正执行了移动”

### 面试官想听什么

- 你是否知道值类别影响重载解析和移动语义
- 你是否能把语言术语和实际代码行为对应起来

### 项目里怎么说

我不会在业务代码里硬背术语，但在设计接口时会明确哪些参数要复制，哪些可以移动，哪些要完美转发，这背后本质上就是值类别问题。

### 深入解释

- 左值强调“有身份、可持续存在”，右值更偏向“临时结果”
- `std::move(x)` 不会真的移动资源，它只是把 `x` 转成更适合匹配移动重载的表达式
- 模板里的 `T&&` 不一定是右值引用，推导上下文下它可能是转发引用
- 值类别是理解移动语义、完美转发和重载决议的地基

### 示例

```cpp
#include <string>
#include <utility>

int main() {
    std::string s = "hello";
    std::string t = s + " world";
    std::string u = std::move(s);
}
```

### 代码讲解

- `s` 是有名字的对象，因此是左值
- `s + " world"` 产生临时结果，体现右值
- `std::move(s)` 不会移动资源本身，它只是把 `s` 转成更适合匹配移动语义的表达式

---

## 3. 什么是移动语义？为什么它重要？

### 核心答案

移动语义允许对象把内部资源转移给另一个对象，而不是复制整份资源。


### English explanation

In an English interview, I would answer it like this:

Move semantics allow an object to transfer internal resources to another object rather than copying the entire resource.

### 错误回答示例

- “移动就是偷指针”
- “用了 `std::move` 一定更快”
- “被 move 之后对象就彻底不能用了”

### 面试官想听什么

- 你是否知道移动语义的目标是减少深拷贝成本
- 你是否知道 moved-from 对象仍需保持可析构、可赋值的有效状态

### 项目里怎么说

在大对象返回、容器扩容、值语义封装这些地方，移动语义能显著减少内存分配和复制成本。但我不会为了“看起来现代”而到处乱加 `std::move`。

### 深入解释

- 移动语义常见于把资源所有权从一个对象转交给另一个对象，而不是复制资源本身
- 容器在扩容时如果元素支持高效移动，往往能显著降低重分配成本
- 不是所有类型移动都比拷贝便宜，小型标量类型的差别通常不明显
- 被移动对象仍然必须处于有效状态，只是值通常不应再依赖

### 示例

```cpp
#include <iostream>
#include <string>
#include <utility>

int main() {
    std::string a = "very large string";
    std::string b = std::move(a);

    std::cout << b << '\n';
}
```

### 代码讲解

- `std::string a = "very large string";` 表示一个普通对象
- `std::string b = std::move(a);` 把 `a` 转成右值语义，允许 `b` 接管内部资源
- 这段代码重点要看的是：移动语义通常发生在构造/赋值位置，而不是 `std::move` 自己“做了什么”

---

## 4. 拷贝构造和拷贝赋值有什么区别？

### 核心答案

- 拷贝构造发生在新对象初始化阶段
- 拷贝赋值发生在对象已存在时


### English explanation

In an English interview, I would answer it like this:

- Copy construction occurs during the initialization phase of the new object
- Copy assignment occurs when the object already exists

### 错误回答示例

- “只要有等号就是赋值”
- “这两个函数写一个就够了”
- “默认版本一定安全”

### 面试官想听什么

- 你是否理解生命周期阶段的不同
- 你是否知道资源类型默认拷贝可能有风险

### 项目里怎么说

如果一个类型管理外部资源，我会明确审视它的拷贝语义，避免默认生成行为无意中做出浅拷贝。必要时会禁用拷贝，只保留移动。

### 深入解释

- 拷贝构造处理“创建时复制”，拷贝赋值处理“已存在对象被覆盖”
- 拷贝赋值通常还要考虑自赋值、旧资源释放和异常安全
- 对资源类来说，这两个操作往往都不是“复制几个成员”这么简单
- 因此现代设计里常见做法是：可拷贝就明确支持，不可拷贝就显式删除

### 示例

```cpp
#include <iostream>

class Item {
public:
    Item() = default;

    Item(const Item&) {
        std::cout << "copy ctor\n";
    }

    Item& operator=(const Item&) {
        std::cout << "copy assign\n";
        return *this;
    }
};

int main() {
    Item a;
    Item b = a;

    Item c;
    c = a;
}
```

### 代码讲解

- `Item b = a;` 会触发拷贝构造，因为这里是在创建新对象
- `c = a;` 会触发拷贝赋值，因为 `c` 已经存在
- 这段代码最重要的是区分“初始化阶段”和“赋值阶段”

---

## 5. 深拷贝和浅拷贝有什么区别？

### 核心答案

- 浅拷贝只复制地址或句柄
- 深拷贝复制底层资源本身


### English explanation

In an English interview, I would answer it like this:

- Shallow copy only copies the address or handle
- Deep copy copies the underlying resource itself

### 错误回答示例

- “浅拷贝就是性能更好的深拷贝”
- “只要程序能跑，浅拷贝也没问题”
- “用了类就自动深拷贝”

### 面试官想听什么

- 你是否理解浅拷贝在资源类上会带来悬空指针和 double free
- 你是否知道现代 C++ 更推荐直接用资源安全成员，减少自己实现深拷贝的机会

### 项目里怎么说

如果我不得不写资源类，会明确写出深拷贝或直接禁用拷贝。更常见的是改设计，让底层资源由现成 RAII 类型管理，从根源上避开这个问题。

### 深入解释

- 浅拷贝在普通值类型上未必有问题，但在拥有资源的类型上风险极高
- 两个对象若只是复制同一块资源地址，析构时可能重复释放
- 深拷贝意味着每个对象都拥有自己的独立资源副本，代价通常更高但语义更安全
- 如果业务不需要拷贝语义，禁止拷贝往往比勉强实现深拷贝更合理

### 示例

```cpp
#include <cstring>

class Text {
public:
    explicit Text(const char* s) {
        data = new char[std::strlen(s) + 1];
        std::strcpy(data, s);
    }

    Text(const Text& other) {
        data = new char[std::strlen(other.data) + 1];
        std::strcpy(data, other.data);
    }

    ~Text() {
        delete[] data;
    }

private:
    char* data = nullptr;
};
```

### 代码讲解

- `data = new char[...]` 表示对象内部自己管理一块动态内存
- `Text(const Text& other)` 里重新分配内存并复制内容，体现深拷贝
- `~Text()` 里 `delete[] data;` 负责释放资源
- 重点看：如果不自定义拷贝构造，默认浅拷贝就会很危险

---

## 6. 智能指针有哪些？怎么选？

### 核心答案

- `unique_ptr` 表达独占所有权
- `shared_ptr` 表达共享所有权
- `weak_ptr` 表达非拥有观察者


### English explanation

In an English interview, I would answer it like this:

- `unique_ptr` expresses exclusive ownership
- `shared_ptr` expresses shared ownership
- `weak_ptr` expresses a non-owning observer

### 错误回答示例

- “`shared_ptr` 比 `unique_ptr` 更高级，所以默认用它”
- “有智能指针就不需要考虑生命周期”
- “`weak_ptr` 就是不安全的指针”

### 面试官想听什么

- 你是否能用所有权模型解释三者区别
- 你是否知道 `shared_ptr` 的代价和循环引用风险

### 项目里怎么说

我会默认从 `unique_ptr` 开始建模，因为它表达“只有一个负责人释放资源”，接口和生命周期都最清楚。只有对象确实被多个独立模块共同延长生命周期时，才使用 `shared_ptr`；一旦出现双向关系、缓存、观察者或回调注册，就要主动设计哪一侧用 `weak_ptr` 表达非拥有关系。

### 深入解释

- `unique_ptr` 最轻量，语义最清晰，天然适合独占所有权
- `shared_ptr` 内部通常带引用计数控制块，会引入额外内存和原子操作成本
- `weak_ptr` 不拥有对象，只是安全观察者，常用于打破引用环
- 面试中最重要的不是背 API，而是能把这三者和所有权模型对应起来

### 示例

```cpp
#include <memory>
#include <vector>

class Node {
public:
    std::shared_ptr<Node> next;
    std::weak_ptr<Node> prev;
};

class Pipeline {
public:
    void add(std::unique_ptr<Node> node) {
        nodes_.push_back(std::move(node));
    }

private:
    std::vector<std::unique_ptr<Node>> nodes_;
};
```

### 代码讲解

- `std::shared_ptr<Node> next;` 表示当前节点共享拥有下一个节点
- `std::weak_ptr<Node> prev;` 表示前驱只是观察关系，不参与拥有
- `Pipeline::add(std::unique_ptr<Node> node)` 表示调用方把节点所有权交给流水线
- `std::move(node)` 是所有权转移，不是普通复制
- 重点是看清：智能指针首先是所有权建模工具，不是“自动 delete 的高级裸指针”

---

## 7. 为什么推荐 `make_unique` 和 `make_shared`？

### 核心答案

它们更安全、更简洁，也能减少直接写 `new` 带来的异常路径问题。


### English explanation

In an English interview, I would answer it like this:

They are safer, more concise, and can reduce the exception path problems caused by writing `new` directly.

### 错误回答示例

- “只是少打几个字”
- “`make_shared` 永远最好”
- “用了工厂函数就没有性能问题了”

### 面试官想听什么

- 你是否知道 `make_shared` 可能合并分配控制块和对象
- 你是否明白接口层推荐返回智能指针，而不是暴露裸所有权

### 项目里怎么说

只要没有自定义删除器、私有构造控制或特殊内存资源要求，我会优先使用 `make_unique`/`make_shared`，因为对象构造和智能指针绑定在同一个表达式里完成，异常路径更简单。需要注意的是，`make_shared` 可能让对象和控制块一次分配，这通常更快，但弱引用长期存在时也可能延长对象内存块的保留时间。

### 深入解释

- `make_unique` 和 `make_shared` 让对象创建和智能指针绑定成为一个表达式，减少中间状态
- `make_shared` 往往会把控制块和对象一起分配，减少一次分配开销
- 但 `make_shared` 也会让对象和控制块生命周期耦合得更紧，某些大对象或自定义释放场景要谨慎
- 选择它们的核心理由仍然是安全性和接口一致性

### 示例

```cpp
#include <memory>

struct Task {
    int id;
    explicit Task(int i) : id(i) {}
};

int main() {
    auto a = std::make_unique<Task>(1);
    auto b = std::make_shared<Task>(2);
}
```

### 代码讲解

- `make_unique` 创建独占所有权对象
- `make_shared` 创建共享所有权对象
- 这段代码重点看：对象创建和智能指针绑定在一个表达式里完成，更安全也更统一
- 如果需要自定义 deleter 或特殊分配策略，才考虑显式构造智能指针

---

## 8. 模板是什么？为什么 C++ 模板能力强？

### 核心答案

模板让你写类型无关的泛型代码，并在编译期生成具体实例。它是 STL、traits、泛型算法和零开销抽象的基础，但工程上要控制模板复杂度、编译时间和错误信息成本。


### English explanation

In an English interview, I would answer it like this:

Templates let you write type-independent generic code and generate concrete instances at compile time.

### 错误回答示例

- “模板就是宏的高级版”
- “模板只适合写算法题”
- “模板一定会让代码很复杂”

### 面试官想听什么

- 你是否理解模板是 STL 和零开销抽象的基础
- 你是否知道模板强大但也需要控制复杂度

### 项目里怎么说

我倾向只在真正能消除重复、表达类型约束、或把运行时分发前移到编译期时使用模板。业务逻辑不会为了泛型而泛型；基础组件、容器适配、序列化工具、数值算法和类型安全封装更适合模板化。C++20 可用 concepts 把模板要求写在接口上，降低调用错误的诊断成本。

### 深入解释

- 模板最强大的地方是零开销抽象，很多泛型能力在编译后不会额外产生运行时分发成本
- 但模板也会带来编译时间、报错信息和阅读复杂度问题
- STL 就是模板价值的典型例子：同一套算法可以作用于不同容器和类型
- 工程上应把模板用在“可复用的抽象层”，而不是让所有业务逻辑都模板化

### 示例

```cpp
#include <iostream>

template <typename T>
T maxValue(T a, T b) {
    return a > b ? a : b;
}

int main() {
    std::cout << maxValue(3, 5) << '\n';
    std::cout << maxValue(2.5, 7.1) << '\n';
}
```

### 代码讲解

- `template <typename T>` 声明模板参数
- `maxValue(3, 5)` 推导出 `T = int`
- `maxValue(2.5, 7.1)` 推导出 `T = double`
- 重点是看：模板用“一份逻辑”适配多种类型
- 如果模板约束变复杂，现代 C++ 更推荐用 concepts 或清晰的 traits 辅助表达要求

---

## 9. `auto`、`decltype`、`using` 在工程里有什么作用？

### 核心答案

- `auto` 用于简化类型书写
- `decltype` 从表达式推导类型
- `using` 用于定义更可读的类型别名和模板别名


### English explanation

In an English interview, I would answer it like this:

- `auto` is used to simplify type writing
- `decltype` deduces type from expression
- `using` is used to define more readable type aliases and template aliases

### 错误回答示例

- “`auto` 会让代码更动态”
- “`decltype` 没什么实际价值”
- “`using` 和 `typedef` 完全一样，没必要学”

### 面试官想听什么

- 你是否知道现代 C++ 倾向减少冗长模板类型书写
- 你是否会把这些特性用于提升可读性而不是隐藏类型信息

### 项目里怎么说

我会在迭代器、复杂模板返回类型和 traits 场景使用 `auto` / `decltype` / `using`，但如果显式类型能让业务语义更清晰，也不会盲目省略。

### 深入解释

- `auto` 是静态类型推导，不会让 C++ 变成动态类型语言
- `decltype` 很适合写泛型代码时保留表达式精确类型
- `using` 比 `typedef` 更现代，尤其在模板别名场景更清晰
- 这些工具的目标是降低样板代码，而不是隐藏本应清晰暴露的类型语义

### 示例

```cpp
#include <type_traits>
#include <vector>

int main() {
    std::vector<int> nums = {1, 2, 3};
    auto it = nums.begin();

    using ValueType = decltype(*it);
    static_assert(std::is_same_v<std::remove_reference_t<ValueType>, int>);
}
```

### 代码讲解

- `auto it = nums.begin();` 用 `auto` 简化复杂迭代器类型
- `decltype(*it)` 根据表达式 `*it` 推导类型
- `using ValueType = ...` 给这个类型起别名
- `static_assert(...)` 在编译期验证推导结果符合预期

---

## 10. `virtual`、`override`、`final` 应该怎么理解？

### 核心答案

- `virtual` 声明动态分发点
- `override` 明确这是重写
- `final` 禁止进一步重写或继承


### English explanation

In an English interview, I would answer it like this:

- `virtual` declares dynamic dispatch points
- `override` makes it clear that this is an override
- `final` prohibits further overriding or inheritance

### 错误回答示例

- “加不加 `override` 都一样”
- “`final` 只是性能优化关键字”
- “只要有继承就该用 `virtual`”

### 面试官想听什么

- 你是否知道动态分发是接口设计选择，不是默认开销
- 你是否把 `override` 当作安全检查，而不是装饰语法

### 项目里怎么说

我会把 `override` 当作默认习惯，保证重写行为可检查；而 `final` 只在确实要封住扩展点时使用，不会为了微小优化而到处加。

### 深入解释

- `virtual` 决定是否走动态分发，是对象模型层面的设计选择
- `override` 是一种编译期保护，能防止签名写错导致“看起来像重写，其实不是”
- `final` 可以加在类或虚函数上，用于明确禁止进一步扩展
- 这些关键字不是装饰语法，而是接口演化和可维护性工具

### 示例

```cpp
class Base {
public:
    virtual void run() {}
    virtual ~Base() = default;
};

class Derived final : public Base {
public:
    void run() override {}
};
```

### 代码讲解

- `virtual void run()` 在基类中声明动态分发点
- `void run() override` 明确告诉编译器这是重写
- `class Derived final` 表示该类不允许再被继承
- 重点看三个关键字各自承担的角色不同

---

## 11. `emplace_back` 和 `push_back` 有什么区别？

### 核心答案

- `push_back` 接收一个现成对象
- `emplace_back` 直接在容器尾部构造对象


### English explanation

In an English interview, I would answer it like this:

- `push_back` receives a ready-made object
- `emplace_back` constructs objects directly at the end of the container

### 错误回答示例

- “`emplace_back` 一定更快”
- “`push_back` 已经过时了”
- “它们只是名字不同”

### 面试官想听什么

- 你是否知道两者语义差别
- 你是否知道不要盲目迷信 `emplace_back`

### 项目里怎么说

如果已有对象就直接 `push_back`，如果是现场构造新元素，我会考虑 `emplace_back`。选择重点是表达意图，而不是机械追求某个 API。

### 深入解释

- `push_back` 是把一个对象放入容器，`emplace_back` 是把构造参数交给容器原地构造
- 在某些场景下 `emplace_back` 可以省去临时对象，但不是所有类型都能明显受益
- 如果代码可读性下降，盲目使用 `emplace_back` 并不值得
- 这类问题真正考的是你是否理解对象构造和移动发生在哪里

### 示例

```cpp
#include <string>
#include <vector>

struct User {
    std::string name;
    int age;
};

int main() {
    std::vector<User> users;
    users.push_back(User{"Alice", 20});
    users.emplace_back("Bob", 22);
}
```

### 代码讲解

- `users.push_back(User{"Alice", 20});` 先构造临时对象，再放入容器
- `users.emplace_back("Bob", 22);` 直接把构造参数交给容器原地构造元素
- 这段代码重点看“已有对象插入”和“原地构造”两种思路

---

## 12. 什么是异常安全？常见等级有哪些？

### 核心答案

异常安全描述的是异常发生后程序状态是否仍然可接受。

- 基本保证：无泄漏，对象仍有效
- 强保证：操作失败像没执行过一样
- 不抛异常保证：承诺不抛异常


### English explanation

In an English interview, I would answer it like this:

Exception safety describes whether the program state is still acceptable after an exception occurs.

- Basic guarantee: no leaks, objects are still valid
- Strong guarantee: if the operation fails, it will be as if it has never been executed.
- No exception guarantee: Promise not to throw exceptions

### 错误回答示例

- “用了 try/catch 就叫异常安全”
- “异常安全就是不让程序崩”
- “业务代码里不用考虑这个”

### 面试官想听什么

- 你是否知道 RAII 是异常安全的基础
- 你是否理解不同等级对应不同实现成本

### 项目里怎么说

在资源类、容器封装和事务式操作里，我会优先保证至少基本保证：资源不泄漏、对象不半坏。如果接口语义像“替换配置”“提交批量结果”，我会尽量用先构造临时对象、成功后 swap/commit 的方式提供强保证；析构、释放资源、移动和 swap 路径则要特别关注 `noexcept`。

### 深入解释

- 异常安全不是“把异常 catch 住”，而是异常发生后对象和资源是否仍处于可接受状态
- 基本保证关注“不会泄漏、对象仍有效”，强保证关注“失败即回滚”
- 不抛异常保证在析构函数、移动操作、清理路径上尤其关键
- RAII 和清晰的所有权模型，是获得异常安全的前提

### 示例

```cpp
#include <string>
#include <utility>
#include <vector>

class NameList {
public:
    void replaceAll(std::vector<std::string> next) {
        names_.swap(next); // next 构造成功后再提交新状态
    }

    void add(std::string name) {
        names_.push_back(std::move(name)); // 至少保持 vector 的异常安全保证
    }

private:
    std::vector<std::string> names_;
};
```

### 代码讲解

- `replaceAll` 的参数 `next` 在函数体执行前已经构造完成，构造失败不会影响 `names_`
- `swap` 是提交动作，成功后当前对象获得新状态，旧状态随 `next` 析构释放
- `add` 依赖 `std::vector` 和 `std::string` 的 RAII 管理资源，异常时不会泄漏
- 面试重点是：异常安全不是多写 `try/catch`，而是设计好资源所有权和状态提交顺序

---

## 13. `map` 和 `unordered_map` 有什么区别？

### 核心答案

- `map` 有序，通常基于平衡树
- `unordered_map` 无序，通常基于哈希表


### English explanation

In an English interview, I would answer it like this:

- `map` is ordered, usually based on a balanced tree
- `unordered_map` is unordered, usually based on a hash table

### 错误回答示例

- “`unordered_map` 一定更快”
- “`map` 就是旧容器，基本不用”
- “选容器只看时间复杂度表”

### 面试官想听什么

- 你是否会结合顺序性、稳定性、哈希质量、内存开销来判断
- 你是否理解平均复杂度和最坏复杂度的区别

### 项目里怎么说

如果需要有序遍历、范围查询或稳定的输出顺序，我会选 `map`；如果主要是 key lookup 且哈希质量可控，会优先考虑 `unordered_map`。

### 深入解释

- `map` 通常基于平衡树，键有序，迭代输出天然有序
- `unordered_map` 通常基于哈希表，平均查找更快，但不保证顺序
- 哈希表会受负载因子、哈希函数质量和冲突情况影响
- 选容器时不能只看平均复杂度，还要看顺序需求、内存开销和最坏情况

### 示例

```cpp
#include <map>
#include <unordered_map>

int main() {
    std::map<int, int> ordered;
    std::unordered_map<int, int> hashed;

    ordered[2] = 20;
    ordered[1] = 10;

    hashed[2] = 20;
    hashed[1] = 10;
}
```

### 代码讲解

- `std::map<int, int> ordered;` 是有序关联容器
- `std::unordered_map<int, int> hashed;` 是无序哈希容器
- 两边插入相同键值对，但底层组织方式不同
- 重点不是打印结果，而是认清一边关注顺序，一边关注平均查找效率

---

## 14. 什么是竞态条件？如何避免？

### 核心答案

多个线程并发访问共享数据，且至少有一个线程写入，没有正确同步时，就可能发生竞态条件。


### English explanation

In an English interview, I would answer it like this:

When multiple threads access shared data concurrently and at least one thread writes, without proper synchronization, a race condition may occur.

### 错误回答示例

- “只要是多线程就有 race”
- “加了 `volatile` 就线程安全”
- “原子变量能替代所有锁”

### 面试官想听什么

- 你是否理解共享可变状态才是问题根源
- 你是否知道锁和原子各自适用边界

### 项目里怎么说

我会优先减少共享状态，其次才用同步工具。业务代码优先锁和成熟并发容器，只有在热点路径确实证明值得时才考虑更复杂的原子方案。

### 深入解释

- 竞态条件的根本问题是“共享可变状态缺少同步”，不是“线程数多”
- `mutex` 适合保护复合操作，`atomic` 更适合简单共享状态
- `volatile` 不是线程同步工具，它解决的是编译器优化与外部可观察副作用问题
- 大多数业务代码优先保证正确性和可读性，而不是急着做 lock-free

### 示例

```cpp
#include <iostream>
#include <mutex>
#include <thread>

int counter = 0;
std::mutex mtx;

void add() {
    for (int i = 0; i < 10000; ++i) {
        std::lock_guard<std::mutex> lock(mtx);
        ++counter;
    }
}

int main() {
    std::thread t1(add);
    std::thread t2(add);
    t1.join();
    t2.join();
    std::cout << counter << '\n';
}
```

### 代码讲解

- `std::mutex mtx;` 是共享锁，保护 `counter`
- `std::lock_guard<std::mutex> lock(mtx);` 每次进入临界区时自动加锁
- `std::thread t1(add); std::thread t2(add);` 表示两个线程并发执行同一逻辑
- 重点是观察：加锁的位置包围了共享变量修改

---

## 15. `constexpr` 的意义是什么？

### 核心答案

`constexpr` 允许值和函数在满足条件时参与编译期求值。


### English explanation

In an English interview, I would answer it like this:

`constexpr` allows values and functions to participate in compile-time evaluation when the required conditions are met.

### 错误回答示例

- “`constexpr` 就是比 `const` 更快”
- “写了 `constexpr` 就一定在编译期执行”
- “只适合写算法题”

### 面试官想听什么

- 你是否知道 `constexpr` 的核心是可参与编译期求值
- 你是否能区分可编译期求值和必须编译期求值

### 项目里怎么说

我会在编译期常量、轻量纯函数、配置常量和模板参数相关逻辑中使用 `constexpr`，这样既能提升表达力，也能让错误更早暴露。

### 深入解释

- `constexpr` 表示“可以在编译期求值”，不是“保证一定在编译期执行”
- 它和 `const` 有交集，但关注点不同：`const` 强调不可修改，`constexpr` 强调编译期可求值
- 随着标准演进，`constexpr` 能做的事情越来越多
- 对面试来说，关键是能讲清它如何帮助写出更强约束、更早暴露错误的代码

### 示例

```cpp
#include <array>

constexpr int square(int x) {
    return x * x;
}

int main() {
    std::array<int, square(4)> arr{};
}
```

### 代码讲解

- `constexpr int square(int x)` 表示这个函数可以在编译期求值
- `std::array<int, square(4)> arr{}` 要求数组长度在编译期已知
- 这里最值得注意的是：`square(4)` 出现在模板参数位置，因此它必须能参与编译期计算

---

## 16. `reserve()` 和 `resize()` 有什么区别？

### 核心答案

- `reserve()` 调整容量，通常不改变当前元素个数
- `resize()` 调整元素个数，可能新增或删除元素


### English explanation

In an English interview, I would answer it like this:

- `reserve()` adjusts the capacity, usually without changing the current number of elements
- `resize()` adjusts the number of elements, possibly adding or deleting elements

### 错误回答示例

- “`reserve(100)` 之后就有 100 个元素了”
- “`resize()` 只是提前扩容”
- “两者只是名字不同”

### 面试官想听什么

- 你是否知道 `capacity` 和 `size` 不是一回事
- 你是否知道 `reserve` 常用于减少重复扩容

### 项目里怎么说

如果我能预估 `vector` 大致会放多少元素，我会提前 `reserve()` 降低扩容次数；如果我需要真正改变元素数量，才会用 `resize()`。

### 深入解释

- `reserve()` 更像是为未来插入预留内存
- `resize()` 会直接改变容器逻辑大小
- 这题本质考察的是你是否理解 `vector` 的 `size`/`capacity` 模型

### 示例

```cpp
#include <iostream>
#include <vector>

int main() {
    std::vector<int> nums;
    nums.reserve(10);
    std::cout << nums.size() << " " << nums.capacity() << '\n';

    nums.resize(5);
    std::cout << nums.size() << " " << nums.capacity() << '\n';
}
```

### 代码讲解

- `nums.reserve(10);` 只预留容量，不会生成 10 个元素
- 第一次输出里 `size()` 仍然是 `0`
- `nums.resize(5);` 之后才真正把元素个数改成 5
- 这段代码重点在于区分“容量”和“当前元素个数”

---

## 17. 什么是迭代器失效？为什么它重要？

### 核心答案

迭代器失效是指容器修改后，原来的迭代器、引用或指针不再有效。


### English explanation

In an English interview, I would answer it like this:

Iterator invalidation means that after the container is modified, the original iterator, reference or pointer is no longer valid.

### 错误回答示例

- “拿到迭代器之后就能一直用”
- “只有删除元素才会让迭代器失效”
- “所有容器的失效规则都差不多”

### 面试官想听什么

- 你是否知道不同容器的失效规则不同
- 你是否知道 `vector` 扩容是高频失效来源

### 项目里怎么说

写 STL 代码时，我会特别留意容器修改是否会让已有迭代器、引用和指针失效，尤其是 `vector` 插入和扩容场景。

### 深入解释

- `vector` 扩容时往往会整体搬迁内存，因此旧迭代器常失效
- `list` 节点分散存储，很多修改下迭代器更稳定
- 这类问题很常导致“代码能编译，但运行时行为诡异”

### 示例

```cpp
#include <vector>

int main() {
    std::vector<int> nums = {1, 2, 3};
    auto it = nums.begin();

    nums.push_back(4);
    // it 这里可能已经失效
}
```

### 代码讲解

- `auto it = nums.begin();` 先保存一个旧迭代器
- `nums.push_back(4);` 可能触发扩容
- 一旦扩容，旧迭代器 `it` 可能不再指向有效位置
- 重点是：容器修改后，别想当然复用旧迭代器

---

## 18. `noexcept` 是什么？为什么重要？

### 核心答案

`noexcept` 用来声明一个函数不会抛出异常，这既影响接口语义，也可能影响标准库优化选择。


### English explanation

In an English interview, I would answer it like this:

`noexcept` is used to declare that a function will not throw exceptions, which affects both interface semantics and may also affect standard library optimization choices.

### 错误回答示例

- “`noexcept` 只是文档注释”
- “写了 `noexcept` 就一定更快”
- “所有函数都该加 `noexcept`”

### 面试官想听什么

- 你是否知道 `noexcept` 是接口承诺
- 你是否知道标准库在某些场景会更偏好 `noexcept` 的移动操作

### 项目里怎么说

我会在析构、swap、移动操作和明确不应失败的清理逻辑上认真考虑 `noexcept`，而不是机械地给所有函数乱加。

### 深入解释

- 如果 `noexcept` 函数真的抛异常，程序通常会终止
- 它既是“不会抛”的承诺，也是某些库优化和异常安全策略的重要信号
- 因此只有在你能真正保证时才应写上

### 示例

```cpp
class Buffer {
public:
    Buffer(Buffer&&) noexcept = default;
    Buffer& operator=(Buffer&&) noexcept = default;
};

int main() {}
```

### 代码讲解

- `Buffer(Buffer&&) noexcept` 表示移动构造承诺不抛异常
- `operator=(Buffer&&) noexcept` 表示移动赋值也不抛异常
- 这类声明常见于资源类型，因为标准容器会更信任这类移动操作

---

## 19. `std::atomic` 和 `std::mutex` 应该怎么初步区分？

### 核心答案

- `std::atomic` 适合简单原子读写和计数类共享状态
- `std::mutex` 适合保护一段复合逻辑或多个变量的一致性


### English explanation

In an English interview, I would answer it like this:

- `std::atomic` is suitable for simple atomic reading and writing and counting class shared state
- `std::mutex` is suitable for protecting the consistency of a piece of complex logic or multiple variables

### 错误回答示例

- “有了 `atomic` 就不需要锁了”
- “锁一定比原子慢，所以不用锁”
- “原子变量天然能保护复杂对象状态”

### 面试官想听什么

- 你是否知道原子和锁适用范围不同
- 你是否知道复合操作往往仍需要锁

### 项目里怎么说

如果只是简单计数器、标志位，我会优先考虑 `atomic`；如果要维护多个共享状态之间的一致性，我通常仍会使用 `mutex`。

### 深入解释

- 原子操作擅长单个变量的安全更新
- 但如果逻辑涉及“检查后再修改”“多个字段一起更新”，锁通常更直接可靠
- 并发设计关键不只是追求快，而是先把正确性边界讲清楚

### 示例

```cpp
#include <atomic>

std::atomic<int> counter = 0;

int main() {
    ++counter;
}
```

### 代码讲解

- `std::atomic<int> counter` 表示这个整数的读写具有原子性
- `++counter;` 是线程安全的单变量自增操作
- 这段代码重点看：原子适合简单共享状态，不等于能替代所有锁

---

## 20. `std::unique_lock` 和 `std::lock_guard` 有什么区别？

### 核心答案

- `lock_guard` 更轻量，适合简单作用域加锁
- `unique_lock` 更灵活，支持延迟加锁、手动解锁和条件变量配合


### English explanation

In an English interview, I would answer it like this:

- `lock_guard` is more lightweight and suitable for simple scope locking
- `unique_lock` is more flexible and supports delayed locking, manual unlocking and condition variable cooperation

### 错误回答示例

- “`unique_lock` 只是名字更长”
- “能用 `unique_lock` 就不用 `lock_guard`”
- “条件变量和两者都没关系”

### 面试官想听什么

- 你是否知道 `unique_lock` 的灵活性来自额外状态管理
- 你是否知道 `condition_variable` 常要求配合 `unique_lock`

### 项目里怎么说

如果只是简单临界区，我会优先 `lock_guard`；如果需要配合等待、手动控制锁时机或更复杂的锁管理，我会使用 `unique_lock`。

### 深入解释

- `lock_guard` 更像最简单的 RAII 锁壳
- `unique_lock` 提供更多控制能力，因此也更重一些
- 选择关键不在于“哪个更新”，而在于场景需要哪种控制粒度

### 示例

```cpp
#include <condition_variable>
#include <mutex>

std::mutex mtx;
std::condition_variable cv;
bool ready = false;

int main() {
    std::unique_lock<std::mutex> lock(mtx);
    cv.wait(lock, [] { return ready; });
}
```

### 代码讲解

- `std::unique_lock<std::mutex> lock(mtx);` 是可被条件变量管理的锁对象
- `cv.wait(lock, [] { return ready; });` 等待时会临时释放锁，被唤醒后再重新持有锁
- 这里不能直接用 `lock_guard`，因为它不提供这种灵活控制能力

---

## 21. `std::future` 和 `std::async` 是什么？

### 核心答案

- `std::async` 用于异步启动任务
- `std::future` 用于稍后获取异步任务结果


### English explanation

In an English interview, I would answer it like this:

- `std::async` is used to start tasks asynchronously
- `std::future` is used to obtain asynchronous task results later

### 错误回答示例

- “`async` 就是开线程的别名”
- “`future` 只是普通返回值包装”
- “有线程池后就完全不需要了解它们”

### 面试官想听什么

- 你是否知道它们提供的是更高层的异步结果模型
- 你是否知道 `future.get()` 会获取结果并同步等待完成

### 项目里怎么说

如果只是简单异步计算并在后面取结果，我会考虑 `async/future` 这类更高层工具；如果任务调度、资源控制更复杂，再考虑线程池或自定义执行器。

### 深入解释

- `std::thread` 更偏向“管理线程”
- `std::future` 更偏向“管理结果”
- 这两类抽象关注点不同，一个偏执行体，一个偏异步结果交付

### 示例

```cpp
#include <future>
#include <iostream>

int main() {
    auto fut = std::async(std::launch::async, [] {
        return 42;
    });

    std::cout << fut.get() << '\n';
}
```

### 代码讲解

- `std::async(std::launch::async, [] { return 42; })` 异步启动一个任务
- `[] { return 42; }` 是任务本体，这里又用了 lambda
- `auto fut` 是 `future`，表示“将来会拿到一个结果”
- `fut.get()` 会等待任务完成并取出结果

---

## 22. 移动构造和移动赋值怎么正确写？

### 核心答案

- 移动构造从临时或可被移动对象接管资源
- 移动赋值要处理已有资源、自赋值和异常安全
- 移动后源对象必须保持有效但值不作保证
- 能用标准库成员表达资源时，优先 Rule of Zero，不要手写移动函数

### English explanation

In an English interview, I would answer it like this:

A move constructor and move assignment operator transfer resources from a source object, leaving the source valid but with an unspecified value. In modern C++, the best move operation is often the one generated automatically from well-designed RAII members.

### 错误回答示例

- “move 后对象不能析构”
- “移动赋值不用处理旧资源”
- “所有成员都直接 `std::move` 就完事”

### 面试官想听什么

- 你是否理解 moved-from 状态
- 你是否知道移动赋值要覆盖已有对象

### 项目里怎么说

资源类需要自己写移动时，我会先保证三件事：目标对象不会泄漏旧资源，源对象移动后仍可析构和重新赋值，移动操作能安全标成 `noexcept`。如果成员已经是 `std::string`、`std::vector`、`unique_ptr` 这类 RAII 类型，我会优先让编译器生成移动操作。

### 深入解释

- 移动构造面对的是新对象
- 移动赋值面对的是已有对象
- 标准库容器会偏好 `noexcept` move
- 手写移动赋值时常见 bug 是先覆盖目标指针，忘记释放旧资源，或者没有处理自移动
- 对拥有资源的裸指针类，移动后通常把源指针置空，让源对象保持可析构状态

### 示例

```cpp
#include <utility>

class Buffer {
public:
    explicit Buffer(int* p = nullptr) : data_(p) {}
    ~Buffer() { delete data_; }

    Buffer(Buffer&& other) noexcept : data_(other.data_) {
        other.data_ = nullptr; // 源对象保持可析构
    }

    Buffer& operator=(Buffer&& other) noexcept {
        if (this != &other) {
            delete data_;       // 释放旧资源
            data_ = other.data_;
            other.data_ = nullptr;
        }
        return *this;
    }

private:
    int* data_ = nullptr;
};
```

### 代码讲解

- 移动构造直接接管 `other.data_`
- 移动赋值先释放目标旧资源
- 把源指针置空，避免析构时重复释放
- `noexcept` 对资源类很重要，因为容器扩容时可能据此选择移动而不是拷贝
- 这段代码是教学用裸资源例子，真实项目里更推荐用 `unique_ptr` 成员获得 Rule of Zero
---

## 23. copy-and-swap idiom 是什么？

### 核心答案

- 先用值参数创建副本，再和当前对象交换资源
- 能自然处理自赋值
- 常用于实现强异常安全的赋值操作
- 代价是可能多一次临时对象构造或拷贝，性能敏感类型要评估成本

### English explanation

In an English interview, I would answer it like this:

The copy-and-swap idiom implements assignment by copying first and then swapping resources, which naturally handles self-assignment and can provide strong exception safety.

### 错误回答示例

- “copy-and-swap 是移动语义的替代品”
- “swap 可以随便抛异常”
- “所有类都必须这么写”

### 面试官想听什么

- 你是否理解先成功构造副本再提交改变
- 你是否知道它的额外拷贝成本

### 项目里怎么说

如果资源类赋值逻辑复杂，我会考虑 copy-and-swap，因为它把“准备新状态”和“提交新状态”分开，容易获得强异常安全。性能关键路径上，我会评估它的额外临时对象、分配和 swap 成本；能用 Rule of Zero 的类型，通常不需要手写这个 idiom。

### 深入解释

- 参数按值会触发拷贝或移动
- 交换通常应 `noexcept`
- 旧资源随临时对象析构自动释放
- 这个 idiom 的关键是：先让可能失败的构造发生在提交之前
- 如果 swap 可能抛异常，就很难声称赋值操作具备强保证

### 示例

```cpp
#include <algorithm>
#include <vector>

class Numbers {
public:
    friend void swap(Numbers& a, Numbers& b) noexcept {
        using std::swap;
        swap(a.values_, b.values_);
    }

    Numbers& operator=(Numbers other) {
        swap(*this, other); // 提交新状态
        return *this;
    }

private:
    std::vector<int> values_;
};
```

### 代码讲解

- `other` 是已经构造好的副本或移动结果
- `swap(*this, other)` 后当前对象获得新资源
- 旧资源在 `other` 析构时释放
- 如果构造 `other` 失败，函数体不会执行，当前对象保持原状态
- `swap` 标成 `noexcept`，才能支撑强异常安全的提交步骤
---

## 24. 自赋值和异常安全为什么要一起考虑？

### 核心答案

- 自赋值是对象赋值给自己
- 赋值过程如果先释放旧资源再拷贝新资源，可能破坏自身
- 异常安全要求异常发生后对象仍保持合理状态
- 更稳的设计是先准备新资源，成功后再替换旧状态

### English explanation

In an English interview, I would answer it like this:

Self-assignment and exception safety matter because assignment often replaces existing state. A bad order of operations can destroy the source when the source is the same object.

### 错误回答示例

- “没人会写 `x = x`”
- “自赋值只要 if 判断就够了”
- “异常发生程序就结束，不用管状态”

### 面试官想听什么

- 你是否理解赋值操作的提交顺序
- 你是否能解释 strong guarantee

### 项目里怎么说

写资源类赋值时，我不会只靠 `if (this == &rhs)` 兜底，而会把提交顺序设计正确：先准备新资源，成功后再替换旧资源。因为自赋值可能通过引用、容器元素别名或指针间接发生，异常也可能出现在分配和拷贝中。

### 深入解释

- 自赋值可能通过别名间接发生
- 强异常安全强调失败后状态不变
- RAII 成员能简化异常安全
- 对纯标准库成员类，默认生成的赋值通常已经正确处理自赋值和异常安全
- 对手写裸资源类，错误顺序常见为“先 delete 自己，再从 rhs 读数据”，自赋值时 rhs 也被破坏

### 示例

```cpp
#include <string>
#include <utility>

class User {
public:
    User& operator=(const User& rhs) {
        if (this == &rhs) {
            return *this;
        }
        std::string tmp = rhs.name_; // 先构造新资源
        name_ = std::move(tmp);      // 再提交
        return *this;
    }

private:
    std::string name_;
};
```

### 代码讲解

- `this == &rhs` 处理直接自赋值
- 临时字符串先完成构造
- 真实资源管理由 `std::string` 负责
- `name_ = std::move(tmp)` 是提交新状态，失败风险已经被前面的临时对象构造隔离
- 在更复杂资源类中，copy-and-swap 往往比手写多个分支更容易保证正确
---

## 25. `std::string_view` 的生命周期风险是什么？

### 核心答案

`std::string_view` 是非拥有字符串视图，只保存指针和长度，不延长底层字符的生命周期。它适合作为只读参数，但不能长期保存指向临时 `std::string`、局部字符串或已释放缓冲区的 view。

### English explanation

In an English interview, I would answer it like this:

`std::string_view` is a non-owning view over characters. It is efficient for read-only parameters, but it becomes dangerous if the view outlives the referenced string.

### 错误回答示例

- “`string_view` 是更快的 `string`，可以直接替代成员变量”
- “字符串字面量和临时 `std::string` 的生命周期一样”
- “函数返回 `string_view` 一定没有拷贝，所以更好”

### 面试官想听什么

- 你是否知道 `string_view` 不拥有内存
- 你是否能区分参数视图和持久化存储
- 你是否知道悬垂 view 通常不会立刻报错，但会造成隐蔽 UB

### 项目里怎么说

我会把 `string_view` 用在“不保存，只读取”的参数上，比如解析、日志格式化、查找接口。如果类需要保存文本，我会存 `std::string`；如果函数要返回数据，也要确认返回的 view 指向的存储比调用者活得更久。

### 深入解释

- `string_view` 没有所有权，因此不会分配、释放或拷贝字符内容
- 它可以绑定到 `std::string`、字符串字面量、字符数组的一段连续字符
- 最大风险是底层字符串销毁或重新分配后，view 仍被使用
- 成员变量使用 `string_view` 时要特别谨慎，除非对象明确只是观察外部稳定存储

### 示例

```cpp
#include <iostream>
#include <string>
#include <string_view>

void print(std::string_view text) {
    std::cout << text << '
';
}

int main() {
    std::string name = "cpp";
    print(name);
    print("interview");
}
```

### 代码讲解

- `print` 不保存 `text`，只在调用期间读取，所以 `string_view` 合适
- `name` 在 `print(name)` 调用期间仍然存在，view 有效
- 字符串字面量有静态存储期，`print("interview")` 也安全
- 如果把 `text` 存到全局或异步任务里，就必须重新审视生命周期

---

## 26. `std::optional` 适合表达什么？

### 核心答案

`std::optional<T>` 表达一个结果“可能有值，也可能没有值”。它适合没有复杂失败原因的查询、解析、缓存命中等场景，比 `-1`、空字符串这类特殊值更清楚。

### English explanation

In an English interview, I would answer it like this:

`std::optional` represents an optional value without inventing sentinel values. It is best for absence, not for rich error reporting.

### 错误回答示例

- “`optional` 就是可以为空的指针”
- “所有错误都应该用 `optional` 表达”
- “用了 `optional` 就不用处理失败原因”

### 面试官想听什么

- 你是否知道它表达“可能没有值”，不是“失败详情”
- 你是否能和 sentinel value、异常、错误码区分
- 你是否会在使用前检查值存在

### 项目里怎么说

查询、解析、缓存命中这类“可能没有结果，但没有复杂错误原因”的接口，我会用 `optional<T>`。如果失败原因对调用方重要，我会使用错误码、异常或 `expected` 风格结果，而不是把所有失败都压成 `nullopt`。

### 深入解释

- `optional<T>` 内部要么没有对象，要么原地存放一个 `T`
- 它不是指针语义，不表达共享、借用或对象身份
- `value()` 在无值时会抛异常，面试中更推荐展示 `if (opt)` 或 `value_or`
- 不适合携带多种失败原因

### 示例

```cpp
#include <iostream>
#include <optional>

std::optional<int> findId(bool ok) {
    if (!ok) {
        return std::nullopt;
    }
    return 7;
}

int main() {
    if (auto id = findId(true)) {
        std::cout << *id << '
';
    }
}
```

### 代码讲解

- `std::nullopt` 明确表达“没有 id”
- `if (auto id = ...)` 先检查是否有值，再解引用
- 这里没有错误详情，所以 `optional<int>` 比 `-1` 这种特殊值更清楚
- 如果需要说明为什么查找失败，就应该换成能携带错误信息的返回类型

---

## 27. `std::variant` 和继承多态怎么取舍？

### 核心答案

`std::variant` 适合候选类型集合固定的值语义场景；继承多态适合实现集合需要运行时扩展的场景。两者不是新旧替代关系，而是扩展方向不同。

### English explanation

In an English interview, I would answer it like this:

`std::variant` works well when the set of alternatives is closed, while virtual polymorphism is better when new implementations need to be added without changing the original type.

### 错误回答示例

- “`variant` 是更现代的虚函数，应该替代继承”
- “继承多态总是更慢，所以不用”
- “`variant` 不需要处理所有分支”

### 面试官想听什么

- 你是否知道 `variant` 是封闭类型集合，虚函数是开放实现集合
- 你是否理解 `visit` 要覆盖所有候选类型
- 你是否能从 ABI、扩展性、值语义和性能角度取舍

### 项目里怎么说

如果消息、状态、AST 节点这类类型集合由本模块控制且变化不频繁，我会考虑 `variant`，因为值语义清楚、无需堆分配和虚表。如果实现需要第三方插件扩展，或运行时替换行为更重要，我会使用继承多态或类型擦除。

### 深入解释

- `variant<A, B, C>` 的候选类型在编译期固定，新增类型要改定义和访问逻辑
- 虚函数接口允许新增派生类，但接口本身要稳定
- `variant` 通常把对象直接存储在自身内部，大小由最大候选类型决定
- 继承多态常通过指针或引用访问对象，涉及所有权和动态分配设计

### 示例

```cpp
#include <iostream>
#include <string>
#include <variant>

int main() {
    std::variant<int, std::string> value = "ok";
    std::visit([](const auto& x) {
        std::cout << x << '
';
    }, value);
}
```

### 代码讲解

- `variant<int, std::string>` 表示值只能是这两种类型之一
- `std::visit` 根据当前实际候选类型调用 lambda
- lambda 的 `auto` 参数让同一段访问逻辑适配多个候选类型
- 如果不同类型行为差异很大，访问逻辑可能变复杂，这是 `variant` 的维护成本

---

## 28. erase-remove idiom 是什么？

### 核心答案

erase-remove idiom 用 `std::remove` 先把保留元素前移，再用容器的 `erase` 真正删除尾部无效区间。关键点是：算法不改变容器大小，容器成员函数才负责删除元素。

### English explanation

In an English interview, I would answer it like this:

The erase-remove idiom first moves the elements to keep toward the front, then erases the remaining tail from the container.

### 错误回答示例

- “`std::remove` 会直接删除 vector 元素”
- “调用 `remove` 后容器 size 会变小”
- “erase-remove 对所有容器都一样推荐”

### 面试官想听什么

- 你是否知道算法不拥有容器，不能改变容器大小
- 你是否能解释 `remove` 返回的新逻辑结尾
- 你是否知道 C++20 的 `std::erase/std::erase_if`

### 项目里怎么说

在维护旧代码或 C++17 代码时，我会熟练使用 erase-remove；如果项目能用 C++20，我更倾向 `std::erase` 或 `std::erase_if`，因为意图更直接，少写迭代器边界也更不容易出错。

### 深入解释

- `std::remove` 是算法，只能重排 `[begin, end)` 范围内的元素
- 它把要保留的元素前移，并返回新的逻辑结尾
- `vector::erase` 才真正销毁尾部多余元素并缩小 size
- 对关联容器，通常直接用成员 `erase` 或 C++20 `erase_if`

### 示例

```cpp
#include <algorithm>
#include <vector>

int main() {
    std::vector<int> values{1, 2, 3, 2};
    values.erase(std::remove(values.begin(), values.end(), 2), values.end());
}
```

### 代码讲解

- `std::remove` 把不等于 2 的元素前移
- 返回值表示新的逻辑末尾
- `erase(..., values.end())` 删除逻辑末尾之后的旧元素
- 重点是区分“算法重排”和“容器删除”两个步骤

---

## 29. `unordered_map` rehash 和迭代器失效怎么理解？

### 核心答案

`unordered_map` rehash 会重建桶数组，通常会让所有迭代器失效。批量插入前合理 `reserve` 可以减少 rehash 次数，也能降低保存迭代器后继续插入的风险。

### English explanation

In an English interview, I would answer it like this:

Rehashing rebuilds the bucket array of an `unordered_map` and invalidates iterators, so code should not keep iterators across insertions that may trigger rehash.

### 错误回答示例

- “`unordered_map` 插入永远不会影响已有迭代器”
- “调用 `reserve` 只是性能优化，不影响正确性”
- “rehash 只改变内部顺序，外部不用关心”

### 面试官想听什么

- 你是否知道 rehash 会重建桶数组并使迭代器失效
- 你是否会在批量插入前使用 `reserve`
- 你是否区分 iterator、reference、pointer 的失效规则

### 项目里怎么说

批量构建哈希表时，我会提前 `reserve`，既减少 rehash 成本，也避免循环中长期保存迭代器后又插入导致失效。代码审查时看到“保存 iterator 后继续 emplace”会特别留意。

### 深入解释

- `unordered_map` 按桶组织元素，负载因子过高时可能 rehash
- rehash 会让所有迭代器失效，因为桶结构被重建
- `reserve(n)` 根据元素数量预留桶，`rehash(n)` 直接请求桶数量
- 即使引用/指针在某些操作下仍有效，也不应把它和迭代器规则混淆

### 示例

```cpp
#include <string>
#include <unordered_map>

int main() {
    std::unordered_map<int, std::string> table;
    table.reserve(100);
    table.emplace(1, "one");
}
```

### 代码讲解

- `reserve(100)` 表示预计要存 100 个元素
- 这样后续插入更不容易触发 rehash
- `emplace` 可能构造新元素，也可能在容量压力下触发 rehash
- 面试回答要把性能和迭代器失效两个维度都说清

---

## 30. lambda 捕获值和引用有什么生命周期陷阱？

### 核心答案

值捕获保存副本，引用捕获保存外部对象引用。异步、延迟执行、线程池和回调列表中，引用捕获或 `[this]` 很容易在原对象销毁后变成悬垂引用。

### English explanation

In an English interview, I would answer it like this:

Value capture copies state into the lambda, while reference capture refers to external objects. Reference capture is risky when the lambda outlives the captured variables.

### 错误回答示例

- “只背 API 名字，不说明生命周期、所有权或工程边界”
- “只要能编译就说明用法正确”
- “现代 C++ 特性一定总是更好”

### 面试官想听什么

- 你是否能说清它解决的问题
- 你是否能讲出生命周期、所有权或性能边界
- 你是否知道现代写法的适用边界

### 项目里怎么说

在工程里我会先看它是否让接口语义、生命周期或错误边界更清楚，再看它是否降低重复和运行时成本；不会为了显得现代而牺牲可读性和可维护性。

### 深入解释

- 这类工具的价值通常来自更准确地表达所有权、生命周期、约束或数据流
- 使用前要确认调用方是否需要拥有、共享、保存或异步使用数据
- 性能收益要结合真实路径评估，不能只按 API 新旧判断
- 面试回答要同时讲出适用场景和不适用场景

### 示例

```cpp
#include <functional>

std::function<int()> makeCounter() {
    int value = 1;
    return [value] { return value; };
}

int main() {
    return makeCounter()();
}
```

### 代码讲解

- 示例展示了该工具的核心用法
- 重点是它表达的接口语义，而不是 API 名字本身
- 面试时要把示例和具体风险联系起来，而不是只背语法
- 能说清边界比单纯背语法更重要

---

## 31. `std::bind` 和 lambda 怎么取舍？

### 核心答案

现代 C++ 中通常优先 lambda，因为捕获、参数和调用逻辑都更显式。`std::bind` 主要出现在旧代码或简单适配场景，复杂占位符会明显降低可读性。

### English explanation

In an English interview, I would answer it like this:

Lambdas are usually clearer than `std::bind` because captures and parameters are explicit at the call site.

### 错误回答示例

- “只背 API 名字，不说明生命周期、所有权或工程边界”
- “只要能编译就说明用法正确”
- “现代 C++ 特性一定总是更好”

### 面试官想听什么

- 你是否能说清它解决的问题
- 你是否能讲出生命周期、所有权或性能边界
- 你是否知道现代写法的适用边界

### 项目里怎么说

在工程里我会先看它是否让接口语义、生命周期或错误边界更清楚，再看它是否降低重复和运行时成本；不会为了显得现代而牺牲可读性和可维护性。

### 深入解释

- 这类工具的价值通常来自更准确地表达所有权、生命周期、约束或数据流
- 使用前要确认调用方是否需要拥有、共享、保存或异步使用数据
- 性能收益要结合真实路径评估，不能只按 API 新旧判断
- 面试回答要同时讲出适用场景和不适用场景

### 示例

```cpp
#include <iostream>

void print(int base, int value) {
    std::cout << base + value << '\n';
}

int main() {
    auto f = [](int value) { print(10, value); };
    f(5);
}
```

### 代码讲解

- 示例展示了该工具的核心用法
- 重点是它表达的接口语义，而不是 API 名字本身
- 面试时要把示例和具体风险联系起来，而不是只背语法
- 能说清边界比单纯背语法更重要

---

## 32. `std::function` 的类型擦除成本是什么？

### 核心答案

`std::function` 通过类型擦除统一保存不同 callable，代价可能是间接调用、无法内联和小对象优化之外的动态分配。它适合运行时保存异构回调，不是模板的零成本替代品。

### English explanation

In an English interview, I would answer it like this:

`std::function` type-erases callable objects. It improves flexibility but can add indirect-call overhead and sometimes allocation.

### 错误回答示例

- “只背 API 名字，不说明生命周期、所有权或工程边界”
- “只要能编译就说明用法正确”
- “现代 C++ 特性一定总是更好”

### 面试官想听什么

- 你是否能说清它解决的问题
- 你是否能讲出生命周期、所有权或性能边界
- 你是否知道现代写法的适用边界

### 项目里怎么说

在工程里我会先看它是否让接口语义、生命周期或错误边界更清楚，再看它是否降低重复和运行时成本；不会为了显得现代而牺牲可读性和可维护性。

### 深入解释

- 这类工具的价值通常来自更准确地表达所有权、生命周期、约束或数据流
- 使用前要确认调用方是否需要拥有、共享、保存或异步使用数据
- 性能收益要结合真实路径评估，不能只按 API 新旧判断
- 面试回答要同时讲出适用场景和不适用场景

### 示例

```cpp
#include <functional>
#include <iostream>

int main() {
    std::function<int(int)> f = [](int x) { return x + 1; };
    std::cout << f(1) << '\n';
}
```

### 代码讲解

- 示例展示了该工具的核心用法
- 重点是它表达的接口语义，而不是 API 名字本身
- 面试时要把示例和具体风险联系起来，而不是只背语法
- 能说清边界比单纯背语法更重要

---

## 33. `shared_ptr` 控制块和 aliasing constructor 是什么？

### 核心答案

`shared_ptr` 控制块保存引用计数、删除器和分配器等所有权元数据。aliasing constructor 可以共享一个对象的控制块，但让 `shared_ptr` 的 `get()` 指向另一个子对象地址。

### English explanation

In an English interview, I would answer it like this:

A `shared_ptr` control block stores ownership metadata. The aliasing constructor can share ownership with one object while pointing to a subobject.

### 错误回答示例

- “只背 API 名字，不说明生命周期、所有权或工程边界”
- “只要能编译就说明用法正确”
- “现代 C++ 特性一定总是更好”

### 面试官想听什么

- 你是否能说清它解决的问题
- 你是否能讲出生命周期、所有权或性能边界
- 你是否知道现代写法的适用边界

### 项目里怎么说

在工程里我会先看它是否让接口语义、生命周期或错误边界更清楚，再看它是否降低重复和运行时成本；不会为了显得现代而牺牲可读性和可维护性。

### 深入解释

- 这类工具的价值通常来自更准确地表达所有权、生命周期、约束或数据流
- 使用前要确认调用方是否需要拥有、共享、保存或异步使用数据
- 性能收益要结合真实路径评估，不能只按 API 新旧判断
- 面试回答要同时讲出适用场景和不适用场景

### 示例

```cpp
#include <memory>
#include <vector>

int main() {
    auto owner = std::make_shared<std::vector<int>>(3, 1);
    std::shared_ptr<int> first(owner, owner->data());
}
```

### 代码讲解

- 示例展示了该工具的核心用法
- 重点是它表达的接口语义，而不是 API 名字本身
- 面试时要把示例和具体风险联系起来，而不是只背语法
- 能说清边界比单纯背语法更重要

---

## 34. `enable_shared_from_this` 为什么存在？

### 核心答案

`enable_shared_from_this` 让对象在成员函数中安全获得共享同一控制块的 `shared_ptr`。它避免 `shared_ptr<T>(this)` 创建第二个控制块导致重复释放。

### English explanation

In an English interview, I would answer it like this:

`enable_shared_from_this` lets an object safely create a `shared_ptr` sharing the existing control block, avoiding a second control block from raw `this`.

### 错误回答示例

- “只背 API 名字，不说明生命周期、所有权或工程边界”
- “只要能编译就说明用法正确”
- “现代 C++ 特性一定总是更好”

### 面试官想听什么

- 你是否能说清它解决的问题
- 你是否能讲出生命周期、所有权或性能边界
- 你是否知道现代写法的适用边界

### 项目里怎么说

在工程里我会先看它是否让接口语义、生命周期或错误边界更清楚，再看它是否降低重复和运行时成本；不会为了显得现代而牺牲可读性和可维护性。

### 深入解释

- 这类工具的价值通常来自更准确地表达所有权、生命周期、约束或数据流
- 使用前要确认调用方是否需要拥有、共享、保存或异步使用数据
- 性能收益要结合真实路径评估，不能只按 API 新旧判断
- 面试回答要同时讲出适用场景和不适用场景

### 示例

```cpp
#include <memory>

struct Session : std::enable_shared_from_this<Session> {
    std::shared_ptr<Session> self() { return shared_from_this(); }
};

int main() {
    auto s = std::make_shared<Session>();
    auto again = s->self();
}
```

### 代码讲解

- 示例展示了该工具的核心用法
- 重点是它表达的接口语义，而不是 API 名字本身
- 面试时要把示例和具体风险联系起来，而不是只背语法
- 能说清边界比单纯背语法更重要

---

## 35. `weak_ptr::lock()` 的正确用法是什么？

### 核心答案

`weak_ptr::lock()` 会尝试把非拥有观察者提升成临时 `shared_ptr`。使用前必须检查返回值，成功后才能在这个局部强引用生命周期内安全访问对象。

### English explanation

In an English interview, I would answer it like this:

`weak_ptr::lock()` safely tries to promote a weak observer to a `shared_ptr`; the result must be checked before use.

### 错误回答示例

- “只背 API 名字，不说明生命周期、所有权或工程边界”
- “只要能编译就说明用法正确”
- “现代 C++ 特性一定总是更好”

### 面试官想听什么

- 你是否能说清它解决的问题
- 你是否能讲出生命周期、所有权或性能边界
- 你是否知道现代写法的适用边界

### 项目里怎么说

在工程里我会先看它是否让接口语义、生命周期或错误边界更清楚，再看它是否降低重复和运行时成本；不会为了显得现代而牺牲可读性和可维护性。

### 深入解释

- 这类工具的价值通常来自更准确地表达所有权、生命周期、约束或数据流
- 使用前要确认调用方是否需要拥有、共享、保存或异步使用数据
- 性能收益要结合真实路径评估，不能只按 API 新旧判断
- 面试回答要同时讲出适用场景和不适用场景

### 示例

```cpp
#include <iostream>
#include <memory>

int main() {
    std::weak_ptr<int> weak;
    {
        auto strong = std::make_shared<int>(42);
        weak = strong;
    }
    if (auto locked = weak.lock()) {
        std::cout << *locked << '\n';
    }
}
```

### 代码讲解

- 示例展示了该工具的核心用法
- 重点是它表达的接口语义，而不是 API 名字本身
- 面试时要把示例和具体风险联系起来，而不是只背语法
- 能说清边界比单纯背语法更重要

---

## 36. `condition_variable` 为什么要配合谓词？

### 核心答案

条件变量可能虚假唤醒，也可能被通知后发现条件已被其他线程消费。谓词才是业务条件，推荐使用 `wait(lock, pred)` 在持锁状态下循环检查。

### English explanation

In an English interview, I would answer it like this:

A condition variable should be used with a predicate because wakeups can be spurious and the condition must be rechecked under the lock.

### 错误回答示例

- “只背 API 名字，不说明生命周期、所有权或工程边界”
- “只要能编译就说明用法正确”
- “现代 C++ 特性一定总是更好”

### 面试官想听什么

- 你是否能说清它解决的问题
- 你是否能讲出生命周期、所有权或性能边界
- 你是否知道现代写法的适用边界

### 项目里怎么说

在工程里我会先看它是否让接口语义、生命周期或错误边界更清楚，再看它是否降低重复和运行时成本；不会为了显得现代而牺牲可读性和可维护性。

### 深入解释

- 这类工具的价值通常来自更准确地表达所有权、生命周期、约束或数据流
- 使用前要确认调用方是否需要拥有、共享、保存或异步使用数据
- 性能收益要结合真实路径评估，不能只按 API 新旧判断
- 面试回答要同时讲出适用场景和不适用场景

### 示例

```cpp
#include <condition_variable>
#include <mutex>

std::mutex m;
std::condition_variable cv;
bool ready = false;

void waitReady() {
    std::unique_lock<std::mutex> lock(m);
    cv.wait(lock, [] { return ready; });
}

int main() {}
```

### 代码讲解

- 示例展示了该工具的核心用法
- 重点是它表达的接口语义，而不是 API 名字本身
- 面试时要把示例和具体风险联系起来，而不是只背语法
- 能说清边界比单纯背语法更重要

---

## 37. `std::promise` 和 `std::packaged_task` 是什么？

### 核心答案

`promise` 手动向 `future` 对应的 shared state 写入结果；`packaged_task` 把 callable 包装成会把返回值或异常写入 `future` 的任务。它们本身不负责创建线程。

### English explanation

In an English interview, I would answer it like this:

`std::promise` manually provides a result for a future, while `std::packaged_task` wraps a callable and exposes its result through a future.

### 错误回答示例

- “只背 API 名字，不说明生命周期、所有权或工程边界”
- “只要能编译就说明用法正确”
- “现代 C++ 特性一定总是更好”

### 面试官想听什么

- 你是否能说清它解决的问题
- 你是否能讲出生命周期、所有权或性能边界
- 你是否知道现代写法的适用边界

### 项目里怎么说

在工程里我会先看它是否让接口语义、生命周期或错误边界更清楚，再看它是否降低重复和运行时成本；不会为了显得现代而牺牲可读性和可维护性。

### 深入解释

- 这类工具的价值通常来自更准确地表达所有权、生命周期、约束或数据流
- 使用前要确认调用方是否需要拥有、共享、保存或异步使用数据
- 性能收益要结合真实路径评估，不能只按 API 新旧判断
- 面试回答要同时讲出适用场景和不适用场景

### 示例

```cpp
#include <future>
#include <iostream>

int main() {
    std::packaged_task<int()> task([] { return 42; });
    auto fut = task.get_future();
    task();
    std::cout << fut.get() << '\n';
}
```

### 代码讲解

- 示例展示了该工具的核心用法
- 重点是它表达的接口语义，而不是 API 名字本身
- 面试时要把示例和具体风险联系起来，而不是只背语法
- 能说清边界比单纯背语法更重要

---

## 38. `shared_mutex` 和读写锁适合什么场景？

### 核心答案

`shared_mutex` 允许多个读者并发或一个写者独占，适合读多写少且读临界区有一定成本的场景。它不一定比 `mutex` 快，写多或临界区很短时可能更差。

### English explanation

In an English interview, I would answer it like this:

`std::shared_mutex` allows multiple readers or one writer, which can help read-heavy workloads but is not automatically faster.

### 错误回答示例

- “只背 API 名字，不说明生命周期、所有权或工程边界”
- “只要能编译就说明用法正确”
- “现代 C++ 特性一定总是更好”

### 面试官想听什么

- 你是否能说清它解决的问题
- 你是否能讲出生命周期、所有权或性能边界
- 你是否知道现代写法的适用边界

### 项目里怎么说

在工程里我会先看它是否让接口语义、生命周期或错误边界更清楚，再看它是否降低重复和运行时成本；不会为了显得现代而牺牲可读性和可维护性。

### 深入解释

- 这类工具的价值通常来自更准确地表达所有权、生命周期、约束或数据流
- 使用前要确认调用方是否需要拥有、共享、保存或异步使用数据
- 性能收益要结合真实路径评估，不能只按 API 新旧判断
- 面试回答要同时讲出适用场景和不适用场景

### 示例

```cpp
#include <mutex>
#include <shared_mutex>

std::shared_mutex m;
int value = 0;

int read() {
    std::shared_lock lock(m);
    return value;
}

void write(int v) {
    std::unique_lock lock(m);
    value = v;
}

int main() {}
```

### 代码讲解

- 示例展示了该工具的核心用法
- 重点是它表达的接口语义，而不是 API 名字本身
- 面试时要把示例和具体风险联系起来，而不是只背语法
- 能说清边界比单纯背语法更重要

---

## 39. `thread_local` 的使用场景是什么？

### 核心答案

`thread_local` 让每个线程拥有变量的独立实例，适合线程私有缓存、统计、随机数生成器或上下文。它不是跨线程共享工具，要注意线程池复用和析构时机。

### English explanation

In an English interview, I would answer it like this:

`thread_local` gives each thread its own instance of a variable, useful for per-thread state but requiring care with lifetime and initialization.

### 错误回答示例

- “只背 API 名字，不说明生命周期、所有权或工程边界”
- “只要能编译就说明用法正确”
- “现代 C++ 特性一定总是更好”

### 面试官想听什么

- 你是否能说清它解决的问题
- 你是否能讲出生命周期、所有权或性能边界
- 你是否知道现代写法的适用边界

### 项目里怎么说

在工程里我会先看它是否让接口语义、生命周期或错误边界更清楚，再看它是否降低重复和运行时成本；不会为了显得现代而牺牲可读性和可维护性。

### 深入解释

- 这类工具的价值通常来自更准确地表达所有权、生命周期、约束或数据流
- 使用前要确认调用方是否需要拥有、共享、保存或异步使用数据
- 性能收益要结合真实路径评估，不能只按 API 新旧判断
- 面试回答要同时讲出适用场景和不适用场景

### 示例

```cpp
#include <iostream>

int next() {
    thread_local int counter = 0;
    return ++counter;
}

int main() {
    std::cout << next() << ' ' << next() << '\n';
}
```

### 代码讲解

- 示例展示了该工具的核心用法
- 重点是它表达的接口语义，而不是 API 名字本身
- 面试时要把示例和具体风险联系起来，而不是只背语法
- 能说清边界比单纯背语法更重要

---

## 40. `noexcept` 对 move 和容器有什么影响？

### 核心答案

- `noexcept` 表达函数不抛异常
- 容器扩容时更愿意使用 `noexcept` move
- 错误标注 `noexcept` 会导致异常时终止程序
- 它既是优化信息，也是接口契约，不能为了性能随便加

### English explanation

In an English interview, I would answer it like this:

`noexcept` is part of an interface contract. Standard containers prefer noexcept move operations during reallocation because they can preserve stronger guarantees.

### 错误回答示例

- “`noexcept` 只是让代码更快，随便加没问题”
- “移动构造有没有 `noexcept` 对容器没影响”
- “函数标了 `noexcept` 后里面的异常会自动被吞掉”

### 面试官想听什么

- 你是否知道 `vector` 扩容时要在强异常安全和移动效率之间取舍
- 你是否理解 `noexcept` 是承诺，不是 try/catch
- 你是否知道错误的 `noexcept` 会触发 `std::terminate`

### 项目里怎么说

我会给真正不会抛的移动构造、移动赋值、swap 和清理函数标 `noexcept`，让容器和泛型代码可以做更好的选择。但如果函数内部会分配内存、调用未知回调或依赖可能抛异常的成员，我不会为了“优化”硬标 `noexcept`。

### 深入解释

- `std::vector` 扩容时要把旧元素搬到新存储；如果 move 可能抛，容器为了维持异常保证可能选择 copy
- 如果类型不可拷贝且 move 可能抛，容器实现能选择的安全路径会变少
- `noexcept` 表达“异常不会逃出函数”，一旦异常逃出会直接终止程序
- 标准库 traits 如 `std::is_nothrow_move_constructible_v<T>` 会读取这个契约

### 示例

```cpp
#include <iostream>
#include <type_traits>
#include <vector>

struct Item {
    Item() = default;
    Item(const Item&) = default;
    Item(Item&&) noexcept = default;
};

int main() {
    static_assert(std::is_nothrow_move_constructible_v<Item>);

    std::vector<Item> items;
    items.emplace_back();
    items.emplace_back();
}
```

### 代码讲解

- `Item(Item&&) noexcept = default;` 明确移动构造不会抛异常
- `is_nothrow_move_constructible_v<Item>` 让泛型代码能在编译期看到这个性质
- `vector` 扩容时更容易选择移动旧元素，从而减少拷贝成本
- 前提是这个承诺真实可靠；如果移动过程可能分配或调用可抛代码，就不应硬标 `noexcept`
---

## 41. `constexpr`、`consteval`、`constinit` 基础区别是什么？

### 核心答案

`constexpr` 允许在满足条件时编译期求值，`consteval` 要求每次调用都必须编译期求值，`constinit` 保证静态或线程存储期变量做静态初始化但不表示只读。

### English explanation

In an English interview, I would answer it like this:

`constexpr` permits compile-time evaluation, `consteval` requires it, and `constinit` guarantees static initialization for variables.

### 错误回答示例

- “只背 API 名字，不说明生命周期、所有权或工程边界”
- “只要能编译就说明用法正确”
- “现代 C++ 特性一定总是更好”

### 面试官想听什么

- 你是否能说清它解决的问题
- 你是否能讲出生命周期、所有权或性能边界
- 你是否知道现代写法的适用边界

### 项目里怎么说

在工程里我会先看它是否让接口语义、生命周期或错误边界更清楚，再看它是否降低重复和运行时成本；不会为了显得现代而牺牲可读性和可维护性。

### 深入解释

- 这类工具的价值通常来自更准确地表达所有权、生命周期、约束或数据流
- 使用前要确认调用方是否需要拥有、共享、保存或异步使用数据
- 性能收益要结合真实路径评估，不能只按 API 新旧判断
- 面试回答要同时讲出适用场景和不适用场景

### 示例

```cpp
#include <iostream>

constexpr int square(int x) { return x * x; }

int main() {
    constexpr int v = square(4);
    std::cout << v << '\n';
}
```

### 代码讲解

- 示例展示了该工具的核心用法
- 重点是它表达的接口语义，而不是 API 名字本身
- 面试时要把示例和具体风险联系起来，而不是只背语法
- 能说清边界比单纯背语法更重要

---

## 42. `std::span`（C++20）作为非拥有连续视图怎么用？

### 核心答案

`std::span<T>` 是非拥有连续内存视图，统一表达数组、`std::array`、`std::vector` 等连续序列参数。它不延长底层数据生命周期，也不适合非连续容器。

### English explanation

In an English interview, I would answer it like this:

`std::span` is a non-owning view over contiguous elements. It is useful for APIs that need access but not ownership.

### 错误回答示例

- “只背 API 名字，不说明生命周期、所有权或工程边界”
- “只要能编译就说明用法正确”
- “现代 C++ 特性一定总是更好”

### 面试官想听什么

- 你是否能说清它解决的问题
- 你是否能讲出生命周期、所有权或性能边界
- 你是否知道现代写法的适用边界

### 项目里怎么说

在工程里我会先看它是否让接口语义、生命周期或错误边界更清楚，再看它是否降低重复和运行时成本；不会为了显得现代而牺牲可读性和可维护性。

### 深入解释

- 这类工具的价值通常来自更准确地表达所有权、生命周期、约束或数据流
- 使用前要确认调用方是否需要拥有、共享、保存或异步使用数据
- 性能收益要结合真实路径评估，不能只按 API 新旧判断
- 面试回答要同时讲出适用场景和不适用场景

### 示例

```cpp
#include <iostream>
#include <span>
#include <vector>

void print(std::span<const int> values) {
    for (int v : values) {
        std::cout << v << ' ';
    }
}

int main() {
    std::vector<int> v{1, 2, 3};
    print(v);
}
```

### 代码讲解

- 示例展示了该工具的核心用法
- 重点是它表达的接口语义，而不是 API 名字本身
- 面试时要把示例和具体风险联系起来，而不是只背语法
- 能说清边界比单纯背语法更重要

---

## 43. `ranges`（C++20）的基本价值是什么？

### 核心答案

ranges 让算法直接操作 range，并通过 views 组合惰性数据处理管道。它提升表达力并减少 begin/end 样板，但 view 的生命周期和过长管道的可读性仍要谨慎。

### English explanation

In an English interview, I would answer it like this:

C++20 ranges make algorithms and views compose more naturally, often reducing temporary containers and boilerplate iterator pairs.

### 错误回答示例

- “只背 API 名字，不说明生命周期、所有权或工程边界”
- “只要能编译就说明用法正确”
- “现代 C++ 特性一定总是更好”

### 面试官想听什么

- 你是否能说清它解决的问题
- 你是否能讲出生命周期、所有权或性能边界
- 你是否知道现代写法的适用边界

### 项目里怎么说

在工程里我会先看它是否让接口语义、生命周期或错误边界更清楚，再看它是否降低重复和运行时成本；不会为了显得现代而牺牲可读性和可维护性。

### 深入解释

- 这类工具的价值通常来自更准确地表达所有权、生命周期、约束或数据流
- 使用前要确认调用方是否需要拥有、共享、保存或异步使用数据
- 性能收益要结合真实路径评估，不能只按 API 新旧判断
- 面试回答要同时讲出适用场景和不适用场景

### 示例

```cpp
#include <iostream>
#include <ranges>
#include <vector>

int main() {
    std::vector<int> v{1, 2, 3, 4};
    for (int x : v | std::views::filter([](int n) { return n % 2 == 0; })) {
        std::cout << x << '\n';
    }
}
```

### 代码讲解

- 示例展示了该工具的核心用法
- 重点是它表达的接口语义，而不是 API 名字本身
- 面试时要把示例和具体风险联系起来，而不是只背语法
- 能说清边界比单纯背语法更重要

---

## 44. Pimpl idiom 解决什么工程问题？

### 核心答案

- Pimpl 把实现细节隐藏到指针后面
- 可以减少头文件依赖和重新编译范围
- 代价是间接访问和额外分配
- 它常用于稳定 ABI、降低编译依赖和保护实现细节

### English explanation

In an English interview, I would answer it like this:

The Pimpl idiom hides implementation details behind a pointer, reducing compile-time dependencies and preserving ABI boundaries at the cost of indirection.

### 错误回答示例

- “Pimpl 只是为了少 include 几个头文件”
- “所有类都应该 Pimpl”
- “Pimpl 没有运行时成本”

### 面试官想听什么

- 你是否知道 Pimpl 解决的是编译依赖、实现隐藏和 ABI 边界
- 你是否理解它通常用 `unique_ptr<Impl>` 表达独占实现对象
- 你是否能说出代价：一次间接访问、动态分配、特殊成员函数位置要求

### 项目里怎么说

我会在公共 SDK、动态库接口、编译依赖很重的头文件里考虑 Pimpl。普通小型业务类如果没有 ABI 或编译时间压力，我不会机械使用，因为它会增加 indirection、分配和实现复杂度。

### 深入解释

- Pimpl 让头文件只暴露稳定外壳，真正成员放到 `.cpp` 中的 `Impl` 结构
- 改动 `Impl` 成员时，依赖头文件的调用方通常不需要重新编译
- `std::unique_ptr<Impl>` 要求析构函数通常在 `.cpp` 中定义，因为那里能看到完整的 `Impl`
- 如果对象极多、访问极频繁，Pimpl 的分配和间接访问成本需要评估

### 示例

```cpp
#include <memory>

class Widget {
public:
    Widget();
    ~Widget();

    Widget(Widget&&) noexcept;
    Widget& operator=(Widget&&) noexcept;

    Widget(const Widget&) = delete;
    Widget& operator=(const Widget&) = delete;

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};
```

### 代码讲解

- `struct Impl;` 是前置声明，头文件不暴露真实成员
- `std::unique_ptr<Impl>` 表示 `Widget` 独占实现对象
- 析构函数声明在头文件，定义通常放到 `.cpp`，因为销毁 `unique_ptr<Impl>` 需要完整类型
- 删除拷贝、保留移动是常见选择，避免不清晰的深拷贝语义
---

## 45. 如何控制编译依赖和头文件污染？

### 核心答案

- 头文件只包含必要依赖
- 能前置声明就不强行 include
- 避免在头文件里写 `using namespace`
- 公共头文件是依赖传播边界，写得越重，整个项目编译和耦合成本越高

### English explanation

In an English interview, I would answer it like this:

Compile dependencies can be controlled by keeping headers minimal, using forward declarations where possible, and avoiding namespace pollution in public headers.

### 错误回答示例

- “头文件 include 多一点没关系，反正能编译”
- “公共头文件里 `using namespace std;` 更方便”
- “前置声明总是能替代 include”

### 面试官想听什么

- 你是否理解头文件会被文本包含并传播依赖
- 你是否知道什么时候能前置声明，什么时候必须 include 完整定义
- 你是否能从模块边界、编译时间和命名空间污染角度说明工程取舍

### 项目里怎么说

我会把公共头文件当成稳定契约来写：只暴露必要类型和函数签名，把重实现依赖放到 `.cpp`。如果头文件被很多模块包含，任何多余 include、宏或 `using namespace` 都会放大成全项目的编译和维护成本。

### 深入解释

- 指针和引用成员/参数通常可以只前置声明类型
- 按值成员、继承基类、访问成员函数、`sizeof(T)` 等场景需要完整定义
- 头文件中的宏、全局 using、重 include 会污染所有包含者
- Pimpl、接口拆分、include-what-you-use 和 C++20 modules 都是控制依赖的不同工具

### 示例

```cpp
#pragma once
#include <memory>

class Engine; // 前置声明

class Car {
public:
    explicit Car(std::unique_ptr<Engine> engine);
    ~Car();

private:
    std::unique_ptr<Engine> engine_;
};
```

### 代码讲解

- `class Engine;` 足够声明 `std::unique_ptr<Engine>` 成员，但析构定义通常要放到看到完整 `Engine` 的 `.cpp`
- 头文件只 include `<memory>`，不需要把 `Engine` 的完整头文件传播给所有 `Car` 使用者
- 不在头文件写 `using namespace`，避免污染包含者作用域
- 这个例子展示的是“接口依赖最小化”，不是为了少写 include 而牺牲正确性

---

## 中级篇复习建议

- 每题先能讲出 tradeoff，再讲 API
- 凡是涉及资源管理，尽量回到所有权、生命周期、异常安全
- 凡是涉及性能，避免用“一定”“永远”这种绝对表达
