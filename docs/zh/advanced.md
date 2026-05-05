# C++ 面试笔记：高级篇

这一篇对应深入追问和区分度问题。回答重点不只是“是什么”，而是“为什么这样设计、这样设计的代价是什么、工程里如何取舍”。

阅读时建议按这个顺序组织答案：

1. 先给出精确定义，再解释它解决的问题。
2. 再用 English explanation 练习英文面试表达。
3. 主动说明代价、边界和现代 C++ 中的替代方案。
4. 最后结合示例代码和中文注释，把抽象机制落到可观察行为上。

---

## 1. 什么是完美转发？

### 核心答案

完美转发是指模板包装层在转发参数时，尽量保留参数原本的左值或右值属性。


### English explanation

In an English interview, I would answer it like this:

Perfect forwarding means that when forwarding parameters, the template wrapper layer tries to retain the original lvalue or rvalue attributes of the parameters.

### 错误回答示例

- “完美转发就是把参数都 `std::move` 一下”
- “有了右值引用就自动是完美转发”
- “模板里 `T&&` 永远都是右值引用”

### 面试官想听什么

- 你是否知道完美转发依赖转发引用和 `std::forward`
- 你是否理解它解决的是包装层丢失值类别的问题

### 项目里怎么说

我会在工厂函数、通用包装器和模板容器接口里使用完美转发，避免中间层把调用方传入的左值/右值属性破坏掉。

### 深入解释

- 完美转发的关键不是 `T&&` 三个字符，而是“推导 + `std::forward` + 保持值类别”
- 如果包装层总把参数当左值传下去，会错过移动语义；如果总 `std::move`，又可能把调用方左值错误搬走
- 这类机制在 `emplace`、工厂函数和泛型封装中非常常见
- 完美转发本质上是为了让中间层“不篡改调用语义”

### 示例

```cpp
#include <iostream>
#include <utility>

void process(int& x) {
    std::cout << "lvalue: " << x << '\n';
}

void process(int&& x) {
    std::cout << "rvalue: " << x << '\n';
}

template <typename T>
void wrapper(T&& value) {
    process(std::forward<T>(value));
}

int main() {
    int x = 10;
    wrapper(x);
    wrapper(20);
}
```

### 代码讲解

- `template <typename T> void wrapper(T&& value)` 这里的 `T&&` 是转发引用
- `wrapper(x);` 传入左值 `x`
- `wrapper(20);` 传入右值临时量
- `std::forward<T>(value)` 是关键，它会保留调用方原本的值类别
- 这段代码重点看：同一个包装函数既能正确转发左值，也能正确转发右值

---

## 2. `std::move` 和 `std::forward` 的区别是什么？

### 核心答案

- `std::move` 无条件把表达式转成右值语义
- `std::forward` 在模板上下文中按原始值类别转发


### English explanation

In an English interview, I would answer it like this:

- `std::move` unconditionally converts expressions to rvalue semantics
- `std::forward` preserves the original value category in a template forwarding context

### 错误回答示例

- “两者只是名字不同”
- “`forward` 比 `move` 更快”
- “只要想优化性能就加 `move`”

### 面试官想听什么

- 你是否知道 `move` 是显式声明“这个对象可以被搬走”
- 你是否知道 `forward` 的存在是为了模板保真转发

### 项目里怎么说

非模板代码里我基本只会在明确不再使用对象时调用 `std::move`；模板包装层则会谨慎使用 `std::forward`，避免错误地把左值也当成右值转走。

### 深入解释

- `std::move` 更像一个类型转换工具，而不是执行移动的函数
- 真正是否发生移动，要看后续是否匹配到移动构造、移动赋值或右值重载
- `std::forward` 只有在模板参数推导场景下才真正体现价值
- 很多面试官问这一题，是为了看你是否理解值类别传播，而不是背两个 API 定义

### 示例

```cpp
#include <iostream>
#include <string>
#include <utility>

void sink(const std::string&) {
    std::cout << "copy/read path\n";
}

void sink(std::string&&) {
    std::cout << "move path\n";
}

template <typename T>
void relay(T&& value) {
    sink(std::forward<T>(value));
}

int main() {
    std::string name = "cpp";
    sink(std::move(name));  // 明确允许 name 被移动

    std::string other = "interview";
    relay(other);           // 保持左值
    relay(std::string{"tmp"}); // 保持右值
}
```

### 代码讲解

- `std::move(name)` 只是把 `name` 转成右值表达式，表示后续可以走移动路径
- `relay(T&& value)` 中的 `T&&` 是转发引用，只有配合模板参数推导才有保留值类别的意义
- `std::forward<T>(value)` 会根据 `T` 的推导结果决定转发成左值还是右值
- 面试重点是：`move` 表达“我愿意交出资源”，`forward` 表达“我不改变调用者原本语义”

---

## 3. 什么是 SFINAE？

### 核心答案

SFINAE 的意思是模板替换失败不是错误，而是让不合法候选退出重载决议。


### English explanation

In an English interview, I would answer it like this:

SFINAE means that template substitution failure is not a hard error, but removes invalid candidates from overload resolution.

### 错误回答示例

- “SFINAE 就是模板编译报错技巧”
- “它和概念完全一样”
- “现代 C++ 里已经没用了”

### 面试官想听什么

- 你是否知道它是旧式模板约束的核心机制
- 你是否能把它和 `enable_if`、traits、重载控制联系起来

### 项目里怎么说

老代码和基础库中仍会遇到 SFINAE。新代码如果编译器和标准允许，我会更倾向 `if constexpr`、`requires` 和 `concepts`，因为可读性更强。

### 深入解释

- SFINAE 的价值在于“非法模板候选自动退出”，而不是把程序直接编译报死
- 它让模板可以根据类型特征有选择地参与重载
- 历史上大量模板库都依赖 SFINAE，因此理解它对读旧代码很重要
- 现代语言特性在逐步替代它的部分用途，但底层思想仍然一致：对模板施加约束

### 示例

```cpp
#include <iostream>
#include <type_traits>

template <typename T>
typename std::enable_if<std::is_integral<T>::value, void>::type
printType(T) {
    std::cout << "integral\n";
}

template <typename T>
typename std::enable_if<!std::is_integral<T>::value, void>::type
printType(T) {
    std::cout << "non-integral\n";
}
```

### 代码讲解

- `std::enable_if<...>::type` 用来控制这个函数模板是否有效
- 第一组模板只允许整数类型参与重载
- 第二组模板只允许非整数类型参与重载
- 这段代码重点看：不满足条件的模板不会硬报错，而是自动退出候选集合

### 现代 C++ 替代方案

- C++17 中很多“根据类型选择实现”的场景可以改成 `if constexpr`，可读性通常更好
- C++20 中模板接口约束优先考虑 `requires` 和 concepts，把约束直接写在函数声明上
- SFINAE 仍然值得掌握，因为旧代码、标准库实现和复杂检测 idiom 里仍会出现

### 面试追问

- SFINAE 发生在模板替换阶段，普通函数体里的编译错误是否也会被忽略？
- `std::enable_if` 放在返回值、模板参数、函数参数位置各有什么可读性差异？
- concepts 比 SFINAE 更现代，但为什么不是所有模板技巧都能简单替换？

---

## 4. 静态多态和动态多态有什么区别？

### 核心答案

- 动态多态基于虚函数，运行时分发
- 静态多态基于模板或 CRTP，编译期分发


### English explanation

In an English interview, I would answer it like this:

- Dynamic polymorphism is based on virtual functions and dispatched at runtime
- Static polymorphism is based on templates or CRTP and resolved at compile time

### 错误回答示例

- “模板不是多态”
- “动态多态一定更慢所以不用”
- “静态多态能完全替代虚函数”

### 面试官想听什么

- 你是否能根据扩展时机和性能需求选择方案
- 你是否知道运行时扩展和编译期优化是两条不同维度

### 项目里怎么说

如果需要插件式扩展、运行时切换实现，我会优先动态多态；如果能力边界在编译期已知，而且性能敏感，我会更考虑模板和静态多态。

### 深入解释

- 动态多态适合“运行时才知道具体类型”的场景，比如插件系统、策略替换、接口注入
- 静态多态更适合编译期已知类型的高性能抽象，比如数值计算和泛型库
- 动态多态通常伴随虚表和间接调用，静态多态则可能带来代码膨胀
- 工程选择往往不是“谁高级”，而是“扩展时机和性能边界是否匹配”

### 示例

```cpp
#include <iostream>

template <typename T>
class Printer {
public:
    void print() const {
        static_cast<const T*>(this)->printImpl();
    }
};

class MessagePrinter : public Printer<MessagePrinter> {
public:
    void printImpl() const {
        std::cout << "hello\n";
    }
};
```

### 代码讲解

- `Printer<T>` 是基类模板，`T` 表示最终派生类型
- `static_cast<const T*>(this)->printImpl();` 是 CRTP 的核心写法
- 它把接口调用下沉到派生类实现，但在编译期就能确定目标
- 这段代码重点看：没有虚函数，也能实现“统一接口 + 不同实现”

---

## 5. 什么是对象切片？

### 核心答案

派生类对象按值传给基类对象时，只会保留基类部分，派生类部分被切掉，这就是对象切片。


### English explanation

In an English interview, I would answer it like this:

When a derived class object is passed to a base class object by value, only the base-class subobject is copied and the derived-class state is sliced away. This is object slicing.

### 错误回答示例

- “有虚函数就不会切片”
- “切片只是少调一个析构函数”
- “只有显式拷贝才会切片”

### 面试官想听什么

- 你是否知道按值传基类会破坏多态
- 你是否知道多态接口应该用基类引用或指针

### 项目里怎么说

如果接口语义上允许多态，我会显式禁止按值接收基类对象，统一用引用、指针或智能指针，避免切片把真实动态类型信息丢掉。

### 深入解释

- 对象切片本质上是“派生对象被按值转换成基类对象时，只复制基类子对象”
- 一旦切片发生，派生类新增状态和行为信息就丢失了
- 即使基类有虚函数，切成一个独立的基类对象后，多态也无法恢复
- 因此多态接口设计通常都避免按值传递基类

### 示例

```cpp
#include <iostream>

class Base {
public:
    virtual void who() const {
        std::cout << "Base\n";
    }
};

class Derived : public Base {
public:
    void who() const override {
        std::cout << "Derived\n";
    }
};

void print(Base b) {
    b.who();
}

int main() {
    Derived d;
    print(d);
}
```

### 代码讲解

- `void print(Base b)` 按值接收参数，这是切片发生的根源
- `print(d);` 传入 `Derived` 时，会先构造一个独立的 `Base` 对象副本
- 派生类那部分状态和动态类型信息在这里丢失
- 重点看：多态接口一旦按值传基类，就可能破坏多态

---

## 6. 为什么基类析构函数通常要写成虚函数？

### 核心答案

如果对象会通过基类指针删除，就必须让基类析构函数为虚函数，保证派生类析构被正确调用。


### English explanation

In an English interview, I would answer it like this:

If the object will be deleted through the base class pointer, the base class destructor must be a virtual function to ensure that the derived class destructor is called correctly.

### 错误回答示例

- “只要有继承就必须虚析构”
- “虚析构只是为了多态调用更优雅”
- “智能指针会自动解决这个问题，不需要虚析构”

### 面试官想听什么

- 你是否理解删除路径上的动态类型析构需求
- 你是否会区分“作为多态基类”与“仅作实现复用基类”

### 项目里怎么说

只要一个类被设计成多态基类，我会把析构函数设计成虚函数；如果不是多态基类，我不会机械地到处加虚析构，因为那会引入额外的对象模型成本。

### 深入解释

- 只有当对象可能经由基类指针或引用体系被销毁时，虚析构才是刚需
- 虚析构会让删除操作根据动态类型选择正确析构链
- 不是所有基类都必须虚析构，纯粹用于代码复用的非多态基类未必需要
- 面试中关键是能说清“为什么需要”而不是机械背结论

### 示例

```cpp
class Base {
public:
    virtual ~Base() = default;
};

class Derived : public Base {
public:
    ~Derived() override = default;
};
```

### 代码讲解

- `virtual ~Base() = default;` 是关键，表示通过基类销毁对象时要走动态析构链
- `~Derived() override` 明确派生类析构函数也在重写基类虚析构
- 这段代码重点看：多态基类最重要的不是有没有别的虚函数，而是析构路径是否正确

---

## 7. 什么是未定义行为？

### 核心答案

未定义行为表示标准不对程序结果做任何保证，结果可能看似正常，也可能在不同编译器、不同优化级别下完全不同。


### English explanation

In an English interview, I would answer it like this:

Undefined behavior means that the standard does not make any guarantees about program results. The results may appear normal, or they may be completely different under different compilers and different optimization levels.

### 错误回答示例

- “未定义行为就是程序会崩”
- “只要本机能跑就不算问题”
- “编译器会帮你兜底”

### 面试官想听什么

- 你是否理解 UB 会破坏优化前提
- 你是否知道常见 UB 类型，如越界、空指针解引用、访问已释放内存、数据竞争

### 项目里怎么说

面对潜在 UB，我不会用“线上目前没出事”来判断风险，而会尽量通过静态分析、sanitizer、边界检查和资源模型设计把这类问题提前消灭。

### 深入解释

- UB 最危险的地方在于结果不可预测，不仅可能崩溃，也可能悄悄产生错误结果
- 编译器优化常基于“程序没有 UB”这个前提，因此 UB 会让优化结果看起来非常反直觉
- 数据竞争在 C++ 里也是 UB，这一点经常被低估
- 学习 UB 的重点不是记例子，而是养成“不要依赖未被标准保证的行为”的习惯

### 示例

```cpp
int main() {
    int* p = nullptr;
    // int x = *p;
}
```

### 代码讲解

- `int* p = nullptr;` 创建一个空指针
- 注释掉的 `*p` 表示对空指针解引用
- 这正是典型未定义行为例子：代码可能崩，也可能表现得更隐蔽
- 重点看：UB 不是“结果固定错误”，而是“标准不保证任何结果”

---

## 8. C++ 内存模型是什么？

### 核心答案

C++ 内存模型定义了多线程程序中读写可见性、同步关系、数据竞争和重排序边界，是理解原子操作和 lock-free 设计的基础。


### English explanation

In an English interview, I would answer it like this:

The C++ memory model defines read and write visibility, synchronization relationships, data races, and reordering boundaries in multi-threaded programs, and is the basis for understanding atomic operations and lock-free design.

### 错误回答示例

- “内存模型就是堆和栈”
- “只要用了 `atomic` 就不用考虑顺序”
- “内存模型只和操作系统有关”

### 面试官想听什么

- 你是否知道线程间可见性不是天然成立的
- 你是否知道 acquire/release 和 happens-before 这些概念

### 项目里怎么说

业务代码里我通常优先使用锁来换取简单正确；只有在确认热点瓶颈存在时，才会更深入地使用原子和更细的内存序控制。

### 深入解释

- 内存模型研究的是线程间读写是否可见、顺序是否被保证，而不是简单的“内存如何分配”
- 编译器和 CPU 都可能为了性能重排指令，这就是为什么线程同步必须由语言层明确定义
- `happens-before` 是理解线程安全的重要概念，它描述一个操作结果对另一个操作可见的顺序关系
- 不了解内存模型，原子代码很容易“看起来对，实际上错”

### 示例

```cpp
#include <atomic>
#include <thread>

std::atomic<bool> ready{false};
int payload = 0;

void producer() {
    payload = 42;
    ready.store(true, std::memory_order_release);
}

void consumer() {
    while (!ready.load(std::memory_order_acquire)) {
    }
    // acquire 看到 release 后，payload 的写入对当前线程可见
    int value = payload;
    (void)value;
}

int main() {
    std::thread a(producer);
    std::thread b(consumer);
    a.join();
    b.join();
}
```

### 代码讲解

- `payload` 不是原子变量，单独跨线程读写会有数据竞争风险
- `ready.store(..., release)` 把之前的普通写入一起发布出去
- `ready.load(..., acquire)` 看到发布标记后，建立同步关系，从而安全读取 `payload`
- 这个例子说明内存模型的重点是“可见性和顺序”，不是简单背几个枚举值

### 面试追问

- 为什么 `ready` 用 `relaxed` 不足以保护 `payload` 的可见性？
- 什么时候你会放弃手写原子同步，改用 `mutex` 或 `condition_variable`？
- `happens-before` 和“代码顺序看起来在前面”有什么区别？

---

## 9. `memory_order_relaxed/acquire/release/seq_cst` 应该怎么理解？

### 核心答案

- `relaxed` 只保证原子性
- `release` 发布之前写入
- `acquire` 获取发布侧写入
- `seq_cst` 提供更强的全局一致观察顺序


### English explanation

In an English interview, I would answer it like this:

- `relaxed` only guarantees atomicity
- `release` publishes writes that happened before it
- `acquire` observes writes published by a matching release operation
- `seq_cst` provides the strongest default ordering: a single global order for sequentially consistent atomic operations

### 错误回答示例

- “都用 `relaxed` 性能最好，所以最好”
- “`seq_cst` 一定最慢所以不能用”
- “有了 acquire/release 就不用再想数据流”

### 面试官想听什么

- 你是否知道内存序的核心是可见性和重排序约束
- 你是否会先追求正确性，再追求局部优化

### 项目里怎么说

除非我在写并发基础设施，否则我不会轻易下沉到复杂内存序调优。业务场景里，简单、可证明正确的同步方式通常比“理论上更快”的技巧更可靠。

### 深入解释

- `relaxed` 只保证单个原子操作本身不被撕裂，不保证跨线程观察顺序
- `release` 和 `acquire` 通常成对使用，用于建立发布-获取同步关系
- `seq_cst` 语义最强，也最容易解释，很多场景先从它开始是合理的
- 内存序越弱，推理越困难，因此“更快”并不自动意味着“更值得用”

### 示例

```cpp
#include <atomic>

std::atomic<bool> ready = false;
int data = 0;

void producer() {
    data = 42;
    ready.store(true, std::memory_order_release);
}

void consumer() {
    if (ready.load(std::memory_order_acquire)) {
        // 此处可见 producer 对 data 的写入
    }
}
```

### 代码讲解

- `ready.store(true, std::memory_order_release);` 发布写入结果
- `ready.load(std::memory_order_acquire)` 获取这次发布
- `data = 42;` 虽然不是原子变量，但在这组 release/acquire 同步关系下，消费者可见
- 这段代码重点看：内存序不是单看某一行，而是成对建立可见性关系

---

## 10. 什么是 type traits？

### 核心答案

type traits 是一组编译期工具，用来判断、查询或变换类型。


### English explanation

In an English interview, I would answer it like this:

Type traits are a set of compile-time tools used to determine, query, or transform types.

### 错误回答示例

- “traits 就是反射”
- “只有模板元编程才会用到”
- “现代 C++ 里都被 concepts 替代了”

### 面试官想听什么

- 你是否知道常见 traits，如 `is_integral`、`is_same`、`remove_reference`
- 你是否知道 traits 是很多泛型约束和实现分支的基础

### 项目里怎么说

在基础组件或通用模板工具中，我会用 traits 控制模板行为；在业务代码中则会克制使用，避免把简单逻辑写成过度技巧化的模板元编程。

### 深入解释

- traits 常见能力包括判断类型性质、移除修饰、生成关联类型
- 很多看似高级的模板技巧，其实底层都在依赖 traits 提供的类型信息
- 它们本质是编译期工具，不会产生运行时反射机制
- 面试中能把 traits 和泛型约束联系起来，通常就已经说明理解比较扎实

### 示例

```cpp
#include <type_traits>

static_assert(std::is_integral_v<int>);
static_assert(std::is_pointer_v<int*>);
static_assert(std::is_same_v<std::remove_reference_t<int&>, int>);
```

### 代码讲解

- `std::is_integral_v<int>` 判断类型是否为整型
- `std::is_pointer_v<int*>` 判断类型是否为指针
- `std::remove_reference_t<int&>` 去掉引用修饰，再与 `int` 比较
- 这段代码重点看：traits 是编译期类型查询和变换工具

---

## 11. `weak_ptr` 解决了什么问题？

### 核心答案

`weak_ptr` 用来观察 `shared_ptr` 管理的对象，但不参与拥有，主要用于打破循环引用。


### English explanation

In an English interview, I would answer it like this:

`weak_ptr` is used to observe objects managed by `shared_ptr`, but does not participate in ownership. It is mainly used to break circular references.

### 错误回答示例

- “`weak_ptr` 就是不安全的智能指针”
- “只要有 `shared_ptr` 就不需要 `weak_ptr`”
- “`weak_ptr` 能直接当普通指针用”

### 面试官想听什么

- 你是否理解引用计数环为什么会泄漏
- 你是否知道 `weak_ptr::lock()` 的用途

### 项目里怎么说

在双向关系、缓存和观察者模式里，我会显式把一侧定义成非拥有关系，用 `weak_ptr` 表达“知道它存在，但不负责延长生命周期”。

### 深入解释

- `shared_ptr` 循环引用问题的根源是引用计数无法降到 0
- `weak_ptr` 不增加强引用计数，因此能打破这种环
- 使用 `weak_ptr` 时通常要先 `lock()` 得到临时 `shared_ptr`，再安全访问对象
- 这一题面试官真正想听的是“你是否会区分拥有关系和观察关系”

### 示例

```cpp
#include <memory>

struct Node {
    std::shared_ptr<Node> next;
    std::weak_ptr<Node> prev;
};
```

### 代码讲解

- `next` 是拥有关系，会增加强引用计数
- `prev` 是观察关系，不会增加强引用计数
- 这正是双向关系中避免循环引用的典型设计
- 重点看：`weak_ptr` 的语义不是“弱一点的 shared_ptr”，而是“不拥有”

---

## 12. 为什么说 `shared_ptr` 不是“更高级的裸指针”？

### 核心答案

`shared_ptr` 的核心不是自动 delete，而是共享所有权语义。它有成本，也会改变对象生命周期模型。


### English explanation

In an English interview, I would answer it like this:

The core of `shared_ptr` is shared ownership, not just automatic deletion. It has runtime cost and changes the object lifetime model.

### 错误回答示例

- “为了安全，所有指针都换成 `shared_ptr`”
- “`shared_ptr` 没有坏处，就是更方便”
- “只要引用计数归零就说明设计没问题”

### 面试官想听什么

- 你是否理解 `shared_ptr` 的引用计数、原子成本和循环引用风险
- 你是否知道所有权建模比“自动释放”更重要

### 项目里怎么说

我会把 `shared_ptr` 当成一种强语义工具，而不是默认容器。只有在对象确实被多个模块共同拥有，并且释放时机无法由单一拥有者决定时，我才会使用它。

### 深入解释

- `shared_ptr` 解决的是共享所有权，不是“普通指针自动释放”
- 一旦默认到处使用 `shared_ptr`，对象生命周期边界会变得模糊
- 这会让释放时机难以推导，也增加调试复杂度
- 所以现代 C++ 更强调先用 `unique_ptr` 建模，再看是否真的需要共享

### 示例

```cpp
#include <iostream>
#include <memory>
#include <string>
#include <vector>

struct Document {
    std::string title;
};

void readOnly(const Document* doc) {
    if (doc) {
        std::cout << doc->title << '\n';
    }
}

int main() {
    auto owner = std::make_unique<Document>(Document{"design"});
    readOnly(owner.get());

    std::vector<std::shared_ptr<Document>> openTabs;
    auto shared = std::make_shared<Document>(Document{"shared"});
    openTabs.push_back(shared);
}
```

### 代码讲解

- `unique_ptr` 表达单一拥有者，是默认更清晰的所有权模型
- `readOnly(owner.get())` 只是临时观察，不应该为了“方便”把接口改成 `shared_ptr`
- `shared_ptr` 适合 `openTabs` 这类确实存在多方共同延长生命周期的场景
- 面试重点是：智能指针不是按“高级程度”选择，而是按所有权语义选择

---

## 13. 什么是 copy elision？RVO / NRVO 是什么？

### 核心答案

copy elision 是编译器省略拷贝或移动，直接在目标位置构造对象。RVO 和 NRVO 是常见返回值优化形式。


### English explanation

In an English interview, I would answer it like this:

Copy elision means that the compiler omits copying or moving and directly constructs the object at the target location. RVO and NRVO are common forms of return value optimization.

### 错误回答示例

- “按值返回对象一定很慢”
- “有移动构造之后就不需要返回值优化了”
- “RVO 只是编译器碰巧帮你快一点”

### 面试官想听什么

- 你是否知道现代 C++ 中按值返回对象通常是合理的
- 你是否知道 copy elision 让值语义设计更可行

### 项目里怎么说

我不会为了避免“想象中的拷贝”而到处返回裸指针或输出参数。只要对象语义清晰，按值返回通常是更自然也更现代的接口形式。

### 深入解释

- copy elision 让“返回对象”不一定意味着真的发生拷贝或移动
- RVO 指直接在调用方目标位置构造返回值，NRVO 是对具名局部变量的类似优化
- 这也是现代 C++ 倾向值语义接口的重要基础
- 因此很多老式“输出参数优先”的习惯在今天未必仍是最优设计

### 示例

```cpp
#include <string>

std::string makeText() {
    return "hello";
}

int main() {
    std::string s = makeText();
}
```

### 代码讲解

- `return "hello";` 返回一个按值构造的 `std::string`
- `std::string s = makeText();` 在现代编译器下常能直接构造到目标位置
- 重点看：按值返回对象在现代 C++ 里通常是自然且高效的

---

## 14. 模板元编程和 `if constexpr` 的关系是什么？

### 核心答案

`if constexpr` 让很多编译期分支逻辑比传统模板特化和 SFINAE 更直观、可读。


### English explanation

In an English interview, I would answer it like this:

`if constexpr` makes a lot of compile-time branching logic more intuitive and readable than traditional template specializations and SFINAE.

### 错误回答示例

- “有了 `if constexpr`，模板特化就没用了”
- “`if constexpr` 和运行时 if 一样”
- “编译期分支就是为了炫技”

### 面试官想听什么

- 你是否知道 `if constexpr` 会在编译期丢弃无效分支
- 你是否理解现代 C++ 正在把模板写法从技巧化转向可读化

### 项目里怎么说

如果只是根据类型差异做少量行为分支，我会优先 `if constexpr`；只有在接口选择或类型关系本身需要通过模板特化表达时，才会下沉到更复杂的模板技巧。

### 深入解释

- `if constexpr` 在编译期丢弃不成立分支，因此可以安全写出某些只对特定类型合法的代码
- 它显著降低了模板分支逻辑的阅读门槛
- 但它不是模板特化的完全替代品，某些类型级接口选择仍需特化
- 现代 C++ 的趋势是让泛型代码更像“正常代码”，而不是满是技巧性模板语法

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

### 代码讲解

- `if constexpr (std::is_integral_v<T>)` 是编译期分支
- 当 `T` 是整型时，只保留第一条分支
- 否则编译器会丢弃不成立的分支
- 重点看：`if constexpr` 不是运行时 if，而是编译期按类型裁剪代码

---

## 15. 如何设计一个现代 C++ 风格的类？

### 核心答案

现代 C++ 风格的类通常强调：

- 所有权清晰
- 生命周期明确
- Rule of Zero 优先
- 接口简洁
- 异常安全可推导


### English explanation

In an English interview, I would answer it like this:

Modern C++ style classes usually emphasize:

- Clear ownership
- Clear lifetime
- Rule of Zero priority
- Simple interface
- Exception-safe and easy to reason about

### 错误回答示例

- “把所有成员 private、所有函数 inline 就叫现代 C++”
- “只要用了智能指针就是现代设计”
- “设计类就是先写一堆继承层级”

### 面试官想听什么

- 你是否把语言特性和工程约束结合起来
- 你是否理解现代风格首先是建模清晰，而不是语法花样

### 项目里怎么说

我设计类时会先问几个问题：谁拥有资源、能不能拷贝、能不能移动、是否需要多态、异常发生后状态要保证到什么程度。很多设计问题本质上都是这些问题的外化。

### 深入解释

- 现代 C++ 风格首先是建模清晰，而不是特性堆砌
- 好的类设计通常能从接口上直接看出所有权和生命周期约束
- 如果一个类必须依赖复杂约定才能安全使用，往往说明接口还不够好
- 设计类时从资源、不变量和错误处理出发，通常比从继承层级出发更稳

### 示例

```cpp
#include <string>
#include <utility>
#include <vector>

class SensorBatch {
public:
    explicit SensorBatch(std::string source) : source_(std::move(source)) {}

    void add(double value) {
        values_.push_back(value);
    }

    const std::string& source() const noexcept {
        return source_;
    }

    const std::vector<double>& values() const noexcept {
        return values_;
    }

private:
    std::string source_;
    std::vector<double> values_;
};
```

### 代码讲解

- 类只持有标准库资源，因此不需要手写析构、拷贝或移动，符合 Rule of Zero
- 构造函数用 `explicit` 避免从字符串隐式构造业务对象
- `source()` 和 `values()` 返回只读引用，表达外部不能破坏内部不变量
- `noexcept` 用在简单访问器上，让接口的失败边界更清楚

### 高频用法

- 值语义对象优先使用标准库成员，让编译器生成特殊成员函数
- 有唯一资源时用 `unique_ptr` 或专门 RAII 类型表达所有权
- 需要多态时通过小而稳定的抽象接口暴露能力，不把内部状态泄露给调用方

---

## 16. 单例在现代 C++ 中怎么写更合理？

### 核心答案

如果必须使用单例，函数内局部静态对象是现代 C++ 中最常见、最简单且线程安全的实现方式。


### English explanation

In an English interview, I would answer it like this:

If you must use a singleton, local static objects within a function are the most common, simplest, and thread-safe implementation in modern C++.

### 错误回答示例

- “单例是最佳实践，所有全局对象都该这么写”
- “自己加双重检查锁最专业”
- “局部静态只是语法糖，不可靠”

### 面试官想听什么

- 你是否知道 C++11 起局部静态初始化线程安全
- 你是否也能主动说出单例的缺点

### 项目里怎么说

如果能通过依赖注入、显式对象生命周期管理解决问题，我不会优先上单例；只有在配置中心、日志设施这类极少数全局资源场景，才会谨慎使用。

### 深入解释

- 函数局部静态单例的优势是实现简单，且自 C++11 起初始化线程安全
- 但单例天然带来全局状态、隐藏依赖和测试困难
- 因此面试中更好的回答通常不是“我会写单例”，而是“我知道怎么写，也知道什么时候不该用”
- 高质量回答应同时覆盖实现方式和架构代价

### 示例

```cpp
class Config {
public:
    static Config& instance() {
        static Config cfg;
        return cfg;
    }

    Config(const Config&) = delete;
    Config& operator=(const Config&) = delete;

private:
    Config() = default;
};
```

### 代码讲解

- `static Config cfg;` 是函数内局部静态对象
- `instance()` 每次返回同一个全局唯一实例引用
- 拷贝构造和赋值被 `delete`，防止复制出新的实例
- 这段代码重点看：单例关键不是语法花样，而是“唯一实例 + 受控访问入口”

---

## 17. ODR 违反有哪些典型场景？

### 核心答案

ODR 要求同一个实体在整个程序中只能有一个一致的定义；违反时轻则链接报重复定义，重则不同翻译单元看到不同定义而产生未定义行为。

### English explanation

In an English interview, I would say: the One Definition Rule keeps definitions unique and consistent across translation units. Some violations are caught by the linker, but inconsistent class or inline definitions can become much more subtle.

### 错误回答示例

- “ODR 只是链接器错误，不影响运行时行为”
- “头文件里随便定义函数也没问题”
- “只要每个 `.cpp` 都能单独编译就没有 ODR 风险”

### 面试官想听什么

- 你是否理解 C++ 是多翻译单元模型
- 你是否知道头文件定义、宏条件编译、inline 变量/函数和模板都和 ODR 有关
- 你是否能区分“重复定义被链接器抓住”和“不同 TU 定义不一致”的隐蔽风险

### 项目里怎么说

我会把普通函数定义放到 `.cpp`，头文件只放声明；如果必须在头文件定义函数或变量，会明确使用 `inline`、模板或 `constexpr/inline variable` 这些符合 ODR 的形式。大型项目里还要避免不同编译选项和宏让同一个头文件在不同 TU 中展开成不同结构。

### 深入解释

- 头文件被多个 `.cpp` 文本包含，非 `inline` 的普通函数定义会在多个目标文件里各产生一个定义
- 类定义、模板定义通常放头文件，但要求每个翻译单元看到的定义一致
- C++17 的 `inline` 变量解决了头文件常量或全局对象定义的部分 ODR 问题
- ODR 问题经常不是“语法不会写”，而是工程边界、构建选项和宏污染导致的二进制不一致

### 示例

```cpp
// header.hpp
#pragma once

inline int answer() {
    return 42;
}

// C++17: header-only 全局常量可用 inline variable
inline constexpr int max_retry = 3;
```

### 代码讲解

- `inline int answer()` 允许函数定义出现在多个翻译单元中，并在链接时合并为同一实体
- `inline constexpr int max_retry` 适合放在头文件里作为全局常量定义
- 如果去掉 `inline`，普通函数定义被多个 `.cpp` 包含时通常会重复定义
- 真正危险的是不同 TU 通过宏看到不同的类布局，这可能绕过链接错误并变成运行期问题

### 面试追问

- 模板为什么通常可以定义在头文件里？
- `static` 放在头文件函数上能避免链接错误，但语义上有什么代价？
- C++17 `inline variable` 解决了什么历史痛点？

---

## 18. ADL 是什么，为什么会影响重载查找？

### 核心答案

ADL 会根据实参类型所在的关联命名空间一起查找函数；它让非成员运算符和定制点更自然，但也可能把意料之外的重载候选带进来。

### English explanation

ADL, or argument-dependent lookup, searches namespaces associated with the argument types. It is useful for operators and customization functions, but it can also make overload resolution less obvious.

### 错误回答示例

- “函数查找只看当前作用域和 using”
- “ADL 只是运算符重载的小细节”
- “遇到找不到函数就多写几个 using namespace”

### 面试官想听什么

- 你是否知道非成员函数为什么能和类型放在同一命名空间里被找到
- 你是否理解 `swap(x, y)`、运算符重载和定制点背后的查找机制
- 你是否知道 ADL 可能引入额外候选，导致重载选择变复杂

### 项目里怎么说

我会把和类型强相关的非成员函数放在同一命名空间里，让 ADL 自然工作；但公共头文件里会避免滥用 `using namespace`，也不会依赖过于隐蔽的 ADL 魔法来组织核心业务逻辑。

### 深入解释

- 普通非限定查找会看当前作用域，ADL 会额外看实参类型关联的命名空间
- 这就是 `operator<<`、`operator==`、自定义 `swap` 等函数通常和类型定义放在一起的原因
- 现代 C++ 的一些定制点对象会更谨慎地控制 ADL，以避免全局函数污染
- ADL 问题排查时，要同时看调用点作用域、参数类型、命名空间和候选函数签名

### 示例

```cpp
#include <iostream>

namespace app {
struct X {};

void print(X) {
    std::cout << "app::X\n";
}
}

int main() {
    app::X x;
    print(x); // ADL 找到 app::print
}
```

### 代码讲解

- 调用点没有写 `app::print(x)`，但参数类型是 `app::X`
- ADL 会把 `app` 作为关联命名空间纳入查找
- 这让类型相关的非成员函数不必全部塞进类成员里
- 但如果关联命名空间里有多个候选，重载决议也可能变得难读

### 面试追问

- 为什么自定义 `swap` 通常写成 `using std::swap; swap(a, b);`？
- ADL 和成员函数查找有什么区别？
- 为什么公共库设计中要谨慎定义过宽泛的模板函数？

---

## 19. strict aliasing 是什么？

### 核心答案

strict aliasing 允许优化器假设无关类型的指针通常不会指向同一个对象；违反这些访问规则属于未定义行为，可能在高优化级别下产生反直觉结果。

### English explanation

Strict aliasing rules let the optimizer assume that pointers of unrelated types do not alias the same object. Breaking those rules can be undefined behavior and may only fail under optimization.

### 错误回答示例

- “只要地址一样，换成任何指针类型读都可以”
- “`reinterpret_cast` 能让所有类型转换都合法”
- “低优化级别能跑就说明没有问题”

### 面试官想听什么

- 你是否知道类型系统会影响优化器的别名假设
- 你是否知道 `char`、`unsigned char`、`std::byte` 可用于查看对象字节表示
- 你是否能说出安全替代方式，如 `std::memcpy` 或 C++20 `std::bit_cast`

### 项目里怎么说

如果需要做序列化、网络协议或二进制解析，我会避免用随意的 `reinterpret_cast` 直接把字节流当成结构体读写。更稳的方式是用 `std::byte` 缓冲区、`std::memcpy`、明确大小端转换和对齐检查。

### 深入解释

- strict aliasing 的动机是让编译器能假设 `int*` 和不相关的 `float*` 不会修改同一个对象
- 这种假设可以带来优化，但前提是程序不违反对象访问规则
- `reinterpret_cast` 只改变表达式类型，不自动创建目标类型对象，也不保证别名访问合法
- C++20 的 `std::bit_cast` 适合在满足大小和可平凡拷贝条件时做值级位拷贝

### 示例

```cpp
#include <bit>
#include <cstdint>
#include <iostream>

int main() {
    float f = 1.0f;
    std::uint32_t bits = std::bit_cast<std::uint32_t>(f);
    std::cout << bits << '\n';
}
```

### 代码讲解

- `std::bit_cast` 不是通过错误类型指针去访问原对象
- 它要求源类型和目标类型大小相同，并且都是可平凡拷贝类型
- 这适合查看浮点数的位模式、协议字段等低层需求
- 面试重点是：底层代码也要尊重对象生命周期、对齐和别名规则

### 面试追问

- `reinterpret_cast<T*>` 和“目标类型对象已经存在”是什么关系？
- 为什么 `std::memcpy` 经常是低层类型转换里更安全的选择？
- strict aliasing bug 为什么常常只在 `-O2/-O3` 出现？

---

## 20. object lifetime、placement new、`std::launder` 怎么理解？

### 核心答案

原始存储存在不等于对象生命周期已经开始；placement new 可以在已有存储上构造对象，`std::launder` 用于某些复用存储后需要重新取得有效指针的细节场景。

### English explanation

Object lifetime is separate from raw storage. Placement new starts an object's lifetime in existing storage, and `std::launder` handles subtle cases where a pointer must be refreshed after storage reuse.

### 错误回答示例

- “有一块内存就等于里面已经有对象”
- “placement new 会自动释放旧对象”
- “`std::launder` 是普通业务代码常用工具”

### 面试官想听什么

- 你是否能区分 storage、object、lifetime 三个概念
- 你是否知道手动生命周期管理必须显式析构
- 你是否知道这类技巧主要出现在容器、内存池、variant 等基础设施中

### 项目里怎么说

业务代码里我通常不会直接使用 placement new，而是交给标准容器、智能指针或 RAII 类型。只有在实现容器、小对象优化、内存池或类型擦除存储时，才会认真处理对齐、构造、析构和异常安全。

### 深入解释

- `operator new` 或字节数组只提供原始存储，不自动开始任意类型对象的生命周期
- placement new 在指定地址构造对象，但对象销毁要显式调用析构函数
- 如果在同一存储位置构造新对象，旧指针在某些情况下不能直接当作新对象指针继续使用
- `std::launder` 是为了配合标准对象模型和优化规则，不是日常替代智能指针的工具

### 示例

```cpp
#include <new>
#include <string>
#include <type_traits>

int main() {
    using Storage = std::aligned_storage_t<sizeof(std::string), alignof(std::string)>;
    Storage storage;

    auto* text = new (&storage) std::string("cpp");
    text->append("20");
    text->~basic_string();
}
```

### 代码讲解

- `aligned_storage_t` 提供大小和对齐都足够的原始存储
- `new (&storage) std::string("cpp")` 在这块存储上开始 `std::string` 的生命周期
- `text->~basic_string()` 手动结束对象生命周期，否则资源不会按预期释放
- 真正项目中还要处理构造失败、重复析构和异常安全问题

### 面试追问

- placement new 和普通 `new` 最大区别是什么？
- 为什么 `malloc` 出来的内存里不自动有 C++ 对象？
- `std::variant` 或 `std::optional` 为什么需要管理对象生命周期？

---

## 21. alignment 和 padding 是什么？

### 核心答案

alignment 是对象地址必须满足的对齐要求，padding 是编译器为了满足对齐和布局规则插入的空洞；因此结构体大小可能大于成员大小之和。

### English explanation

Alignment defines valid address boundaries for objects, and padding is extra space inserted by the compiler to satisfy alignment and layout rules.

### 错误回答示例

- “结构体大小一定等于成员大小相加”
- “padding 是编译器浪费空间，可以随便关掉”
- “对齐只影响性能，不影响正确性”

### 面试官想听什么

- 你是否理解对象布局和 CPU 访问约束
- 你是否知道成员顺序会影响结构体大小
- 你是否能区分内存优化、二进制协议和 ABI 稳定性里的布局问题

### 项目里怎么说

我不会随便用 `#pragma pack` 追求表面省空间；如果结构体跨网络、磁盘或动态库边界，我会明确字段大小、大小端和版本，而不是直接依赖编译器内存布局。

### 深入解释

- 每种类型都有 `alignof(T)`，对象地址必须满足对应对齐
- 编译器会在成员之间或结构体尾部插入 padding，保证数组中每个元素都正确对齐
- 调整成员顺序有时能减少 padding，但不能牺牲接口可读性和 ABI 约束
- packed 结构可能导致未对齐访问，某些平台上不仅慢，甚至可能出错

### 示例

```cpp
#include <iostream>

struct A {
    char c;
    int i;
};

struct B {
    int i;
    char c;
};

int main() {
    std::cout << sizeof(A) << ' ' << sizeof(B) << ' ' << alignof(A) << '\n';
}
```

### 代码讲解

- `A` 中 `char` 后面通常会插入 padding，让 `int` 满足对齐
- `B` 可能减少成员之间的 padding，但尾部仍可能补齐到整体对齐
- `sizeof` 和 `alignof` 是观察对象布局的基本工具
- 面试回答要强调：布局是语言规则、平台 ABI 和编译器实现共同决定的

---

## 22. empty base optimization 是什么？

### 核心答案

EBO 允许空基类子对象不占额外存储；标准库常用它优化分配器、比较器、deleter 和策略类包装的对象大小。

### English explanation

Empty base optimization allows an empty base subobject to take no additional storage. It is commonly used for allocators, deleters, comparators, and policy classes.

### 错误回答示例

- “空类大小就是 0”
- “EBO 只是编译器小优化，不影响库设计”
- “继承空类一定都能省空间”

### 面试官想听什么

- 你是否知道普通空对象大小至少为 1，以保证不同对象地址不同
- 你是否知道空基类在特定条件下可以被优化掉
- 你是否能把 EBO 和 `unique_ptr` deleter、allocator、policy class 联系起来

### 项目里怎么说

业务代码一般不会主动为了 EBO 设计继承层级，但在写基础库、RAII 包装、策略类或轻量函数对象时，我会注意空状态对象的存储成本，优先使用标准库已经封装好的压缩技巧。

### 深入解释

- C++ 要求完整对象通常有唯一地址，因此空类对象大小至少为 1
- 空基类子对象不一定需要独立占用空间，这就是 EBO 的空间来源
- C++20 `[[no_unique_address]]` 把类似优化扩展到空成员场景
- EBO 是“零状态策略对象”能低成本组合的原因之一

### 示例

```cpp
#include <iostream>

struct EmptyPolicy {};

struct AsMember {
    EmptyPolicy policy;
    int value;
};

struct AsBase : EmptyPolicy {
    int value;
};

int main() {
    std::cout << sizeof(AsMember) << ' ' << sizeof(AsBase) << '\n';
}
```

### 代码讲解

- `AsMember` 中空成员通常仍要有地址，因此可能占空间
- `AsBase` 让空类型成为基类，编译器有机会应用 EBO
- 实际大小取决于 ABI 和实现，但这个例子展示了优化方向
- 现代代码中也可以了解 `[[no_unique_address]]` 对空成员的价值

---

## 23. small string optimization 是什么？

### 核心答案

SSO 让短字符串直接存放在 `std::string` 对象内部，避免常见短文本场景的堆分配；具体阈值是实现细节，不能写业务逻辑依赖它。

### English explanation

Small string optimization stores short strings inside the string object itself, avoiding heap allocation for many common short strings. The threshold is implementation-specific.

### 错误回答示例

- “SSO 是标准保证的固定 15 个字符”
- “有 SSO，所以字符串传参怎么写都无所谓”
- “SSO 能完全消除字符串性能问题”

### 面试官想听什么

- 你是否知道 SSO 是性能优化，不是可移植语义保证
- 你是否能说明短字符串频繁构造为什么可能更便宜
- 你是否知道 `string_view` 解决的是非拥有视图问题，不等同于 SSO

### 项目里怎么说

我会把 SSO 当成实现层面的性能背景，而不是接口设计依据。接口上如果只读、不需要拥有，我会考虑 `std::string_view`；如果要保存内容，仍然用 `std::string` 明确拥有关系。

### 深入解释

- `std::string` 对象内部通常有一小块缓冲区，可直接容纳短文本
- 字符串超过阈值后仍会退回堆分配
- SSO 让按值返回小字符串、临时拼接短文本在很多实现中更便宜
- 但阈值、布局和是否启用都是实现细节，不能写 `sizeof(std::string)` 相关假设

### 示例

```cpp
#include <iostream>
#include <string>
#include <string_view>

void logName(std::string_view name) {
    std::cout << name << '\n';
}

int main() {
    std::string s = "imu";
    logName(s);
    logName("lidar");
}
```

### 代码讲解

- `std::string s = "imu"` 在许多实现里可受益于 SSO，但代码不依赖具体阈值
- `logName(std::string_view)` 表示只读观察，不拥有字符串
- `string_view` 可以接收 `std::string` 和字符串字面量，避免不必要拷贝
- 面试中要区分：SSO 是 `string` 实现优化，`string_view` 是接口语义工具

---

## 24. allocator 的基本模型是什么？

### 核心答案

allocator 抽象容器获取原始存储的方式；分配内存、构造对象、销毁对象和释放内存是相关但不同的步骤。

### English explanation

Allocators abstract how containers obtain raw storage. Allocation, construction, destruction, and deallocation are separate responsibilities.

### 错误回答示例

- “allocator 就是 `new/delete` 的别名”
- “容器只要有内存就等于对象已经构造好了”
- “业务代码应该频繁手写 allocator 才高级”

### 面试官想听什么

- 你是否知道 allocator 主要服务于标准容器和基础设施
- 你是否能区分 raw storage 与 object lifetime
- 你是否知道现代代码通常通过 `allocator_traits` 与 allocator 交互

### 项目里怎么说

普通业务代码我很少手写 allocator；如果遇到大量短生命周期对象、固定帧内批量分配或低延迟组件，我会先考虑 `std::pmr` 或成熟内存池，再决定是否实现自定义 allocator。

### 深入解释

- `allocate` 只获得未构造的原始存储
- `construct` 才在存储上开始对象生命周期，`destroy` 结束生命周期
- `deallocate` 只释放存储，不能替代析构
- allocator 设计复杂的原因在于它和容器传播、异常安全、对象生命周期都有关

### 示例

```cpp
#include <memory>

int main() {
    std::allocator<int> alloc;
    int* p = alloc.allocate(1);

    std::allocator_traits<std::allocator<int>>::construct(alloc, p, 42);
    std::allocator_traits<std::allocator<int>>::destroy(alloc, p);

    alloc.deallocate(p, 1);
}
```

### 代码讲解

- `allocate(1)` 得到能放一个 `int` 的原始存储
- `construct` 在该位置构造值为 42 的 `int`
- `destroy` 结束对象生命周期
- `deallocate` 释放原始存储，顺序不能颠倒

---

## 25. type erasure 怎么设计？

### 核心答案

type erasure 隐藏具体类型，只暴露统一运行时接口；它用灵活性换取间接调用、对象管理和可能的动态分配成本。

### English explanation

Type erasure hides concrete types behind a uniform runtime interface. It trades compile-time type knowledge for flexibility and usually adds some runtime cost.

### 错误回答示例

- “type erasure 就是虚函数，没别的形式”
- “`std::function` 没有成本，可以到处替代模板”
- “类型擦除和模板是同一个东西”

### 面试官想听什么

- 你是否知道 `std::function`、`std::any`、迭代器包装都体现了类型擦除思想
- 你是否能说明它和模板静态多态、虚函数动态多态的取舍
- 你是否知道小对象优化、拷贝语义、生命周期管理会影响实现

### 项目里怎么说

当调用方不需要知道具体类型，而且运行时组合能力比极致性能更重要时，我会考虑 type erasure，比如任务队列里的 `std::function<void()>`。如果类型集合在编译期固定且性能敏感，模板或 `std::variant` 可能更合适。

### 深入解释

- 模板保留具体类型，编译期生成不同实现；type erasure 把具体类型封装到统一对象后面
- 典型实现可以用虚基类 + 持有模型，也可以用函数指针表和局部缓冲优化
- `std::function` 擦除了 callable 的具体类型，但仍保留调用签名
- 设计 type erasure 时要先决定是否可拷贝、是否拥有对象、是否允许空状态

### 示例

```cpp
#include <functional>
#include <iostream>
#include <vector>

int main() {
    std::vector<std::function<void()>> tasks;
    tasks.emplace_back([] { std::cout << "load\n"; });
    tasks.emplace_back([] { std::cout << "process\n"; });

    for (auto& task : tasks) {
        task();
    }
}
```

### 代码讲解

- 两个 lambda 的闭包类型不同，但都能放进 `std::function<void()>`
- `std::function` 擦除了具体 callable 类型，只暴露 `void()` 调用接口
- 代价可能包括间接调用和分配，具体取决于实现和 callable 大小
- 面试回答要说清：它解决的是运行时统一管理异构对象的问题

---

## 26. CRTP 的优缺点和边界是什么？

### 核心答案

CRTP 用“基类模板 + 派生类作为模板参数”实现静态多态；优点是编译期分发和接口复用，缺点是类型耦合强、错误信息复杂、不能替代运行时多态。

### English explanation

CRTP implements static polymorphism by passing the derived type to a base template. It can avoid virtual dispatch, but it increases coupling and does not replace runtime polymorphism.

### 错误回答示例

- “CRTP 就是更快的虚函数，应该总是用”
- “CRTP 能在运行时切换实现”
- “只要用了模板继承就是 CRTP”

### 面试官想听什么

- 你是否知道 CRTP 是编译期技术
- 你是否能说明它适合接口复用、mixin、静态多态和返回派生类型接口
- 你是否能讲出边界：类型必须编译期已知，错误信息和编译依赖更重

### 项目里怎么说

我会在基础库、数值类型、mixin 能力注入这类场景考虑 CRTP；如果需求是插件、配置驱动、运行时替换实现，我会选择虚函数接口或类型擦除，而不是硬套 CRTP。

### 深入解释

- CRTP 基类通过 `static_cast<Derived*>(this)` 调用派生类实现
- 因为目标类型编译期已知，编译器更容易内联和优化
- 它要求派生类遵守隐式接口，C++20 concepts 可以帮助把要求显式化
- CRTP 的代价是模板实例化膨胀、错误信息复杂和接口耦合

### 示例

```cpp
#include <iostream>

template <typename Derived>
struct Printable {
    void print() const {
        static_cast<const Derived*>(this)->printImpl();
    }
};

struct Sensor : Printable<Sensor> {
    void printImpl() const {
        std::cout << "sensor\n";
    }
};

int main() {
    Sensor{}.print();
}
```

### 代码讲解

- `Printable<Sensor>` 在编译期知道最终派生类型是 `Sensor`
- `static_cast<const Derived*>(this)->printImpl()` 是 CRTP 的核心调用
- 没有虚表和虚调用，但也没有运行时替换能力
- 如果 `Sensor` 没有 `printImpl`，错误会在模板实例化阶段暴露

---

## 27. concepts（C++20）相比 SFINAE 的工程价值是什么？

### 核心答案

concepts 把模板约束直接写在接口上，让泛型代码的要求、错误信息和重载选择更清楚；它改善的是可读性和可诊断性，不是让模板设计自动变简单。

### English explanation

Concepts express template requirements directly in the interface. Compared with many SFINAE patterns, they make constraints and diagnostics clearer, but they do not remove the need for good generic design.

### 错误回答示例

- “concepts 只是 SFINAE 的语法糖”
- “用了 concepts 就不需要理解 traits 和 overload resolution”
- “concepts 会让模板运行更快”

### 面试官想听什么

- 你是否知道 concepts 约束的是模板可接受的类型集合
- 你是否能说明它比 `enable_if` 更靠近接口层
- 你是否理解 concepts 仍然需要设计清晰的语义要求，而不是把任意表达式检查堆上去

### 项目里怎么说

如果项目可以使用 C++20，我会优先用 concepts 描述公共模板接口约束，比如“必须是 range”“必须可比较”“必须可哈希”。这能让调用错误更早、更清楚地暴露，也让代码评审更容易看懂模板想接受什么。

### 深入解释

- SFINAE 常把约束藏在返回类型、默认模板参数或检测 idiom 中
- concepts 把约束提升为接口的一部分，读声明就能看到要求
- concepts 参与重载排序，能表达更具体的约束优先级
- 好的 concept 应该描述语义能力，如 `Sortable`，而不是只堆砌偶然需要的语法表达式

### 示例

```cpp
#include <concepts>
#include <iostream>

void print(std::integral auto value) {
    std::cout << "integer: " << value << '\n';
}

template <typename T>
requires std::floating_point<T>
void print(T value) {
    std::cout << "float: " << value << '\n';
}

int main() {
    print(42);
    print(3.14);
}
```

### 代码讲解

- `std::integral auto` 把参数约束直接写在接口位置
- `requires std::floating_point<T>` 是 requires clause，控制模板是否参与匹配
- 调用 `print("x")` 时，错误会指向约束不满足，而不是深层模板实例化失败
- concepts 的工程价值在于把“模板要求”从技巧实现变成可读契约

### 现代 C++ 替代方案

- C++11/14 常见做法是 `std::enable_if` 和 traits
- C++17 可以用 `if constexpr` 简化函数体内的类型分支
- C++20 公共模板接口优先使用 concepts，把约束写到声明层

### 面试追问

- concepts 和 `if constexpr` 分别解决模板设计里的哪类问题？
- concept 应该描述语法可用，还是也应该表达语义要求？
- 为什么 concepts 改善错误信息，但不会自动避免代码膨胀？

---

## 28. requires clause 和 requires expression（C++20）有什么区别？

### 核心答案

requires clause 用来约束一个声明是否可用；requires expression 用来检查某组类型、表达式或嵌套要求是否合法，常用于定义 concept。

### English explanation

A requires clause constrains a declaration, while a requires expression checks whether expressions, types, and nested requirements are valid. They are often used together.

### 错误回答示例

- “两个 requires 完全是一回事”
- “requires expression 会在运行时检查条件”
- “requires 只是为了替代所有 `static_assert`”

### 面试官想听什么

- 你是否能区分“约束声明”和“检测表达式”
- 你是否知道 requires expression 结果是编译期 bool
- 你是否能写出一个简单 concept 并用它约束模板

### 项目里怎么说

我会用 requires expression 定义可复用的业务或库级 concept，再用 requires clause 或 abbreviated template syntax 放到函数接口上。这样比在函数体里写一堆 `static_assert` 更早参与重载选择。

### 深入解释

- `template <typename T> requires C<T>` 是 requires clause
- `requires(T x) { x.size(); }` 是 requires expression，用于检查表达式是否有效
- requires expression 中可以写 simple requirement、type requirement、compound requirement 和 nested requirement
- 当约束放在声明上时，不满足约束的模板不会成为可行候选

### 示例

```cpp
#include <concepts>
#include <vector>

template <typename T>
concept HasSize = requires(const T& x) {
    { x.size() } -> std::convertible_to<std::size_t>;
};

template <typename T>
requires HasSize<T>
auto sizeOf(const T& x) {
    return x.size();
}

int main() {
    std::vector<int> values{1, 2, 3};
    return static_cast<int>(sizeOf(values));
}
```

### 代码讲解

- `requires(const T& x) { ... }` 是 requires expression，用来定义 `HasSize`
- `{ x.size() } -> std::convertible_to<std::size_t>` 同时检查表达式存在和返回值约束
- `requires HasSize<T>` 是 requires clause，用来约束 `sizeOf`
- 这比把错误留到函数体里更清晰，也更适合重载决议

---

## 29. fold expression 的典型用途是什么？

### 核心答案

fold expression 用一个运算符展开参数包，常用于求和、逻辑组合、批量调用和构造参数检查；它让可变参数模板不再依赖递归展开。

### English explanation

Fold expressions expand parameter packs with an operator. They replace many recursive variadic-template patterns and make pack-based code much easier to read.

### 错误回答示例

- “fold expression 只能做加法”
- “参数包必须递归展开”
- “fold expression 和运行时循环是同一个东西”

### 面试官想听什么

- 你是否知道一元/二元、左折叠/右折叠的基本形式
- 你是否能说出逻辑 `&&`、`,` 逗号表达式等高频用途
- 你是否知道空参数包时需要考虑初始值或运算符规则

### 项目里怎么说

我会在日志封装、参数校验、批量注册、tuple 工具和模板工具函数里使用 fold expression。它的价值是让意图直接出现在代码里，而不是用递归模板制造阅读成本。

### 深入解释

- `(values + ...)` 是右折叠，`(... + values)` 是左折叠
- `(... && predicates)` 常用于所有条件都满足
- `((call(args)), ...)` 可用逗号表达式按顺序批量执行
- 对可能为空的参数包，二元折叠如 `(0 + ... + values)` 更安全

### 示例

```cpp
#include <iostream>
#include <type_traits>

template <typename... Ts>
auto sum(Ts... values) {
    return (0 + ... + values);
}

template <typename... Ts>
constexpr bool all_integral = (std::is_integral_v<Ts> && ...);

int main() {
    std::cout << sum(1, 2, 3) << '\n';
    static_assert(all_integral<int, long, char>);
}
```

### 代码讲解

- `(0 + ... + values)` 是带初始值的 fold，空参数包时也有定义
- `(std::is_integral_v<Ts> && ...)` 把每个类型 traits 结果用 `&&` 合并
- fold expression 发生在编译期展开语法层面，不是运行时容器循环
- 面试可强调：它是 C++17 简化可变参数模板的重要工具

---

## 30. template specialization 和 overload 怎么取舍？

### 核心答案

函数行为差异通常优先用重载或 concepts 约束表达；类型级定制、traits 和类模板差异常用特化。不要把所有分支都写成特化，否则可读性和重载规则会变复杂。

### English explanation

For function behavior differences, overloads or constrained overloads are usually clearer. Specialization is more common for class templates, type traits, and type-level customization.

### 错误回答示例

- “模板特化比重载更高级，所以优先用特化”
- “函数模板偏特化可以直接使用”
- “重载、特化、SFINAE 都差不多”

### 面试官想听什么

- 你是否知道函数模板不能偏特化，通常用重载解决
- 你是否能说明类模板特化适合类型级结构差异
- 你是否理解 overload resolution 和 specialization 是不同机制

### 项目里怎么说

如果我要根据参数类型选择函数行为，我会先考虑普通重载或 C++20 constrained overload；如果是在写 traits、policy 或容器适配这种类型级映射，才会使用类模板特化。

### 深入解释

- 重载参与函数重载决议，适合表达不同参数接口
- 显式特化是为某个具体类型提供特殊实现
- 类模板偏特化适合把类型模式映射到不同实现
- C++20 concepts 能让“哪些类型能调用这个重载”更清楚

### 示例

```cpp
#include <iostream>
#include <type_traits>

void print(int) {
    std::cout << "int overload\n";
}

template <typename T>
void print(T) {
    std::cout << "generic template\n";
}

template <typename T>
struct IsPointerLike : std::false_type {};

template <typename T>
struct IsPointerLike<T*> : std::true_type {};

int main() {
    print(1);
    print(1.0);
    static_assert(IsPointerLike<int*>::value);
}
```

### 代码讲解

- `print(int)` 是普通重载，调用 `print(1)` 时优先匹配
- `print(T)` 是泛型兜底
- `IsPointerLike<T*>` 是类模板偏特化，适合表达“某种类型模式”的性质
- 面试里要避免把“函数行为选择”和“类型性质映射”混成一种工具

---

## 31. dependent name 和 `typename` / `template` 关键字是什么？

### 核心答案

依赖模板参数的名字在模板定义阶段含义不一定确定；`typename` 告诉编译器某个依赖名是类型，`template` 告诉编译器某个依赖成员是模板。

### English explanation

Dependent names depend on template parameters, so their meaning may not be known when the template is parsed. `typename` and `template` disambiguate types and member templates in dependent contexts.

### 错误回答示例

- “编译器应该能自己猜出依赖名是不是类型”
- “`typename` 只在模板参数列表里用”
- “dependent name 是语法冷知识，不影响读模板代码”

### 面试官想听什么

- 你是否理解模板分两阶段查找的基本问题
- 你是否知道依赖名默认不被当作类型
- 你是否能读懂标准库和泛型库里的 `typename T::value_type`

### 项目里怎么说

读模板库代码时，我会特别关注依赖名，因为很多看似奇怪的 `typename` 和 `template` 不是风格问题，而是告诉编译器如何解析模板。写公共模板时我也会尽量通过别名和 concept 降低这种语法噪音。

### 深入解释

- `T::value_type` 是否存在、是否为类型，要等 `T` 确定后才知道
- 在依赖上下文中，编译器需要 `typename` 才能把它按类型解析
- 调用依赖对象的成员模板时，可能需要 `obj.template f<int>()` 消除 `<` 的解析歧义
- C++20 concepts 能提前约束类型要求，但不消除所有依赖名语法

### 示例

```cpp
#include <vector>

template <typename Container>
void resetFirst(Container& c) {
    typename Container::value_type value{};
    c[0] = value;
}

int main() {
    std::vector<int> values{1};
    resetFirst(values);
}
```

### 代码讲解

- `Container::value_type` 依赖模板参数 `Container`
- `typename` 告诉编译器它是一个类型，而不是静态成员或别的名字
- `value{}` 构造一个该容器元素类型的默认值
- 面试重点是：这是模板解析规则，不是多余关键字

---

## 32. exception guarantee 如何设计到接口？

### 核心答案

异常保证是接口契约的一部分：基本保证确保异常后对象仍有效且无泄漏，强保证确保失败后状态不变，不抛保证承诺函数不会抛异常。

### English explanation

Exception guarantees are part of interface design. The basic guarantee keeps objects valid, the strong guarantee preserves state on failure, and the no-throw guarantee promises no exceptions.

### 错误回答示例

- “用异常就不用设计错误边界”
- “所有函数都应该强保证”
- “`noexcept` 只是优化提示，写不写无所谓”

### 面试官想听什么

- 你是否能把异常安全和资源管理、对象不变量联系起来
- 你是否知道 move 构造的 `noexcept` 会影响标准容器优化
- 你是否能说明 copy-and-swap、先构造临时对象再提交等强保证策略

### 项目里怎么说

我会在接口设计时明确失败后对象处于什么状态。资源释放和析构路径必须不抛；修改复杂状态时尽量先准备临时结果，成功后再提交，避免半更新状态泄露到调用方。

### 深入解释

- 基本保证是最低要求：没有资源泄漏，对象仍能析构或继续使用
- 强保证常通过事务式更新实现：先构造新状态，成功后交换或提交
- 不抛保证适合析构、释放资源、移动操作和底层清理函数
- `noexcept` 如果写错导致异常逃出，会调用 `std::terminate`，所以必须有把握

### 示例

```cpp
#include <string>
#include <utility>
#include <vector>

class Names {
public:
    void replaceAll(std::vector<std::string> next) {
        names_.swap(next); // 构造 next 失败时，names_ 尚未改变
    }

private:
    std::vector<std::string> names_;
};
```

### 代码讲解

- 参数 `next` 在进入函数前已经构造完成，失败不会修改当前对象
- `swap` 通常是低风险提交动作，可用于实现强保证
- 这类设计把“准备新状态”和“提交新状态”分开
- 面试中要说明异常安全不是 try/catch 数量，而是不变量和状态提交策略

---

## 33. lock-free 不等于 wait-free 是什么意思？

### 核心答案

lock-free 保证系统整体总有线程能推进；wait-free 保证每个线程都能在有限步骤内完成。wait-free 更强，也通常更难实现和验证。

### English explanation

Lock-free means the system as a whole makes progress; wait-free means every individual thread completes within a bounded number of steps.

### 错误回答示例

- “不用 mutex 就一定 lock-free”
- “lock-free 等于每个线程都不会等待”
- “lock-free 数据结构一定比加锁更快”

### 面试官想听什么

- 你是否知道 progress guarantee 的层级差异
- 你是否能区分无锁算法、原子操作和实际性能
- 你是否知道无锁代码还要处理内存回收、ABA、内存序和测试困难

### 项目里怎么说

我不会因为听起来高级就优先写 lock-free。业务代码优先选择锁和清晰的不变量；只有在性能数据证明锁竞争是瓶颈，并且团队能维护内存序和回收策略时，才考虑无锁结构。

### 深入解释

- lock-free 允许某个线程一直失败重试，只要整体有线程成功推进
- wait-free 要求每个线程都有 bounded progress，不会被其他线程无限拖住
- obstruction-free 又更弱，只保证单线程独占运行时能推进
- 性能上，无锁可能减少阻塞，但也可能因为 CAS 重试、缓存争用和复杂内存序变慢

### 示例

```cpp
#include <atomic>

class Counter {
public:
    void increment() {
        value_.fetch_add(1, std::memory_order_relaxed);
    }

    int value() const {
        return value_.load(std::memory_order_relaxed);
    }

private:
    std::atomic<int> value_{0};
};
```

### 代码讲解

- `fetch_add` 是原子读改写操作，不需要 `mutex` 保护这个计数值
- `relaxed` 足够用于单纯计数，因为这里只需要原子性，不发布其他数据
- 这不等于所有 lock-free 结构都简单；栈、队列还涉及节点生命周期和 ABA
- 面试里要避免把“用了 atomic”直接等同于“算法可证明正确”

---

## 34. ABA 问题基础是什么？

### 核心答案

ABA 问题是 CAS 只看到值从 A 又变回 A，却不知道中间经历过 B；在无锁栈、队列和内存复用场景中，这可能让线程基于过期假设错误更新结构。

### English explanation

The ABA problem occurs when compare-and-swap sees the same value again but misses intermediate changes. This is dangerous in lock-free structures where pointer identity and lifetime matter.

### 错误回答示例

- “值最后没变，所以 CAS 成功一定没问题”
- “ABA 只发生在理论算法里”
- “把指针换成 atomic 指针就解决了 ABA”

### 面试官想听什么

- 你是否知道 CAS 比较的是当前值，不理解历史变化
- 你是否能把 ABA 和节点释放/复用联系起来
- 你是否知道版本号、tagged pointer、hazard pointer、epoch reclamation 等缓解思路

### 项目里怎么说

如果要做无锁容器，我会先确认内存回收方案，而不是只写 CAS 循环。很多 ABA 风险来自节点被弹出、释放、又复用到同一地址，单看 atomic 操作本身无法解决生命周期问题。

### 深入解释

- 线程 T1 读到 head=A 后暂停
- 线程 T2 把 A 弹出，又经过若干操作让 head 回到 A
- T1 的 CAS 看到 head 仍是 A，于是误以为结构没变
- 版本号让 CAS 比较 `(指针, 版本)`，hazard pointer/epoch 则避免节点被过早回收复用

### 示例

```cpp
#include <atomic>
#include <cstdint>

struct Node {};

struct TaggedPtr {
    Node* ptr;
    std::uint64_t version;
};

int main() {
    TaggedPtr old{nullptr, 0};
    TaggedPtr next{nullptr, old.version + 1};
    (void)next;
}
```

### 代码讲解

- `TaggedPtr` 表示不仅比较地址，也比较版本
- 即使 `ptr` 从 A 变回 A，`version` 也会变化
- 真实无锁结构还要保证 `TaggedPtr` 能被原子更新，且平台支持对应宽度 CAS
- 这个例子展示思路，不是完整无锁栈实现

---

## 35. false sharing 和 cache line 是什么？

### 核心答案

false sharing 是不同线程修改不同变量，但这些变量落在同一 cache line，导致缓存一致性协议反复让整条缓存行失效，性能严重下降。

### English explanation

False sharing happens when independent variables modified by different threads share a cache line, causing unnecessary cache-coherence traffic.

### 错误回答示例

- “不同变量就不会互相影响”
- “false sharing 是数据竞争的一种”
- “加 atomic 就能避免 false sharing”

### 面试官想听什么

- 你是否知道 CPU cache line 是一致性传输的基本粒度
- 你是否能区分正确性问题和性能问题
- 你是否知道对齐、padding、分片计数和数据布局能缓解热点写入争用

### 项目里怎么说

并发性能问题我会先用 profiling 证明，再调整数据布局。对高频写入的 per-thread 计数器、队列索引或统计字段，我会考虑 cache line 隔离，而不是只盯着锁或算法复杂度。

### 深入解释

- cache line 常见大小是 64 字节，但不要在可移植代码里硬编码所有假设
- 即使两个线程写的是不同 atomic 变量，只要在同一 cache line，也可能反复争夺所有权
- C++17 提供 `std::hardware_destructive_interference_size` 作为提示
- 解决 false sharing 通常会增加内存占用，所以要用在真实热点上

### 示例

```cpp
#include <atomic>
#include <new>

struct alignas(std::hardware_destructive_interference_size) Counter {
    std::atomic<int> value{0};
};

int main() {
    Counter counters[2];
    counters[0].value.fetch_add(1, std::memory_order_relaxed);
    counters[1].value.fetch_add(1, std::memory_order_relaxed);
}
```

### 代码讲解

- `alignas(std::hardware_destructive_interference_size)` 尝试让热点对象按破坏性干扰大小隔离
- 两个 `Counter` 更不容易落在同一 cache line
- `relaxed` 只说明这个计数不发布其他数据，和 false sharing 是不同维度
- 面试中要强调：false sharing 是性能问题，不是数据竞争正确性问题

---

## 36. acquire-release 的真实发布订阅例子是什么？

### 核心答案

release store 可以发布它之前的普通写入；acquire load 如果读到这次发布，就能看到发布前写入。它适合单向“准备数据 -> 发布标记 -> 读取数据”的同步。

### English explanation

A release store publishes prior writes, and an acquire load that observes that store can safely see those writes. It is a common publish-subscribe synchronization pattern.

### 错误回答示例

- “acquire/release 会让所有线程全局顺序一致”
- “release 写在消费者，acquire 写在生产者也一样”
- “标记是 atomic，数据就不需要同步关系了”

### 面试官想听什么

- 你是否能说出 release 和 acquire 的方向性
- 你是否知道同步关系必须通过同一个原子对象或 release sequence 建立
- 你是否知道 acquire/release 比 seq_cst 弱，但常足以表达发布订阅

### 项目里怎么说

我会把 acquire-release 用在小而明确的底层同步点，比如一次性发布配置、状态标记或无锁队列节点可见性。若同步逻辑跨多个状态变量，业务代码里通常用锁更可维护。

### 深入解释

- release 防止之前写入被重排到发布之后
- acquire 防止之后读取被重排到获取之前
- acquire 只有读到对应 release 写入的值时，才建立有用的同步关系
- 如果消费者没有读到 `ready=true`，就不能假设看到了生产者的数据

### 示例

```cpp
#include <atomic>
#include <thread>

struct Message {
    int code;
    int value;
};

Message msg{};
std::atomic<bool> ready{false};

void publish() {
    msg = Message{7, 42};
    ready.store(true, std::memory_order_release);
}

int read() {
    while (!ready.load(std::memory_order_acquire)) {
    }
    return msg.value;
}
```

### 代码讲解

- `msg = Message{7, 42}` 是普通写入
- `ready.store(true, release)` 发布这次普通写入
- `ready.load(acquire)` 读到 `true` 后，消费者能安全读取 `msg`
- 如果把 load/store 都改成 `relaxed`，原子性仍在，但 `msg` 的可见性没有被建立

---

## 37. coroutine（C++20）基础模型是什么？

### 核心答案

C++ coroutine 是可暂停和恢复的函数机制；语言只提供状态机转换、promise/awaiter 协议和句柄模型，不自带事件循环、线程池或异步 IO 框架。

### English explanation

C++ coroutines are suspendable functions. The language provides the state-machine mechanism and the promise/awaiter protocol, but scheduling and I/O behavior come from libraries.

### 错误回答示例

- “协程等于新线程”
- “写了 `co_await` 就自动异步并发”
- “C++20 coroutine 已经自带完整 async runtime”

### 面试官想听什么

- 你是否能区分语言机制和库调度器
- 你是否知道 promise type、awaiter、coroutine handle 的角色
- 你是否理解协程帧的生命周期和资源释放风险

### 项目里怎么说

我会把 coroutine 当作异步控制流表达工具，而不是单独的并发方案。项目里是否使用它，取决于有没有成熟 runtime、调试工具、取消模型和异常传播约定。

### 深入解释

- 编译器把协程函数转换成状态机，并把局部状态保存在 coroutine frame 中
- `promise_type` 定义返回对象、初始/最终挂起、异常处理和返回值策略
- `await_ready/await_suspend/await_resume` 决定 `co_await` 的行为
- 没有调度器时，协程不会凭空切到后台线程执行

### 示例

```cpp
#include <coroutine>

struct Task {
    struct promise_type {
        Task get_return_object() { return {}; }
        std::suspend_never initial_suspend() noexcept { return {}; }
        std::suspend_never final_suspend() noexcept { return {}; }
        void return_void() {}
        void unhandled_exception() {}
    };
};

Task run() {
    co_return;
}

int main() {
    run();
}
```

### 代码讲解

- 出现 `co_return` 后，`run` 成为协程函数
- `promise_type` 是协程协议的核心，定义返回对象和挂起策略
- `suspend_never` 表示这里不在初始或最终位置挂起
- 真实异步场景还需要 awaiter 和调度器，这个例子只展示语言骨架

---

## 38. modules（C++20）解决什么问题？

### 核心答案

modules 试图替代头文件文本包含模型，减少重复解析、宏污染和脆弱包含顺序，同时让接口和实现边界更明确；落地依赖编译器、构建系统和库生态支持。

### English explanation

C++ modules reduce problems caused by textual inclusion: repeated parsing, macro leakage, and fragile include order. They improve interface boundaries but require toolchain and build-system support.

### 错误回答示例

- “modules 就是更快的 header”
- “用了 modules 就不需要理解链接和 ABI”
- “所有项目都应该立刻迁移 modules”

### 面试官想听什么

- 你是否知道头文件模型的问题：文本包含、宏泄漏、编译成本和 ODR 风险
- 你是否理解 module interface unit、export、import 的基本角色
- 你是否能说出现阶段迁移成本和生态限制

### 项目里怎么说

新项目如果工具链稳定，我会评估 modules 对构建时间和接口边界的收益；已有大型项目迁移时会分层推进，优先从内部库或稳定模块开始，不会把它当成单纯搜索替换 `#include`。

### 深入解释

- `import` 导入的是已编译的模块接口，不是简单文本粘贴
- `export` 决定哪些声明成为模块接口的一部分
- 宏默认不会像头文件那样自然穿透模块边界，这能减少污染，也会影响迁移
- modules 改善源码组织和构建模型，但不自动解决动态库 ABI 稳定问题

### 示例

```cpp
// math.cppm
export module math;

export int add(int a, int b) {
    return a + b;
}

// main.cpp
import math;

int main() {
    return add(1, 2);
}
```

### 代码讲解

- `export module math;` 定义模块接口单元
- `export int add...` 把函数暴露给导入者
- `import math;` 使用模块接口，而不是文本包含头文件
- 实际构建需要编译器和构建系统正确处理模块依赖扫描

---

## 39. ABI 稳定性和动态库接口设计要注意什么？

### 核心答案

ABI 稳定性关注二进制兼容：调用约定、符号名、对象布局、异常、RTTI、标准库类型和编译器版本都会影响动态库边界。稳定接口通常用 C API、Pimpl、版本化符号或明确的插件边界隔离 C++ 实现细节。

### English explanation

ABI stability is about binary compatibility. Exposing C++ classes across shared-library boundaries is fragile because layout, name mangling, exceptions, RTTI, and standard library ABI can vary across compilers and versions.

### 错误回答示例

- “头文件不变 ABI 就一定稳定”
- “C++ 类直接跨动态库导出最方便，也最安全”
- “只要能链接成功，就说明 ABI 没问题”

### 面试官想听什么

- 你是否知道 API 和 ABI 的区别
- 你是否能说出哪些 C++ 细节会改变二进制布局
- 你是否知道动态库边界上内存分配、异常传播和 STL 类型暴露的风险

### 项目里怎么说

跨动态库或插件边界时，我会尽量暴露稳定 C ABI 或很薄的抽象边界，避免把 `std::string`、`std::vector`、模板类和异常直接作为 ABI 契约。C++ 实现细节放在库内部，通过工厂/销毁函数或 Pimpl 管理生命周期。

### 深入解释

- API 是源码层接口，ABI 是编译后二进制如何调用和解释对象
- 给类新增虚函数、改变成员顺序、改变对齐、切换标准库实现都可能破坏 ABI
- 跨库分配和释放内存要非常谨慎，最好由同一模块负责创建和销毁
- 异常和 RTTI 跨边界依赖运行时兼容性，插件系统里常选择错误码或结果对象

### 示例

```cpp
// plugin_api.h
#pragma once

#ifdef __cplusplus
extern "C" {
#endif

struct PluginHandle;

PluginHandle* plugin_create();
void plugin_destroy(PluginHandle* handle);
int plugin_version();

#ifdef __cplusplus
}
#endif
```

### 代码讲解

- `extern "C"` 降低 C++ name mangling 带来的符号兼容问题
- `PluginHandle` 是不透明类型，调用方不知道内部 C++ 类布局
- `plugin_create/plugin_destroy` 让同一个库负责对象创建和销毁
- 真实项目还会加版本号、能力查询、错误码和线程安全约定

### 面试追问

- API 兼容但 ABI 不兼容的例子有哪些？
- 为什么不建议把 STL 容器直接暴露到长期稳定的动态库 ABI？
- Pimpl 能解决哪些 ABI 问题，又不能解决哪些问题？

---

## 40. `std::pmr` 和内存资源基础是什么？

### 核心答案

`std::pmr` 把容器的分配策略抽象成 `memory_resource`，让同一类容器能在运行时选择不同内存资源；它适合批量分配、短生命周期区域、局部内存池和性能诊断明确的场景。

### English explanation

`std::pmr` separates containers from allocation strategy through `memory_resource`. It lets containers choose allocation behavior at runtime, which is useful for arenas, short-lived batches, and allocation-sensitive code.

### 错误回答示例

- “pmr 是更快的 vector，应该默认用”
- “monotonic buffer resource 会自动逐个析构所有对象”
- “用了 pmr 就不用关心资源生命周期”

### 面试官想听什么

- 你是否知道 `memory_resource` 是运行时多态分配接口
- 你是否能区分 allocator 模板参数和 pmr 运行时资源
- 你是否知道 `monotonic_buffer_resource` 适合批量释放，不适合任意释放模式

### 项目里怎么说

如果某个请求、帧或批处理阶段会创建大量短生命周期字符串和容器，我会考虑用 `std::pmr::monotonic_buffer_resource` 把分配集中到一个区域，阶段结束一次性释放。前提是生命周期边界清楚，并且 profiling 证明分配成本值得优化。

### 深入解释

- `std::pmr::vector<T>` 本质是使用 `polymorphic_allocator<T>` 的 vector 别名
- `polymorphic_allocator` 持有 `memory_resource*`，因此分配策略可在运行时决定
- `monotonic_buffer_resource` 通常只增长不单独回收小块内存，适合 arena 风格
- pmr 不改变对象语义，容器元素仍会正常构造和析构；它改变的是底层存储来源

### 示例

```cpp
#include <array>
#include <cstddef>
#include <memory_resource>
#include <string>
#include <vector>

int main() {
    std::array<std::byte, 2048> buffer{};
    std::pmr::monotonic_buffer_resource arena(buffer.data(), buffer.size());

    std::pmr::vector<std::pmr::string> names{&arena};
    names.emplace_back("imu");
    names.emplace_back("lidar");
}
```

### 代码讲解

- `buffer` 提供一块栈上初始存储
- `monotonic_buffer_resource arena(...)` 把这块存储包装成内存资源，不够时可向上游资源继续申请
- `std::pmr::vector<std::pmr::string> names{&arena}` 让 vector 和内部字符串都使用同一个资源
- 适合“整批对象一起释放”的生命周期，不适合长期零散删除和复用的通用场景

### 面试追问

- `std::pmr::vector<T>` 和 `std::vector<T, MyAllocator<T>>` 的设计差异是什么？
- `monotonic_buffer_resource` 为什么适合 request/frame arena？
- pmr 优化分配成本时，最容易引入的生命周期错误是什么？

---

## 高级篇复习建议

- 回答不要只停在定义，要讲设计动机和代价
- 凡是并发题，优先强调正确性和可证明性
- 凡是高级技巧题，尽量回到“什么时候真的值得用”
